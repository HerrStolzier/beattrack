-- Migration 023: Persistent status for uploaded audio analysis jobs

CREATE TABLE IF NOT EXISTS public.analysis_jobs (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    progress DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (progress >= 0 AND progress <= 1),
    audio_path TEXT,
    duration_sec DOUBLE PRECISION,
    result JSONB,
    last_error TEXT,
    error_code TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0
        CHECK (attempt_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status
    ON public.analysis_jobs(status);

CREATE INDEX IF NOT EXISTS idx_analysis_jobs_created_at
    ON public.analysis_jobs(created_at DESC);

ALTER TABLE public.analysis_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "analysis_jobs_all_service"
    ON public.analysis_jobs FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
