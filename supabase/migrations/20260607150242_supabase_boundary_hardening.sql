-- Follow-up hardening from Supabase Advisor review.
-- Keep public app reads/writes explicit, but close internal maintenance surfaces.

-- Prevent future public-schema objects from becoming public by default.
alter default privileges for role postgres in schema public
  revoke select, insert, update, delete on tables from anon, authenticated;

alter default privileges for role postgres in schema public
  revoke execute on functions from public, anon, authenticated;

alter default privileges for role postgres in schema public
  revoke usage, select on sequences from anon, authenticated;

-- Minimize table/view grants to the currently intended public surface.
revoke all privileges on table public.analysis_jobs from anon, authenticated;
grant select, insert, update, delete on table public.analysis_jobs to service_role;

revoke all privileges on table public.ab_ctr_summary from anon, authenticated;
alter view if exists public.ab_ctr_summary set (security_invoker = true);

revoke all privileges on table public.songs from anon, authenticated;
grant select on table public.songs to anon;

revoke all privileges on table public.config from anon, authenticated;
grant select on table public.config to anon;

revoke all privileges on table public.feedback from anon, authenticated;
grant select, insert on table public.feedback to anon;

revoke all privileges on table public.click_events from anon, authenticated;
grant select, insert on table public.click_events to anon;

revoke all privileges on table public.feedback_stats from authenticated;
grant select on table public.feedback_stats to anon;

revoke all privileges on table public.genre_focus_weights from authenticated;
grant select on table public.genre_focus_weights to anon;

-- SECURITY DEFINER maintenance/import RPCs must not be publicly executable.
do $$
declare
  target_function record;
begin
  for target_function in
    select
      format('%I.%I(%s)', n.nspname, p.proname, pg_get_function_identity_arguments(p.oid)) as signature
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname in (
        'backfill_deezer_ids',
        'bulk_import_songs',
        'refresh_genre_weights',
        'sample_embeddings',
        'update_song_genre',
        'update_song_mert'
      )
  loop
    execute format(
      'revoke execute on function %s from public, anon, authenticated',
      target_function.signature
    );
    execute format(
      'grant execute on function %s to service_role',
      target_function.signature
    );
    execute format(
      'alter function %s set search_path = public, extensions',
      target_function.signature
    );
  end loop;
end $$;

-- Public feedback refresh is intentionally callable, but its search path must be fixed.
do $$
declare
  target_function record;
begin
  for target_function in
    select
      format('%I.%I(%s)', n.nspname, p.proname, pg_get_function_identity_arguments(p.oid)) as signature
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'refresh_feedback_stats'
  loop
    execute format(
      'alter function %s set search_path = public, extensions',
      target_function.signature
    );
  end loop;
end $$;
