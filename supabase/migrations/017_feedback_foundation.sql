-- Phase 0: Feedback Learning Foundation
-- Extend feedback table with audit + context columns

ALTER TABLE feedback ADD COLUMN IF NOT EXISTS ip_hash TEXT;
ALTER TABLE feedback ADD COLUMN IF NOT EXISTS focus_active TEXT;
ALTER TABLE feedback ADD COLUMN IF NOT EXISTS ab_group TEXT;

-- Index for spam detection (by IP over time)
CREATE INDEX IF NOT EXISTS idx_feedback_ip_hash ON feedback (ip_hash, created_at DESC);

-- Index for focus aggregation (Phase 1 prep)
CREATE INDEX IF NOT EXISTS idx_feedback_focus ON feedback (focus_active) WHERE focus_active IS NOT NULL;

-- Unique index on materialized view for CONCURRENTLY refresh
CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_stats_unique
  ON feedback_stats (query_song_id, result_song_id);
