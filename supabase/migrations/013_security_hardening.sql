-- Migration 013: Security hardening
-- Fixes: bulk_import anon access, SECURITY DEFINER misuse, missing input validation,
--        match_count cap, search_path, feedback INSERT policy, refresh_feedback_stats access, bpm index

-- ============================================================
-- 1. REVOKE anon/authenticated access to bulk_import_songs
--    Import is done — no reason to keep this callable by anon
-- ============================================================
REVOKE EXECUTE ON FUNCTION bulk_import_songs(jsonb) FROM anon;
REVOKE EXECUTE ON FUNCTION bulk_import_songs(jsonb) FROM authenticated;

-- ============================================================
-- 2. Add input validation to bulk_import_songs
-- ============================================================
CREATE OR REPLACE FUNCTION bulk_import_songs(rows jsonb)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_count integer := 0;
  v_row jsonb;
BEGIN
  -- Validate batch size
  IF jsonb_array_length(rows) > 500 THEN
    RAISE EXCEPTION 'Batch too large: maximum 500 rows per call';
  END IF;

  FOR v_row IN SELECT jsonb_array_elements(rows)
  LOOP
    -- Validate required fields
    IF v_row->>'title' IS NULL OR length(v_row->>'title') > 500 THEN
      RAISE EXCEPTION 'Invalid or missing title';
    END IF;
    IF v_row->>'artist' IS NULL OR length(v_row->>'artist') > 500 THEN
      RAISE EXCEPTION 'Invalid or missing artist';
    END IF;

    INSERT INTO songs (
      title,
      artist,
      album,
      duration_sec,
      bpm,
      musical_key,
      learned_embedding,
      handcrafted_raw,
      source,
      genre,
      release_year,
      embedding_type,
      metadata_status
    ) VALUES (
      v_row->>'title',
      v_row->>'artist',
      v_row->>'album',
      (v_row->>'duration_sec')::float,
      (v_row->>'bpm')::float,
      v_row->>'musical_key',
      (v_row->>'learned_embedding')::vector(200),
      (v_row->>'handcrafted_raw')::vector(44),
      COALESCE(v_row->>'source', 'unknown'),
      v_row->>'genre',
      (v_row->>'release_year')::integer,
      COALESCE(v_row->>'embedding_type', 'real'),
      COALESCE(v_row->>'metadata_status', 'complete')
    )
    ON CONFLICT DO NOTHING;

    v_count := v_count + 1;
  END LOOP;

  RETURN v_count;
END;
$$;

-- Only service_role can call bulk_import_songs
GRANT EXECUTE ON FUNCTION bulk_import_songs(jsonb) TO service_role;

-- ============================================================
-- 3. Fix get_distinct_genres: SECURITY INVOKER (no elevated privileges needed)
-- ============================================================
CREATE OR REPLACE FUNCTION get_distinct_genres()
RETURNS TABLE (genre TEXT)
LANGUAGE sql SECURITY INVOKER
SET search_path = public
AS $$
    SELECT DISTINCT genre FROM songs
    WHERE genre IS NOT NULL
    ORDER BY genre;
$$;

-- ============================================================
-- 4. Recreate find_similar_songs with match_count cap + search_path
-- ============================================================
DROP FUNCTION IF EXISTS find_similar_songs(VECTOR(200), INT, UUID, FLOAT, FLOAT);

CREATE OR REPLACE FUNCTION find_similar_songs(
    query_embedding VECTOR(200),
    match_count INT DEFAULT 20,
    exclude_id UUID DEFAULT NULL,
    min_bpm FLOAT DEFAULT 0,
    max_bpm FLOAT DEFAULT 999
) RETURNS TABLE (
    id UUID,
    title TEXT,
    artist TEXT,
    album TEXT,
    bpm FLOAT,
    musical_key TEXT,
    duration_sec FLOAT,
    genre TEXT,
    similarity FLOAT
)
LANGUAGE sql
SECURITY INVOKER
SET search_path = public
AS $$
    SELECT id, title, artist, album, bpm, musical_key,
           duration_sec, genre,
           1 - (learned_embedding <=> query_embedding) AS similarity
    FROM songs
    WHERE id IS DISTINCT FROM exclude_id
      AND bpm BETWEEN min_bpm AND max_bpm
      AND metadata_status != 'failed'
    ORDER BY learned_embedding <=> query_embedding
    LIMIT LEAST(match_count, 100);
$$;

-- ============================================================
-- 5. Restrict refresh_feedback_stats to service_role only
-- ============================================================
REVOKE EXECUTE ON FUNCTION refresh_feedback_stats() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION refresh_feedback_stats() TO service_role;

-- ============================================================
-- 6. Tighten feedback INSERT policy: require non-null song IDs
-- ============================================================
DROP POLICY IF EXISTS "feedback_insert_anon" ON public.feedback;

CREATE POLICY "feedback_insert_anon"
    ON public.feedback FOR INSERT
    TO anon
    WITH CHECK (
        query_song_id IS NOT NULL
        AND result_song_id IS NOT NULL
        AND rating IN (1, -1)
    );

-- ============================================================
-- 7. Add BPM index for range queries in similarity function
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_songs_bpm ON songs (bpm);
