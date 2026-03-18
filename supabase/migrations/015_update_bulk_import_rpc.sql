-- Migration 015: Update bulk_import_songs to include handcrafted_norm and deezer_id
-- These columns were added in later migrations but the RPC was never updated.

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
      handcrafted_norm,
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
      (v_row->>'handcrafted_norm')::vector(44),
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
