# Plan: Beattrack Improvements Across Product, Quality, Operations, And Data

**Generated**: 2026-05-17  
**Estimated Complexity**: High

## Overview

Beattrack is already a working production-facing music discovery system. The next phase should focus on turning that technical foundation into a clearer, more reliable, easier-to-improve product.

The main recommendation is to improve in this order:

1. Stabilize the repo and operational baseline.
2. Make the core music-discovery experience clearer.
3. Measure and improve recommendation quality.
4. Harden external APIs, jobs, and auto-ingest.
5. Clean up data pipeline ownership and backfill strategy.
6. Improve observability and release confidence.

★ ʕ ᵔᴥᵔ ʔ Erklaerbaer  
In simple words: first make sure the house is tidy and the doors close properly. Then improve the main room where users spend time. After that, upgrade the engine under the floor.

## Prerequisites

- Keep production access to Supabase, Railway, and Vercel available.
- Decide which uncommitted files belong to the current work and which are local/runtime artifacts.
- Use small, independent commits; avoid mixing data files, product changes, and infra changes.
- Run `npm run check:prod-health` before and after deploy-sensitive work.

## Sprint 1: Repo Hygiene And Baseline

**Goal**: Make the working tree understandable, reduce accidental commits, and create a stable baseline for future work.

**Demo/Validation**:

- `git status --short` contains only intentional changes.
- Runtime/checkpoint/build artifacts are either ignored or intentionally committed.
- Backend tests still pass.
- Production health check still passes.

### Task 1.1: Sort The Current Working Tree

- **Location**: repository root
- **Description**: Review every modified/untracked file and classify it as one of: persistent analysis job work, intentional project doc, local runtime artifact, generated data, unrelated product change.
- **Dependencies**: none
- **Acceptance Criteria**:
  - A short commit plan exists.
  - Runtime artifacts are not accidentally staged.
  - User-made unrelated changes are not reverted.
- **Validation**:
  - `git status --short`
  - `git diff --stat`

### Task 1.2: Update `.gitignore` For Runtime Artifacts

- **Location**: `.gitignore`, `apps/api/.gitignore`, `apps/web/.gitignore`
- **Description**: Ignore local coverage files, generated checkpoints, temporary logs, build caches, and large generated analysis outputs where appropriate.
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - `apps/api/.coverage` is not shown as an untracked file after cleanup.
  - Script checkpoint files are either intentionally tracked or ignored by pattern.
  - `.next` and TypeScript build info are ignored if not already covered.
- **Validation**:
  - `git status --short`

### Task 1.3: Commit The Persistent Analysis Job Change

- **Location**:
  - `apps/api/app/routes/analyze.py`
  - `apps/api/app/services/analysis_jobs.py`
  - `apps/api/app/workers/__init__.py`
  - `apps/api/tests/test_analyze.py`
  - `supabase/migrations/023_analysis_jobs.sql`
  - `docs/analysis-jobs.md`
- **Description**: Commit the completed persistent analysis jobs change separately from future product work.
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - Commit contains only job persistence code, tests, migration, and direct docs.
  - Commit message is in English.
- **Validation**:
  - `cd apps/api && .venv/bin/python -m pytest -q`
  - `supabase db push --yes`

## Sprint 2: Music Discovery Focus And UX Clarity

**Goal**: Make the main user journey obvious and align the product around music explorers looking for less obvious songs that still feel right.

**Demo/Validation**:

- A new user can understand the primary action within 5 seconds: start from one seed track and dig outward.
- Upload/URL/search paths feel like one coherent flow.
- Secondary modes are available without competing with the main path.

### Task 2.1: Define The Primary Product Promise

- **Location**: `docs/product-direction.md`
- **Description**: Write a one-page product direction note that chooses music discovery as the primary promise for the next 4-6 weeks.
- **Dependencies**: none
- **Acceptance Criteria**:
  - Names the primary user as an electronic music explorer.
  - Names one primary job-to-be-done.
  - Lists non-goals for the next cycle.
- **Validation**:
  - Human review.

### Task 2.1b: Document The Researched Music Discovery Direction

- **Location**: `docs/music-discovery-direction.md`
- **Description**: Capture the "less obvious songs that still feel right" direction, including critical research findings about novelty, relevance, serendipity, and retention.
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - Documents product principles, ranking principles, UI principles, and non-goals.
  - Includes source-backed research notes.
  - Explicitly warns against optimizing for obscurity at the cost of relevance.
