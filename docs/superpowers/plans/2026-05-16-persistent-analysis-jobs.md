# Persistent Analysis Jobs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist `/analyze` job status in Supabase/Postgres so analysis jobs survive API restarts and can be read by any API instance.

**Architecture:** Replace the route-local `_job_status` dictionary with a small `analysis_jobs` database table and a focused Python service. The upload route creates a row, the Procrastinate worker updates that row, and polling/SSE endpoints read the row from Postgres.

**Tech Stack:** FastAPI, Supabase Python client, PostgreSQL/Supabase migrations, Procrastinate, pytest.

---

## File Map

- Create `supabase/migrations/023_analysis_jobs.sql`: database table, indexes, RLS policies.
- Create `apps/api/app/services/analysis_jobs.py`: small persistence service for create/read/update operations.
- Modify `apps/api/app/routes/analyze.py`: remove in-memory status tracking and read/write jobs through the service.
- Modify `apps/api/app/workers/__init__.py`: update jobs through the service instead of importing the API route.
- Modify `apps/api/tests/test_analyze.py`: replace memory-dict tests with persistent job service/route tests.
- Create `docs/analysis-jobs.md`: human-readable operating notes for the persistent analysis job flow.

## Task 1: Add Database Shape

**Files:**
- Create: `supabase/migrations/023_analysis_jobs.sql`
- Create: `docs/analysis-jobs.md`

- [x] **Step 1: Add migration**

Create `analysis_jobs` with status, progress, result, error, attempts, timestamps, and indexes.

```sql
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
```

- [x] **Step 2: Add operating documentation**

Document the new job lifecycle, what each status means, and how to debug a missing/stuck job.

- [x] **Step 3: Check migration syntax**

Run: `rg -n "analysis_jobs|Migration 023" supabase/migrations/023_analysis_jobs.sql docs/analysis-jobs.md`

Expected: both files contain the new table/lifecycle references.

## Task 2: Add Analysis Job Service With Tests

**Files:**
- Create: `apps/api/app/services/analysis_jobs.py`
- Modify: `apps/api/tests/test_analyze.py`

- [x] **Step 1: Write failing service tests**

Add tests that prove:

- `create_analysis_job()` inserts a queued row.
- `get_analysis_job()` returns data from Supabase.
- `update_analysis_job()` writes status, progress, result/error fields, and timestamps.
- A missing row returns `None`.

- [x] **Step 2: Run focused tests and confirm failure**

Run: `cd apps/api && pytest tests/test_analyze.py -q`

Expected before implementation: import or assertion failure for missing `analysis_jobs` service.

- [x] **Step 3: Implement service**

Create a small service that calls `get_supabase()` at runtime, uses Python UTC timestamps, and keeps route/worker code independent from Supabase query details.

- [x] **Step 4: Run focused tests**

Run: `cd apps/api && pytest tests/test_analyze.py -q`

Expected after implementation: service tests pass; route tests may still need updating in Task 3.

## Task 3: Move Routes From Memory To Persistence

**Files:**
- Modify: `apps/api/app/routes/analyze.py`
- Modify: `apps/api/tests/test_analyze.py`

- [x] **Step 1: Write failing route tests**

Update tests so unknown jobs are driven by a mocked persistent lookup, and completed/failed polling responses come from `analysis_jobs`.

- [x] **Step 2: Run focused tests and confirm failure**

Run: `cd apps/api && pytest tests/test_analyze.py -q`

Expected: tests fail because routes still read `_job_status`.

- [x] **Step 3: Replace route-local state**

Remove `_job_status`, `_JOB_TTL_SEC`, `_cleanup_stale_jobs()`, and `update_job_status()`. Use:

- `create_analysis_job()` after upload validation.
- `update_analysis_job()` if enqueue fails.
- `get_analysis_job()` in `/results` and `/stream`.

- [x] **Step 4: Run focused tests**

Run: `cd apps/api && pytest tests/test_analyze.py -q`

Expected: analyze route tests pass.

## Task 4: Move Worker Updates To Persistence

**Files:**
- Modify: `apps/api/app/workers/__init__.py`
- Modify: `apps/api/tests/test_analyze.py`

- [x] **Step 1: Write failing worker test**

Add a test that patches `update_analysis_job`, runs the worker path with patched feature extraction/result processing, and verifies `processing` then `completed` updates are written.

- [x] **Step 2: Run focused test and confirm failure**

Run: `cd apps/api && pytest tests/test_analyze.py -q`

Expected: test fails while the worker imports `update_job_status` from the route.

- [x] **Step 3: Replace worker import**

Change `from app.routes.analyze import update_job_status` to `from app.services.analysis_jobs import update_analysis_job`, and update error/success calls.

- [x] **Step 4: Run focused tests**

Run: `cd apps/api && pytest tests/test_analyze.py -q`

Expected: analyze and worker tests pass.

## Task 5: Final Verification

**Files:**
- All touched files.

- [x] **Step 1: Run focused backend tests**

Run: `cd apps/api && pytest tests/test_analyze.py -q`

Expected: all tests in `test_analyze.py` pass.

- [x] **Step 2: Run broader backend tests if environment supports it**

Run: `cd apps/api && pytest -q`

Expected: backend suite passes, or any unrelated environment/tooling failure is reported clearly.

- [x] **Step 3: Inspect diff**

Run: `git diff -- apps/api/app/routes/analyze.py apps/api/app/workers/__init__.py apps/api/app/services/analysis_jobs.py apps/api/tests/test_analyze.py supabase/migrations/023_analysis_jobs.sql docs/analysis-jobs.md docs/superpowers/plans/2026-05-16-persistent-analysis-jobs.md`

Expected: diff only contains the persistent analysis job change and docs.

## Self-Review

- Spec coverage: The plan covers persistent job storage, lifecycle statuses, worker updates, route polling/SSE reads, documentation, and tests.
- Placeholder scan: No TBD/TODO/fill-later placeholders.
- Type consistency: Job fields use `last_error`, `error_code`, `result`, `attempt_count`, `created_at`, `updated_at`, and `completed_at` consistently across SQL and Python.
