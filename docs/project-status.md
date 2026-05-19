# Beattrack Project Status

Last reviewed: 2026-05-19

## Summary

Beattrack is a production-facing music discovery system for finding songs that sound alike. It combines a Next.js frontend, a FastAPI backend, Supabase/Postgres with pgvector, and Procrastinate background jobs.

The project is past the simple prototype stage. It already has user-facing workflows, asynchronous audio analysis, external music API integrations, vector similarity search, feedback collection, CI, production health checks, and a real deployment footprint.

## Product Shape

The core promise is sonic discovery:

1. A user starts from a known track, URL, or uploaded audio.
2. Beattrack identifies or analyzes the track.
3. The backend searches the vector database for songs with similar sound.
4. The frontend presents similar tracks with optional focus modes, journeys, blends, vibes, and playlist tools.

Current product modes:

- Upload an audio file and analyze it.
- Identify tracks from YouTube, SoundCloud, Spotify, Apple Music, or Deezer URLs.
- Search for similar songs from a known catalog song.
- Use Focus categories: timbre, harmony, rhythm, brightness, intensity.
- Blend two songs into a centroid-style query.
- Search a Vibe from 2-5 seed songs.
- Continue discovery through Sonic Journey.
- Build a local playlist and use DJ-oriented harmonic/BPM cues.

## Repository Layout

- `apps/web/` — Next.js 15 frontend.
- `apps/api/` — FastAPI backend and worker code.
- `apps/api/scripts/` — long-running data, seeding, backfill, and maintenance scripts.
- `supabase/migrations/` — numbered Supabase migrations, currently `001` through `023`.
- `docs/` — project status, scaling, job lifecycle, improvement plans, and durable learnings.
- `.github/workflows/` — CI and secret scanning.
- `scripts/check_production_health.mjs` — production API/Supabase/catalog/job-table health check.

## Frontend

Stack:

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS v4
- framer-motion
- Vitest

Important files:

- `apps/web/app/page.tsx` — app shell and first screen.
- `apps/web/app/components/AnalyzeView.tsx` — central product flow.
- `apps/web/app/hooks/useAnalyzeState.ts` — main client-side state machine.
- `apps/web/app/hooks/usePersistentPlaylist.ts` — playlist localStorage persistence.
- `apps/web/lib/api.ts` — API client, retries, analysis/identify/similarity calls.
- `apps/web/app/components/analyze/*` — split phase components for idle, processing, results, history, and playlist panel.

Frontend strengths:

- Rich feature set for discovery: upload, URL identify, blend, vibe, journey, playlist.
- German UI language is mostly consistent.
- Tests exist for key components.
- API client already has retry and timeout handling for common failures.

Frontend risks:

- `useAnalyzeState.ts` carries many workflows in one hook. This is still manageable, but future features may make it harder to reason about.
- The product offers many modes at once. The main user path should stay visually and conceptually dominant.
- Local linting is known to be brittle because of workspace/Next/Bun hoisting details.

## Backend

Stack:

- Python 3.12
- FastAPI
- Essentia / TensorFlow models
- Chromaprint / pyacoustid
- Supabase Python client
- Procrastinate
- slowapi rate limiting
- pytest

Important files:

- `apps/api/app/main.py` — FastAPI app, CORS, security headers, health check, cleanup.
- `apps/api/app/routes/analyze.py` — audio upload, persistent analysis job creation, SSE/polling.
- `apps/api/app/services/analysis_jobs.py` — persistence helpers for `analysis_jobs`.
- `apps/api/app/workers/__init__.py` — Procrastinate app setup and task registration.
- `apps/api/app/workers/analysis.py` — import-safe upload analysis task logic.
- `apps/api/app/workers/ingest_tasks.py` — import-safe Deezer ingest task logic.
- `apps/api/app/routes/similar.py` — similarity, blend, and vibe HTTP routes.
- `apps/api/app/services/similarity.py` — fusion, discovery scoring, deduplication, MMR, and shared ranking helpers.
- `apps/api/app/routes/identify.py` — external URL identification and auto-ingest trigger.
- `apps/api/app/services/ingest.py` — Deezer preview ingestion and neighbor expansion.
- `apps/api/app/services/features.py` — feature extraction and normalization helpers.