- **Validation**:
  - Human review.

### Task 2.2: Simplify First-Screen Hierarchy

- **Location**:
  - `apps/web/app/page.tsx`
  - `apps/web/app/components/analyze/IdlePhase.tsx`
  - `apps/web/app/components/UrlInput.tsx`
  - `apps/web/app/components/UploadZone.tsx`
- **Description**: Make the primary input path visually dominant and move Blend/Vibe/Journey into clearly secondary controls.
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - The main call to action is clear.
  - Secondary modes do not visually compete with the main path.
  - Mobile layout remains readable.
- **Validation**:
  - `cd apps/web && bun run test --run`
  - Browser check on desktop and mobile widths.

### Task 2.3: Improve Empty, Loading, And Failure States

- **Location**:
  - `apps/web/app/components/analyze/ProcessingPhase.tsx`
  - `apps/web/app/components/analyze/ResultsPhase.tsx`
  - `apps/web/app/hooks/useAnalyzeState.ts`
  - `apps/web/lib/api.ts`
- **Description**: Make external API failures, ingest-in-progress states, and analysis failures understandable in plain German.
- **Dependencies**: Sprint 4 error codes are useful but not mandatory.
- **Acceptance Criteria**:
  - User can tell whether retrying makes sense.
  - "Track not found" and "service temporarily unavailable" are visually and verbally distinct.
  - Processing state explains enough without sounding technical.
- **Validation**:
  - Component tests for error state branches.
  - Manual checks with mocked failed API responses.

## Sprint 3: Discovery Quality

**Goal**: Make discovery quality measurable and improve ranking with evidence.

**Demo/Validation**:

- There is a repeatable evaluation set.
- Ranking changes can be compared before/after.
- Bad recommendations can be categorized by why they missed.

### Task 3.1: Create A Discovery Golden Query Set

- **Location**:
  - `apps/api/scripts/eval_similarity.py`
  - `apps/api/scripts/fixtures/similarity_queries.json`
  - `docs/recommendation-quality.md`
- **Description**: Define a curated set of representative Electronic tracks with expected feeling, known-bad results, duplicate/version risks, and too-obvious examples.
- **Dependencies**: none
- **Acceptance Criteria**:
  - At least 30 query songs across subgenres.
  - Each query has notes for expected sonic traits, avoid traits, known-bad results, and discovery intent.
  - Evaluation script prints top results and basic metrics.
- **Validation**:
  - `cd apps/api && .venv/bin/python scripts/eval_similarity.py --limit 10`

**Status 2026-05-17**: Fixture expanded to 31 curated Electronic query songs. Each case includes expected traits, avoid traits, known-bad result patterns, too-obvious examples, duplicate/version risks, and a plain discovery intent note. Remaining work: add known-good neighbors after listening review and store real evaluation snapshots.

### Task 3.2: Log And Inspect Bad Matches

- **Location**:
  - `apps/api/app/routes/feedback.py`
  - `supabase/migrations/024_feedback_reason_tags.sql`
  - `apps/web/app/components/FeedbackButtons.tsx`
- **Description**: Let users or internal testers tag why a result is bad: wrong genre, wrong energy, too obvious, duplicate/remix, noisy metadata.
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - Feedback can include an optional reason.
  - Existing thumbs up/down still works.
  - Reasons are queryable in Supabase.
- **Validation**:
  - Backend feedback tests.
  - Frontend component tests.

**Status 2026-05-17**: Feedback requests can include reason tags, and `apps/api/scripts/report_feedback_reasons.py` now provides a read-only text or JSON summary over recent negative feedback reasons with suggested ranking checks per reason. Remaining work: run it with Supabase env vars, review dominant failure modes weekly, and connect repeated reasons to specific ranking experiments.

### Task 3.3: Tune Fusion Weights With Evaluation

- **Location**:
  - `apps/api/app/routes/similar.py`
  - `apps/api/tests/test_similarity_logic.py`
  - `docs/recommendation-quality.md`
- **Description**: Use the golden query set to compare current weights with alternatives for MusiCNN/MERT/handcrafted and focus modes.
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - Current baseline recorded.
  - At least 2 alternative weighting strategies tested.
  - Decision documented with examples.
