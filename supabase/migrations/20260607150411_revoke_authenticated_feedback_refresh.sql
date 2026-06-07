-- The app does not use Supabase Auth roles for feedback refresh.
-- Keep the public feedback refresh callable by anon only.

revoke execute on function public.refresh_feedback_stats() from public, authenticated;
grant execute on function public.refresh_feedback_stats() to anon;
