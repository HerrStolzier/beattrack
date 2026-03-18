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
- `supabase/migrations/` — SQL Migrations (001–014)
- `docs/scaling-plan.md` — Skalierungsstrategie + Kosten

## API Routes
`songs`, `similar`, `feedback`, `analyze`, `identify` — Health-Check: `GET /health`
- `POST /similar` — Single-Song Similarity (mit optionalem `focus` + `exclude_ids`)
- `POST /similar/blend` — Centroid-Search zwischen 2 Songs
- `POST /similar/vibe` — Intersection-Search über 2–5 Seeds
- `POST /songs/features/batch` — Radar-Features für bis zu 30 Songs

## Database Schema
- **songs**: `id`, `title`, `artist`, `album`, `duration_sec`, `bpm`, `musical_key`, `learned_embedding` (vector 200d), `handcrafted_raw` (vector 44d), `handcrafted_norm` (vector 44d), `source`, `genre`, `release_year`, `deezer_id`
- **config**: Key-Value-Store (`normalization_stats` JSON mit mean/std/dim/n_songs)
- **feedback**: Rating (-1/+1), nur Analytics — nicht in Similarity eingebaut
- **Indexes**: HNSW auf `learned_embedding` + `handcrafted_norm` (cosine_ops, m=16, ef=64), Trigram (gin) auf title+artist, B-tree auf genre
- **RLS**: Enabled auf allen Tabellen (anon=SELECT, service_role=ALL)
- **RPC**: `bulk_import_songs(jsonb)` — SECURITY DEFINER, callable mit anon key (Migration 011)

## Data Scope
- **Genre**: Electronic (Sub-Genres: Techno, House, IDM, Minimal Electronic, Dance, Downtempo, Chill-out, Dubstep, Drum & Bass, Trance, Breakbeat, Ambient, Electronic)
- **Quelle**: Deezer API — kommerzielle Electronic-Tracks (30s Previews → Essentia-Extraktion)
- **Crawl-Strategie**: 105 Seed-Artists → Top-Tracks + Related Artists (2 Ebenen) mit Album-Genre-Filter
- **Aktuell**: ~175K kommerzielle Tracks
- **Legacy (inaktiv)**: FMA-large, MTG-Jamendo — Seeder-Scripts existieren noch in `scripts/`, werden nicht mehr verwendet

## Deployment
- Railway: Root Directory `/apps/api`, Config `/apps/api/railway.toml`, Healthcheck `/health` (30s timeout), Restart ON_FAILURE (max 3)
- Vercel: Auto-deploy von `main`, `NEXT_PUBLIC_API_URL` zeigt auf Railway
- Supabase: Migrations via MCP oder `supabase db push`
- Deploy-Status prüfen: `/deploy-check` (Config in `.claude/deploy.json`)

## Environment Variables (Backend)
- `DATABASE_URL` — Supabase PostgreSQL Connection String (required)
- `SUPABASE_URL` + `SUPABASE_ANON_KEY` — Supabase Client (required)
- `ACOUSTID_API_KEY` — Song-Identifikation via AcoustID (required)
- `CORS_ORIGINS` — Erlaubte Origins (default: beattrack.app + localhost:3000)
- `SUPABASE_DB_URL` — Procrastinate-Connection (port 6543 Supavisor, optional fallback: DATABASE_URL)
- `SENTRY_DSN` — Error-Tracking (optional)

## Entwicklung
- `cd apps/api && uvicorn app.main:app --reload` — Backend lokal
- `cd apps/web && bun dev` — Frontend lokal
- Backend-Tests: `cd apps/api && pytest`
- Frontend-Tests: `cd apps/web && bun test` (Vitest, nicht Jest)

