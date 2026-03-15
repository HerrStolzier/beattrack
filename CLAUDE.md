# Beattrack

Sonically similar song finder — findet Songs die ähnlich klingen.

## Stack
- **Frontend**: Next.js 15 + TypeScript + TailwindCSS v4 + framer-motion → Vercel
- **Backend**: Python 3.12+ FastAPI + Essentia → Railway (Dockerfile)
- **Database**: Supabase PostgreSQL + pgvector (eu-central-1)
- **Job Queue**: Procrastinate (Postgres-based, kein Redis)
- **Build-Tools**: Bun (Frontend/Vercel), uv (Python/Backend)

## Monorepo-Struktur
- `apps/web/` — Next.js Frontend
- `apps/api/` — FastAPI Backend
- `supabase/migrations/` — SQL Migrations

## Deployment
- Railway: Root Directory `/apps/api`, Config `/apps/api/railway.toml`
- Vercel: Auto-deploy von `main`, `NEXT_PUBLIC_API_URL` zeigt auf Railway
- Supabase: Migrations via MCP oder `supabase db push`
- Deploy-Status prüfen: `/deploy-check` (Config in `.claude/deploy.json`)

## Environment Variables (Backend)
- `DATABASE_URL` — Supabase PostgreSQL Connection String (required)
- `SUPABASE_URL` + `SUPABASE_ANON_KEY` — Supabase Client (required)
- `ACOUSTID_API_KEY` — Song-Identifikation via AcoustID (required)
- `CORS_ORIGINS` — Erlaubte Origins (default: beattrack.vercel.app + localhost:3000)
- `SENTRY_DSN` — Error-Tracking (optional)

## Entwicklung
- `cd apps/api && uvicorn app.main:app --reload` — Backend lokal
- `cd apps/web && bun dev` — Frontend lokal
- Backend-Tests: `cd apps/api && pytest`
- Frontend-Tests: `cd apps/web && bun test` (Vitest, nicht Jest)

## Konventionen
- Essentia läuft in isoliertem Subprocess (Crash-Schutz)
- Dual Embeddings: MusiCNN 200d (learned) + 44d handcrafted
- Normalisierung via Z-Score aus `config`-Tabelle
- URL-Identify: YouTube oEmbed, SoundCloud oEmbed, Spotify Web API
- Commit-Messages auf Englisch, UI-Texte auf Deutsch

## Gotchas
- **Tailwind v4**: Config komplett in `globals.css` via `@theme` — kein `tailwind.config.ts`
- **ESLint**: Beim Build disabled (`next.config.ts`) wegen Workspace-Hoisting
- **API Concurrency**: Upload-Semaphore (max 3), SSE-Limiter (max 50 Connections)
- **Subprocess Exit-Codes**: 0=OK, 1=bad args, 2=model missing, 3=extraction error
- **Supabase Client**: Gecached via `@lru_cache(maxsize=1)` in `app/db.py`
- **React 19 SSR + framer-motion**: Animierte Komponenten mit dynamischen Inline-Styles brauchen Client-only Rendering (`useState(false)` + `useEffect`) — React 19 serialisiert Style-Properties unterschiedlich (kebab vs camelCase)
- **framer-motion**: Im Root `node_modules` gehoisted (Monorepo) — nicht in `apps/web/node_modules`
