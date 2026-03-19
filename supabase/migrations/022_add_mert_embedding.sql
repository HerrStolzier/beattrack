-- Migration 022: Add MERT embedding column for dual-embedding fusion
-- MERT-v1-95M produces 768-dim embeddings, used as re-ranking signal
-- MusiCNN HNSW stays as primary search index

ALTER TABLE songs ADD COLUMN IF NOT EXISTS mert_embedding VECTOR(768);

COMMENT ON COLUMN songs.mert_embedding IS 'MERT-v1-95M 768-dim embedding (mean-pooled last hidden state). Used for re-ranking in Late Fusion, not HNSW search.';