## Seeding & Maintenance Scripts
Alle in `apps/api/scripts/`, ausführen mit `.venv/bin/python`:
- **seed_deezer.py** — Deezer Electronic-Crawl + Essentia-Extraktion (`--crawl-only`, `--tracks-json`, `--resume`, `--workers`)
- **import_features.py** — JSONL → Supabase via REST RPC (braucht `--url` + `--key`, kein service_role_key nötig)
- **compute_stats.py** — Z-Score Stats berechnen + normalisieren (generiert SQL, `--format sql` für stdout)
- **cleanup_genres.py** — Songs nach Genre/Jahr filtern und löschen (`--execute`)
- **seed_fma.py** / **seed_jamendo.py** — Legacy-Seeder (nicht mehr aktiv)

## Similarity Engine
- **Dual Embeddings**: MusiCNN 200d (learned) + 44d handcrafted, Late Fusion (80/20 Default)
- **Handcrafted 44-dim Layout**: MFCC mean [0:13], MFCC stdev [13:26], HPCP [26:38], Spectral Centroid [38], Spectral Rolloff [39], BPM [40], ZCR [41], Avg Loudness [42], Danceability [43]
- **5 Radar-Kategorien**: Timbre (dims 0–25), Harmony (dims 26–37), Rhythm (dims 40,43), Brightness (dims 38,39), Intensity (dims 41,42)
- **Focus-Mode**: Gewichtung verschiebt sich auf 60/40 (learned/handcrafted) für gewählte Kategorie
- **Blend**: Embedding-Centroid zwischen 2 Songs → Nearest Neighbors
- **Vibe**: Intersection-Search über 2–5 Seeds (min. 2 Treffer-Overlap, Fallback auf Centroid)

## Frontend Features
- **Sonic Journey**: Chain Discovery mit Visited-Filter, Gamification (Distance, Genres)
- **Focus Selector**: Feature-gewichtete Ähnlichkeit (5 Kategorien als Chips)
- **Sonic Blend / Vibe**: Multi-Song Query UI (2 Songs für Blend, 2–5 für Vibe)
- **Playlist Builder**: Drag & Drop, Sonic Flow Chart (BPM + Intensity), Copy-to-Clipboard
- **DJ Mode**: Camelot-Wheel Harmonic Compatibility + BPM-Differenz als optionaler Layer
- **A/B Radar Toggle**: Vergleich / Query / Result Ansichten im RadarChart
- **Deep-Link**: `?url=YOUTUBE_URL` + Bookmarklet (YouTube, SoundCloud, Spotify, Apple Music)
- **Deezer Embed**: Inline-Player für Songs mit `deezer_id`

## Konventionen
- Essentia läuft in isoliertem Subprocess (Crash-Schutz)
- Normalisierung via Z-Score aus `config`-Tabelle
- URL-Identify: YouTube oEmbed, SoundCloud oEmbed, Spotify oEmbed+OG-Scraping, Apple Music iTunes API
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
- **Deezer Preview URLs**: HMAC-signiert, ~10min TTL — vor jedem Download frische URL via `/track/{id}` holen
- **Dockerfile**: Runtime braucht `ffmpeg` + `libmagic1`
- **Spotify oEmbed**: Liefert keinen `author_name` — Artist muss via OG-Tag (`og:description`) von der Track-Page gescrapt werden (Pattern: `"Artist · Album · Song · Year"`)
- **Essentia Extraction**: Kann bei `--workers >1` in Multiprocessing-Deadlock geraten (POSIX Semaphores). Fix: Prozess killen + `--resume`

## Security
- **Rate Limiting**: slowapi auf `/analyze` (10/min), `/identify/*` (20/min), `/feedback` (30/min)
- **HTTP Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options via `next.config.ts`
- **CORS**: Eingeschränkt auf GET/POST/OPTIONS, explizite Headers
- **SSRF-Schutz**: YouTube URL-Validation via `urlparse` Host-Check (nicht Substring)
- **RLS**: Enabled auf allen Tabellen (anon=SELECT, service_role=ALL)

## SEO
- `sitemap.ts` + `robots.ts` im App-Root
- Open Graph + Twitter Cards in `layout.tsx` Metadata
- JSON-LD WebApplication Schema
- Canonical URL: `https://beattrack.app`
