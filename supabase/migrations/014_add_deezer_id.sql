-- Add deezer_id column for Deezer widget embedding
ALTER TABLE public.songs ADD COLUMN IF NOT EXISTS deezer_id BIGINT;

-- Unique index (partial — only on non-null values so uploads without deezer source don't conflict)
CREATE UNIQUE INDEX IF NOT EXISTS idx_songs_deezer_id
  ON public.songs (deezer_id) WHERE deezer_id IS NOT NULL;

-- Extend find_similar_songs to return deezer_id
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
    deezer_id BIGINT,
    similarity FLOAT
)
LANGUAGE sql AS $$
    SELECT id, title, artist, album, bpm, musical_key,
           duration_sec, genre, deezer_id,
           1 - (learned_embedding <=> query_embedding) AS similarity
    FROM songs
    WHERE id IS DISTINCT FROM exclude_id
      AND bpm BETWEEN min_bpm AND max_bpm
      AND metadata_status != 'failed'
    ORDER BY learned_embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Update bulk_import_songs to accept deezer_id
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
  FOR v_row IN SELECT jsonb_array_elements(rows)
  LOOP
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
      metadata_status,
      deezer_id
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
      COALESCE(v_row->>'metadata_status', 'complete'),
      (v_row->>'deezer_id')::bigint
    )
    ON CONFLICT DO NOTHING;

    v_count := v_count + 1;
  END LOOP;

  RETURN v_count;
END;
$$;

GRANT EXECUTE ON FUNCTION bulk_import_songs(jsonb) TO anon;
GRANT EXECUTE ON FUNCTION bulk_import_songs(jsonb) TO authenticated;
