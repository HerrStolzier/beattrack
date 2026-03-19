-- Phase 3: A/B Testing Framework

CREATE TABLE IF NOT EXISTS click_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_hash TEXT NOT NULL,
  query_song_id UUID,
  result_song_id UUID,
  result_rank INT,
  ab_group TEXT NOT NULL,
  action TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_click_events_ab ON click_events (ab_group, created_at);
CREATE INDEX idx_click_events_session ON click_events (session_hash, created_at);

-- RLS: anon can insert + select
ALTER TABLE click_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY click_events_insert_anon ON click_events FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY click_events_select_anon ON click_events FOR SELECT TO anon USING (true);
CREATE POLICY click_events_all_service ON click_events FOR ALL TO service_role USING (true) WITH CHECK (true);

-- CTR analysis view
CREATE OR REPLACE VIEW ab_ctr_summary AS
SELECT
  ab_group,
  action,
  COUNT(*) as event_count,
  COUNT(DISTINCT session_hash) as unique_sessions,
  MIN(created_at)::date as first_event,
  MAX(created_at)::date as last_event
FROM click_events
GROUP BY ab_group, action;

GRANT SELECT ON ab_ctr_summary TO anon;
