-- Phase 1: Feature Importance Learning
-- Genre-specific focus weights derived from user feedback

CREATE MATERIALIZED VIEW IF NOT EXISTS genre_focus_weights AS
WITH vote_context AS (
  SELECT
    sq.genre,
    f.focus_active,
    COUNT(*) as votes
  FROM feedback f
  JOIN songs sq ON f.query_song_id = sq.id
  WHERE f.focus_active IS NOT NULL
    AND f.rating = 1
  GROUP BY sq.genre, f.focus_active
),
genre_totals AS (
  SELECT genre, SUM(votes) as total_positive
  FROM vote_context
  GROUP BY genre
  HAVING SUM(votes) >= 20
)
SELECT
  vc.genre,
  vc.focus_active as focus_category,
  ROUND(vc.votes::numeric / gt.total_positive, 4) as weight,
  vc.votes as vote_count
FROM vote_context vc
JOIN genre_totals gt ON vc.genre = gt.genre;

CREATE UNIQUE INDEX IF NOT EXISTS idx_genre_focus_weights_pk
  ON genre_focus_weights (genre, focus_category);

-- RPC to refresh the view (callable from backend)
CREATE OR REPLACE FUNCTION refresh_genre_weights()
RETURNS void
LANGUAGE sql
SECURITY DEFINER
AS $$ REFRESH MATERIALIZED VIEW CONCURRENTLY genre_focus_weights; $$;

-- Grants
GRANT SELECT ON genre_focus_weights TO anon;
GRANT SELECT ON genre_focus_weights TO authenticated;
GRANT EXECUTE ON FUNCTION refresh_genre_weights() TO anon;
