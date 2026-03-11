-- Phase 1.3: Core schema with pgvector + pg_trgm
-- Extensions must be enabled before use

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Songs table with dual embeddings (MusiCNN learned + handcrafted)
CREATE TABLE songs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    musicbrainz_id TEXT UNIQUE,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT,
    duration_sec FLOAT,
    bpm FLOAT,
    musical_key TEXT,
    -- Dual Embeddings
    learned_embedding VECTOR(200) NOT NULL,
    handcrafted_raw VECTOR(44) NOT NULL,
    handcrafted_norm VECTOR(44) NOT NULL,
    -- Metadata
    source TEXT DEFAULT 'fma',
    embedding_type TEXT DEFAULT 'real',
    metadata_status TEXT DEFAULT 'complete',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index on learned embedding (primary similarity search)
CREATE INDEX idx_songs_learned_embedding ON songs
    USING hnsw (learned_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- HNSW index on handcrafted embedding (secondary/filter queries)
CREATE INDEX idx_songs_handcrafted_norm ON songs
    USING hnsw (handcrafted_norm vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Trigram indexes for fuzzy text search (URL input)
CREATE INDEX idx_songs_title_trgm ON songs USING gin (title gin_trgm_ops);
CREATE INDEX idx_songs_artist_trgm ON songs USING gin (artist gin_trgm_ops);
