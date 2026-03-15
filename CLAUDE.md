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
- `apps/api/scripts/` — Seeding, Import, Normalisierung
- `supabase/migrations/` — SQL Migrations (001–010)
- `docs/scaling-plan.md` — Skalierungsstrategie + Kosten

## API Routes
`songs`, `similar`, `feedback`, `analyze`, `identify` — Health-Check: `GET /health`

## Database Schema
- **songs**: `id`, `title`, `artist`, `album`, `duration_sec`, `bpm`, `musical_key`, `learned_embedding` (vector 200d), `handcrafted_raw` (vector 44d), `handcrafted_norm` (vector 44d), `source`, `genre`, `release_year`
- **config**: Key-Value-Store (`normalization_stats` JSON mit mean/std/dim/n_songs)
- **feedback**: Rating (-1/+1), nur Analytics — nicht in Similarity eingebaut
- **Indexes**: HNSW auf `learned_embedding` + `handcrafted_norm` (cosine_ops, m=16, ef=64), Trigram (gin) auf title+artist, B-tree auf genre
- **RLS**: Enabled auf allen Tabellen (anon=SELECT, service_role=ALL)

## Data Scope (Iteration 1)
- **Genre**: Nur Electronic (13 Sub-Genres: Techno, House, IDM, Glitch, Minimal Electronic, Dance, Downtempo, Chill-out, Dubstep, Drum & Bass, Jungle, Bigbeat, Electronic)
- **Excluded**: Trip-Hop, Skweee, Chiptune, Chip Music, Breakcore-Hard, Ambient Electronic
- **Jahr**: >= 2000
- **Aktuell**: ~21.586 Songs (FMA-large)

## Deployment
- Railway: Root Directory `/apps/api`, Config `/apps/api/railway.toml`, Healthcheck `/health` (30s timeout), Restart ON_FAILURE (max 3)
- Vercel: Auto-deploy von `main`, `NEXT_PUBLIC_API_URL` zeigt auf Railway
- Supabase: Migrations via MCP oder `supabase db push`
- Deploy-Status prüfen: `/deploy-check` (Config in `.claude/deploy.json`)

## Environment Variables (Backend)
- `DATABASE_URL` — Supabase PostgreSQL Connection String (required)
- `SUPABASE_URL` + `SUPABASE_ANON_KEY` — Supabase Client (required)
- `ACOUSTID_API_KEY` — Song-Identifikation via AcoustID (required)
- `CORS_ORIGINS` — Erlaubte Origins (default: beattrack.vercel.app + localhost:3000)
- `SUPABASE_DB_URL` — Procrastinate-Connection (port 6543 Supavisor, optional fallback: DATABASE_URL)
- `SENTRY_DSN` — Error-Tracking (optional)

## Entwicklung
- `cd apps/api && uvicorn app.main:app --reload` — Backend lokal
- `cd apps/web && bun dev` — Frontend lokal
- Backend-Tests: `cd apps/api && pytest`
- Frontend-Tests: `cd apps/web && bun test` (Vitest, nicht Jest)

## Seeding & Maintenance Scripts
Alle in `apps/api/scripts/`, ausführen mit `.venv/bin/python`:
- **seed_fma.py** — Feature-Extraktion aus FMA-Audio (`--extract-only` für JSONL ohne DB, `--resume` für Checkpoint)
- **import_features.py** — JSONL → Supabase via REST RPC (braucht `--url` + `--key`, kein service_role_key nötig)
- **compute_stats.py** — Z-Score Stats berechnen + normalisieren (generiert SQL, `--format sql` für stdout)
- **cleanup_genres.py** — Songs nach Genre/Jahr filtern und nicht-matchende löschen (`--execute` für echtes Löschen)

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
- **Procrastinate**: `listen_notify=False` (Polling-Mode, spart 1 DB-Connection)
- **pgvector Subscripting**: `vector`-Typ unterstützt kein `[]` — erst `::text` dann `replace([→{, ]→})::float8[]`
- **Dockerfile**: Runtime braucht `ffmpeg` + `libmagic1`
