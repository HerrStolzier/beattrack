-- Extend find_similar_songs to return musical_key and duration_sec
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
    similarity FLOAT
)
LANGUAGE sql AS $$
    SELECT id, title, artist, album, bpm, musical_key,
           duration_sec,
           1 - (learned_embedding <=> query_embedding) AS similarity
    FROM songs
    WHERE id IS DISTINCT FROM exclude_id
      AND bpm BETWEEN min_bpm AND max_bpm
      AND metadata_status != 'failed'
    ORDER BY learned_embedding <=> query_embedding
    LIMIT match_count;
$$;
