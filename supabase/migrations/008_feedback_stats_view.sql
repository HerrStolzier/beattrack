-- Materialized view: aggregated feedback per song pair
CREATE MATERIALIZED VIEW IF NOT EXISTS feedback_stats AS
SELECT
  query_song_id,
  result_song_id,
  COUNT(*) FILTER (WHERE rating = 1) AS total_up,
  COUNT(*) FILTER (WHERE rating = -1) AS total_down,
  COUNT(*) FILTER (WHERE rating = 1) - COUNT(*) FILTER (WHERE rating = -1) AS net_score,
  COUNT(*) AS total_votes
FROM feedback
GROUP BY query_song_id, result_song_id;

-- Index for fast lookup by song pair
CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_stats_pair
  ON feedback_stats (query_song_id, result_song_id);

-- Index for top/flop queries
CREATE INDEX IF NOT EXISTS idx_feedback_stats_net_score
  ON feedback_stats (net_score DESC);

-- Function to refresh the view (call periodically or on demand)
CREATE OR REPLACE FUNCTION refresh_feedback_stats()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY feedback_stats;
END;
$$ LANGUAGE plpgsql;
