-- Enable Row Level Security on all public tables
-- Fixes: Supabase Security Advisor errors for songs, config, feedback

-- ============================================================
-- 1. SONGS — read-only for anon, writes via service_role / direct DB
-- ============================================================
ALTER TABLE public.songs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "songs_select_anon"
    ON public.songs FOR SELECT
    TO anon
    USING (true);

CREATE POLICY "songs_all_service"
    ON public.songs FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- 2. CONFIG — read-only for anon, writes via service_role / direct DB
-- ============================================================
ALTER TABLE public.config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "config_select_anon"
    ON public.config FOR SELECT
    TO anon
    USING (true);

CREATE POLICY "config_all_service"
    ON public.config FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- 3. FEEDBACK — insert-only for anon, full access for service_role
-- ============================================================
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "feedback_insert_anon"
    ON public.feedback FOR INSERT
    TO anon
    WITH CHECK (true);

CREATE POLICY "feedback_all_service"
    ON public.feedback FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- 4. FUNCTION search_path — fix "Function Search Path Mutable" warning
-- ============================================================
ALTER FUNCTION public.find_similar_songs(VECTOR(200), INT, UUID, FLOAT, FLOAT)
    SET search_path = public;
