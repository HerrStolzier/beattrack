-- Migration 011: bulk_import_songs RPC function
-- Used by import_features.py to insert songs via anon key (no service_role needed)

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

-- Grant execute to anon so import_features.py can call it with anon key
GRANT EXECUTE ON FUNCTION bulk_import_songs(jsonb) TO anon;
GRANT EXECUTE ON FUNCTION bulk_import_songs(jsonb) TO authenticated;
