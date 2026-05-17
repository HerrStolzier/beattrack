# Beattrack

[![CI](https://github.com/HerrStolzier/beattrack/actions/workflows/ci.yml/badge.svg)](https://github.com/HerrStolzier/beattrack/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)](https://www.typescriptlang.org/)

Find songs that sound alike — sonic similarity search powered by audio fingerprinting and vector embeddings.

Beattrack is a music discovery app for finding songs that sound similar, not just songs with matching metadata. Users can search by URL, upload audio, blend multiple songs, explore a sonic journey, and build playlists from similarity results.

## Current Status

Production is live across Vercel, Railway, and Supabase.

- **Frontend:** Next.js app at `apps/web`
- **Backend:** FastAPI app at `apps/api`
- **Database:** Supabase Postgres with pgvector
- **Jobs:** Procrastinate on Postgres
- **Primary data scope:** Electronic music, Deezer-backed ingest and backfill
- **Current operational check:** `npm run check:prod-health`

For a fuller project snapshot, see [`docs/project-status.md`](./docs/project-status.md).

## Stack

- **Frontend:** Next.js 15, React 19, TypeScript, Tailwind CSS v4, framer-motion
- **Backend:** FastAPI, Python 3.12, Essentia, Chromaprint/pyacoustid
- **Database:** Supabase PostgreSQL, pgvector, pg_trgm
- **Job Queue:** Procrastinate
- **Monorepo:** Bun workspaces, uv for Python

## Development

```bash
bun install
bun run dev        # Frontend (apps/web)
```

```bash
cd apps/api
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

## Main Features

- URL identification for YouTube, SoundCloud, Spotify, Apple Music, and Deezer
- Audio upload and asynchronous analysis
- Single-song sonic similarity search
- Focus modes for timbre, harmony, rhythm, brightness, and intensity
- Sonic Blend for two seed songs
- Vibe search for 2-5 seed songs
- Sonic Journey and playlist-building UI
- Deezer auto-ingest for missing tracks when a preview is available

## Testing

```bash
cd apps/web && bun run test
cd apps/api && uv run pytest
```

## Operations

```bash
npm run check:prod-health
```

Useful docs:

- [`docs/project-status.md`](./docs/project-status.md) — current architecture and project state
- [`docs/beattrack-improvement-plan.md`](./docs/beattrack-improvement-plan.md) — proposed next improvements
- [`docs/analysis-jobs.md`](./docs/analysis-jobs.md) — persistent `/analyze` job lifecycle
- [`docs/scaling-plan.md`](./docs/scaling-plan.md) — scaling and data growth notes
- [`docs/project-learnings.md`](./docs/project-learnings.md) — durable implementation gotchas

## License

AGPL-3.0 — see [LICENSE](./LICENSE)