Backend strengths:

- Clear route split by domain.
- Upload validation and isolated feature extraction reduce risk.
- Persistent analysis jobs now survive process restarts and multi-instance routing.
- Similarity logic goes beyond plain nearest-neighbor search with late fusion, MERT, handcrafted features, dedup, and diversity.
- Tests cover many API and service paths.

Backend risks:

- External API failure handling is still uneven. Some errors are permanent, some retryable, and some rate-limit related; the code should make these classes explicit.
- Worker retry behavior is still basic. `analysis_jobs.attempt_count` exists but is not yet fully used.
- Procrastinate registration is now thinner, but future worker features should keep business logic in import-safe modules rather than growing `workers/__init__.py` again.
- Auto-ingest is useful but operationally sensitive because Deezer preview URLs expire and external APIs can be flaky.

## Database And Data

Database:

- Supabase Postgres in Central EU.
- pgvector for embeddings.
- pg_trgm for fuzzy title/artist matching.
- RLS enabled on public tables.

Core tables:

- `songs`
- `config`
- `feedback`
- `click_events`
- `analysis_jobs`

Key embedding fields:

- `learned_embedding` — 200-dimensional MusiCNN vector.
- `handcrafted_norm` / `handcrafted_raw` — 44-dimensional handcrafted audio features.
- `mert_embedding` — 768-dimensional MERT vector for re-ranking where available.

Current data posture:

- The active scope is Electronic music.
- Current documentation notes roughly 121K songs.
- Deezer is the active commercial preview-backed source.
- FMA/Jamendo scripts still exist but are legacy/inactive for the current direction.
- Genre and MERT backfills are part of the ongoing data quality work.

## Deploy And Operations

Production shape:

- Frontend: Vercel.
- Backend: Railway, root `apps/api`, health check `/health`.
- Database: Supabase project `qpkemujemfnymtgmtkfg`.

Current production check:

```bash
npm run check:prod-health
```

The production check covers:

- Railway API `/health`.
- API song count endpoint.
- API lightweight song search.
- Supabase REST config read for `normalization_stats`.
- Supabase REST read against `analysis_jobs`.

Migration state:

- Local and remote Supabase migration history is aligned on `001` through `023`.
- `supabase db push --yes` reports the remote database is up to date.
- `023_analysis_jobs.sql` has been applied.

## Quality And CI

CI includes:

- Backend pytest.
- Backend dependency audit with `pip-audit`.
- Frontend lint, type check, build, and Vitest coverage.
- Gitleaks secret scanning.

Useful local checks:

```bash
cd apps/api && .venv/bin/python -m pytest -q
cd apps/api && .venv/bin/python -m ruff check app tests
cd apps/web && bun run test
cd apps/web && bunx tsc --noEmit
npm run check:prod-health
```

## Current Working Tree Note

As of this review, the active local changes are intentional roadmap execution
work: recommendation evaluation notes, worker cleanup, and a small frontend
maintainability cut. Before unrelated work, commit or discard these changes so
future diffs stay easy to review.

## Strategic Assessment

Beattrack's next phase is less about proving the idea and more about sharpening it.

The highest-leverage questions are:

1. What is the primary product path: fast similar-track lookup, DJ discovery, playlist building, or exploratory sonic journeys?
2. How will recommendation quality be measured beyond "looks good"?
3. How much operational complexity should auto-ingest and backfills be allowed to add?
4. What data growth target matters next: 150K, 500K, or quality before quantity?

See `docs/beattrack-improvement-plan.md` for a proposed improvement plan across product, recommendation quality, operations, data, frontend, backend, testing, and repo hygiene.