- **Validation**:
  - Evaluation script output.
  - Existing similarity tests.

### Task 3.4: Prototype A Discovery Score

- **Location**:
  - `apps/api/scripts/eval_similarity.py`
  - `apps/api/app/routes/similar.py`
  - `docs/recommendation-quality.md`
- **Description**: Compare raw sonic similarity against a discovery score that includes duplicate/version penalties, same-artist/obviousness penalties, and energy drift penalties.
- **Dependencies**: Tasks 3.1, 3.2, 3.3
- **Acceptance Criteria**:
  - Production ranking remains unchanged until evaluation supports a switch.
  - Evaluation output can compare raw similarity and discovery-score rankings.
  - Decision notes include examples where the score helps and hurts.
- **Validation**:
  - `cd apps/api && .venv/bin/python scripts/eval_similarity.py --limit 10`

**Status 2026-05-17**: First conservative production version implemented in `apps/api/app/routes/similar.py`. It applies small same-artist, same-base-title, and too-close-result penalties after fusion and before dedup/MMR, and keeps internal penalty reasons for evaluation explainability. `apps/api/scripts/eval_similarity.py` can compare raw and discovery-scored rankings with `--score-mode both`, prints a short rank-change summary, flags 12+ BPM top-result drift for easier listening review, can persist compact JSON snapshots with fixture review notes and a top-level `review_summary` via `--snapshot-out`, supports quick smoke runs with `--query-limit`, and `apps/api/scripts/compare_eval_snapshots.py` can compare before/after review-summary deltas. Remaining work: compare live examples with Supabase env vars, decide whether BPM drift should become a live penalty, add richer energy/intensity drift only with evidence, and tune based on reason-tag feedback.

## Sprint 4: Jobs, External APIs, And Reliability

**Goal**: Make upload analysis and auto-ingest robust under restarts, temporary API failures, and rate limits.

**Demo/Validation**:

- Failed jobs have clear error codes.
- Retryable failures retry briefly.
- Permanent failures fail fast and clearly.
- `/analyze` status remains understandable.

### Task 4.1: Add Job Attempt Tracking

- **Location**:
  - `apps/api/app/services/analysis_jobs.py`
  - `apps/api/app/workers/__init__.py`
  - `apps/api/tests/test_analyze.py`
- **Description**: Increment `attempt_count` when workers start or retry, and store final error category.
- **Dependencies**: persistent analysis jobs already implemented.
- **Acceptance Criteria**:
  - `attempt_count` increases on processing attempts.
  - Failed jobs include `error_code` and `last_error`.
  - Completed jobs preserve `result`.
- **Validation**:
  - `cd apps/api && .venv/bin/python -m pytest tests/test_analyze.py -q`

### Task 4.2: Define External API Error Classes

- **Location**:
  - `apps/api/app/services/deezer.py`
  - `apps/api/app/services/spotify.py`
  - `apps/api/app/services/youtube.py`
  - `apps/api/app/services/soundcloud.py`
  - `apps/api/app/services/apple_music.py`
  - `apps/api/tests/test_*`
- **Description**: Standardize temporary unavailable, not found, invalid URL, and rate limit errors.
- **Dependencies**: none
- **Acceptance Criteria**:
  - Services raise or return consistent error categories.
  - Identify routes map categories to clear HTTP responses.
  - Frontend can display meaningful German messages.
- **Validation**:
  - Service-specific tests.
  - Identify route tests.

### Task 4.3: Add Short Retries For Retryable External Calls

- **Location**:
  - `apps/api/app/services/*`
  - `apps/api/app/services/ingest.py`
- **Description**: Add bounded retry with backoff for temporary network errors and 5xx responses, but not for not-found or invalid URL errors.
- **Dependencies**: Task 4.2
- **Acceptance Criteria**:
  - Retry count is small and bounded.
  - Rate limit response is not hammered.
  - Tests prove retryable and non-retryable branches.
- **Validation**:
  - Service unit tests with mocked HTTP responses.

## Sprint 5: Data Pipeline And Catalog Quality

**Goal**: Make the catalog strategy explicit and keep data growth from becoming messy.

**Demo/Validation**:

- There is one current data pipeline direction.
- Legacy scripts are clearly marked.
- Backfills can resume safely.
- Catalog quality metrics are visible.

