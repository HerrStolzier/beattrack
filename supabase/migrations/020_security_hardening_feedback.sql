-- Migration 020: Security hardening for feedback & click_events

-- Fix 1: Revoke refresh_genre_weights from anon
REVOKE EXECUTE ON FUNCTION refresh_genre_weights() FROM anon;

-- Fix 2: Replace overly permissive click_events insert policy with validated one
DROP POLICY IF EXISTS click_events_insert_anon ON click_events;

CREATE POLICY click_events_insert_validated ON click_events FOR INSERT TO anon
  WITH CHECK (
    length(session_hash) <= 20
    AND action IN ('play', 'spotify', 'youtube', 'playlist', 'similar', 'feedback_up', 'feedback_down')
    AND (result_rank IS NULL OR (result_rank > 0 AND result_rank <= 200))
  );

-- Fix 9: Composite index for A/B analytics
CREATE INDEX IF NOT EXISTS idx_click_events_ab_action ON click_events (ab_group, action, created_at);
