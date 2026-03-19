-- Fix: similarity search times out at 175K+ songs because WHERE clauses
-- prevent PostgreSQL from using the HNSW index.
-- Solution: do vector search first (inner subquery uses index), then filter.

-- Also increase HNSW ef_search for better recall at scale
SET ivfflat.probes = 10;

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
LANGUAGE sql
SET hnsw.ef_search = 200
AS $$
    -- Inner query forces HNSW index usage, outer query applies filters
    SELECT sub.id, sub.title, sub.artist, sub.album, sub.bpm,
           sub.musical_key, sub.duration_sec, sub.genre, sub.deezer_id,
           sub.similarity
    FROM (
        SELECT s.id, s.title, s.artist, s.album, s.bpm,
               s.musical_key, s.duration_sec, s.genre, s.deezer_id,
               1 - (s.learned_embedding <=> query_embedding) AS similarity
        FROM songs s
        WHERE s.learned_embedding IS NOT NULL
        ORDER BY s.learned_embedding <=> query_embedding
        LIMIT match_count * 5
    ) sub
    WHERE sub.id IS DISTINCT FROM exclude_id
      AND sub.bpm BETWEEN min_bpm AND max_bpm
    ORDER BY sub.similarity DESC
    LIMIT match_count;
$$;

-- Rebuild HNSW index with higher parameters for 175K+ songs
DROP INDEX IF EXISTS idx_songs_learned_embedding;
CREATE INDEX idx_songs_learned_embedding ON songs
    USING hnsw (learned_embedding vector_cosine_ops)
    WITH (m = 24, ef_construction = 128);

-- Grant access
GRANT EXECUTE ON FUNCTION find_similar_songs(VECTOR(200), INT, UUID, FLOAT, FLOAT) TO anon;
GRANT EXECUTE ON FUNCTION find_similar_songs(VECTOR(200), INT, UUID, FLOAT, FLOAT) TO authenticated;