### Task 5.1: Document Active Vs Legacy Data Sources

- **Location**:
  - `docs/data-pipeline.md`
  - `apps/api/scripts/README.md`
- **Description**: Document Deezer as active source, MERT/genre backfills as active maintenance, and FMA/Jamendo as legacy unless revived.
- **Dependencies**: none
- **Acceptance Criteria**:
  - Each script has a status: active, maintenance, legacy, experimental.
  - Required env vars are listed.
  - Dangerous commands are clearly marked.
- **Validation**:
  - Human review.

### Task 5.2: Add Catalog Health Queries

- **Location**:
  - `apps/api/scripts/catalog_health.py`
  - `docs/data-pipeline.md`
- **Description**: Create a read-only script that reports song count, missing genres, missing MERT, duplicate Deezer IDs, duplicate title/artist pairs, and normalization stats age.
- **Dependencies**: Task 5.1
- **Acceptance Criteria**:
  - Script is read-only by default.
  - Output is easy to paste into docs or issues.
- **Validation**:
  - `.venv/bin/python scripts/catalog_health.py`

### Task 5.3: Decide MERT Completion Strategy

- **Location**:
  - `docs/recommendation-quality.md`
  - `apps/api/scripts/extract_mert_batch.py`
- **Description**: Decide whether MERT is a must-have for all tracks, a partial re-rank signal, or a premium/quality subset.
- **Dependencies**: Task 3.1 and Task 5.2
- **Acceptance Criteria**:
  - Target coverage is documented.
  - Backfill cost and runtime are estimated.
  - Similarity fallback behavior is documented.
- **Validation**:
  - Catalog health output.
  - Evaluation output with/without MERT.

## Sprint 6: Backend Architecture Cleanup

**Goal**: Keep backend modules easier to test and safer to run in scripts.

**Demo/Validation**:

- Worker-adjacent scripts can import needed functions without initializing Procrastinate.
- Route files stay focused on HTTP behavior.
- Services own reusable logic.

### Task 6.1: Split Worker Business Logic From Procrastinate Registration

- **Location**:
  - `apps/api/app/workers/__init__.py`
  - `apps/api/app/workers/analysis.py`
  - `apps/api/app/workers/ingest_tasks.py`
  - `apps/api/tests/*`
- **Description**: Move task bodies into import-safe modules and leave Procrastinate decorators in a thin registration layer.
- **Dependencies**: Sprint 1 baseline commit
- **Acceptance Criteria**:
  - Scripts can import MERT/analysis helpers without importing Procrastinate.
  - Existing task names remain unchanged.
  - Tests do not need broad fake Procrastinate modules.
- **Validation**:
  - Backend test suite.
  - Import smoke tests for scripts.

### Task 6.2: Move Similarity Pure Logic Into A Service

- **Location**:
  - `apps/api/app/routes/similar.py`
  - `apps/api/app/services/similarity.py`
  - `apps/api/tests/test_similarity_logic.py`
- **Description**: Keep HTTP validation in the route, move fusion/dedup/MMR pure logic into a service module.
- **Dependencies**: Task 3.1 is useful but not mandatory.
- **Acceptance Criteria**:
  - Route file is smaller and easier to scan.
  - Pure logic has direct unit tests.
  - API behavior is unchanged.
- **Validation**:
  - `cd apps/api && .venv/bin/python -m pytest tests/test_similarity_logic.py -q`

## Sprint 7: Observability And Release Confidence

**Goal**: Make production failures easier to detect and diagnose.

**Demo/Validation**:

- Health checks cover API, Supabase, and at least one lightweight similarity path.
- Job failures can be inspected quickly.
- Release checklist is documented.

### Task 7.1: Expand Production Health Check

- **Location**:
  - `scripts/check_production_health.mjs`
  - `docs/project-status.md`
- **Description**: Add optional checks for `/songs/count/total`, a small `/songs` query, and `analysis_jobs` existence through Supabase metadata or a safe read.
- **Dependencies**: none
- **Acceptance Criteria**:
  - Script remains safe and read-only.
  - Failures identify which subsystem is degraded.
- **Validation**:
  - `npm run check:prod-health`

### Task 7.2: Add Job Failure Inspection Script

- **Location**:
  - `apps/api/scripts/analysis_jobs_report.py`
  - `docs/analysis-jobs.md`
