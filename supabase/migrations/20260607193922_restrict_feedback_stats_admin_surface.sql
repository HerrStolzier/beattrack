-- feedback_stats is an internal reporting surface now. Runtime recommendations
-- still use genre_focus_weights through the anon-backed API client.

revoke select on table public.feedback_stats from public, anon, authenticated;
grant select on table public.feedback_stats to service_role;