- **Description**: Print recent failed/stuck jobs grouped by error code and age.
- **Dependencies**: `analysis_jobs` table
- **Acceptance Criteria**:
  - Script is read-only.
  - Output is concise enough for debugging.
- **Validation**:
  - `.venv/bin/python scripts/analysis_jobs_report.py`

### Task 7.3: Write A Release Checklist

- **Location**: `docs/release-checklist.md`
- **Description**: Document pre-deploy checks, migration order, deploy verification, and rollback notes for Railway/Vercel/Supabase.
- **Dependencies**: none
- **Acceptance Criteria**:
  - Includes frontend, backend, DB, and health check steps.
  - Includes what not to do when the working tree is dirty.
- **Validation**:
  - Human review.

## Sprint 8: Frontend Maintainability

**Goal**: Keep the rich UI from becoming hard to change.

**Demo/Validation**:

- State logic is easier to test.
- Main phases have narrower responsibilities.
- UI tests cover the most important paths.

### Task 8.1: Split `useAnalyzeState` Into Focused Hooks

- **Location**:
  - `apps/web/app/hooks/useAnalyzeState.ts`
  - `apps/web/app/hooks/useUploadAnalysis.ts`
  - `apps/web/app/hooks/useUrlIdentify.ts`
  - `apps/web/app/hooks/usePlaylistState.ts`
- **Description**: Separate upload, identify, playlist, and multi-search logic while preserving the public shape consumed by `AnalyzeView`.
- **Dependencies**: Sprint 2 is useful before this refactor.
- **Acceptance Criteria**:
  - Behavior remains unchanged.
  - Each hook has a narrower responsibility.
  - Existing tests pass.
- **Validation**:
  - `cd apps/web && bun run test --run`
  - `cd apps/web && bunx tsc --noEmit`

### Task 8.2: Add Tests For URL Identify And Ingest Retry UX

- **Location**:
  - `apps/web/__tests__/AnalyzeView.test.tsx`
  - `apps/web/__tests__/UrlInput.test.tsx`
  - `apps/web/app/hooks/useAnalyzeState.ts`
- **Description**: Cover matched URL, no match, ingesting, retry success, and retry give-up states.
- **Dependencies**: Task 8.1 optional
- **Acceptance Criteria**:
  - Tests prove the user sees the right state for each branch.
  - Timers are controlled in tests.
- **Validation**:
  - `cd apps/web && bun run test --run AnalyzeView`

## Testing Strategy

- Backend behavior: pytest focused tests first, then full backend suite.
- Frontend behavior: Vitest component/hook tests, then TypeScript check.
- Database changes: `supabase db push --yes`, then read-only verification queries.
- Production-sensitive changes: `npm run check:prod-health` before and after deploy.
- Recommendation changes: run a repeatable evaluation set before changing weights.

## Potential Risks And Gotchas

- **Dirty working tree**: The repo currently has many modified/untracked files. Mitigation: sort and commit before large changes.
- **Migration drift**: Supabase history was repaired to `001`-`023`. Mitigation: use `supabase migration list --linked` before future DB work.
- **External API behavior changes**: YouTube/Spotify/SoundCloud/Deezer behavior can change. Mitigation: explicit error categories and small retry wrappers.
- **Feature overload**: Blend, Vibe, Journey, Playlist, Focus, and Upload all compete for attention. Mitigation: choose one primary product promise per cycle.
- **Recommendation changes are subjective**: "Better" needs examples. Mitigation: golden query set and feedback reason tags.
- **Data files can bloat the repo**: Checkpoint and JSONL files should be intentionally tracked or ignored.

## Rollback Plan

- Product/UI changes: revert frontend commits and redeploy Vercel.
- Backend route/service changes: revert commit and redeploy Railway.
- Database migrations: write explicit rollback migration; avoid manual destructive changes.
- Recommendation ranking changes: keep old weights documented and feature-flag new weights if risk is high.
- Data pipeline changes: run scripts in dry-run/read-only mode before `--apply`.

## Suggested Priority

The best next sequence is:

1. Sprint 1: Repo Hygiene And Baseline.
2. Sprint 2: Product Focus And UX Clarity.
3. Sprint 3: Recommendation Quality.
4. Sprint 4: Jobs, External APIs, And Reliability.

The rest can follow once the core product path and quality loop are clearer.
