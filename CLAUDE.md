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
- `supabase/migrations/` — SQL Migrations (001–022+)
- `docs/scaling-plan.md` — Skalierungsstrategie + Kosten

## API Routes
`songs`, `similar`, `feedback`, `analyze`, `identify` — Health-Check: `GET /health`
- `POST /similar` — Single-Song Similarity (mit optionalem `focus` + `exclude_ids`)
- `POST /similar/blend` — Centroid-Search zwischen 2 Songs
- `POST /similar/vibe` — Intersection-Search über 2–5 Seeds
- `POST /songs/features/batch` — Radar-Features für bis zu 30 Songs

## Auto-Ingest
- Bei Identify-Miss: Deezer-API-Suche → Preview-Download → Essentia-Extraktion → DB-Insert (async via Procrastinate)
- Neighbor-Expansion: Nach Ingest werden ~10 Top-Tracks des gleichen Artists im Hintergrund ingestiert
- Procrastinate-Tasks: `ingest_from_deezer`, `ingest_neighbors` (in `app/workers/__init__.py`)

## Database Schema
- **songs**: `id`, `title`, `artist`, `album`, `duration_sec`, `bpm`, `musical_key`, `learned_embedding` (vector 200d), `handcrafted_raw` (vector 44d), `handcrafted_norm` (vector 44d), `mert_embedding` (vector 768d), `source`, `genre`, `release_year`, `deezer_id`
- **config**: Key-Value-Store (`normalization_stats` JSON mit mean/std/dim/n_songs)
- **feedback**: Rating (-1/+1), Feedback Learning System (Feature Importance per Genre)
- **click_events**: CTR-Tracking für A/B-Testing (action, result_rank, ab_group)
- **Indexes**: HNSW auf `learned_embedding` (m=24, ef_construction=128, ef_search=200), Trigram (gin) auf title+artist, Unique auf `(lower(title), lower(artist))`
- **RLS**: Enabled auf allen Tabellen (anon=SELECT+INSERT feedback, service_role=ALL)
- **RPC**: `bulk_import_songs`, `find_similar_songs`, `update_song_genre`, `update_song_mert`, `sample_embeddings` — alle SECURITY DEFINER
- **Supabase Project-ID**: `qpkemujemfnymtgmtkfg` (für MCP-Calls und CLI)

## Data Scope
- **Genre**: Electronic (Sub-Genres: Techno, House, IDM, Minimal Electronic, Dance, Downtempo, Chill-out, Dubstep, Drum & Bass, Trance, Breakbeat, Ambient, Electronic)
- **Quelle**: Deezer API — kommerzielle Electronic-Tracks (30s Previews → Essentia-Extraktion)
- **Crawl-Strategie**: 424 Seed-Artists → Top-Tracks + Related Artists (Tiefe 2, 25 Related pro Artist) mit Album-Genre-Filter
- **Aktuell**: ~121K Songs. Genre-Backfill von Deezer Album API + MERT-Embedding-Extraction laufend
- **Legacy (inaktiv)**: FMA-large, MTG-Jamendo — Seeder-Scripts existieren noch in `scripts/`, werden nicht mehr verwendet

## Deployment
- Railway: Root Directory `/apps/api`, Config `/apps/api/railway.toml`, Healthcheck `/health` (30s timeout), Restart ON_FAILURE (max 3). CLI: `railway logs`, `railway variables`
- Vercel: Auto-deploy von `main`, `NEXT_PUBLIC_API_URL` zeigt auf Railway. Cron aktuell deaktiviert (CRON_SECRET Issue)
- Supabase: Migrations via MCP (`project_id: qpkemujemfnymtgmtkfg`) oder `supabase db push`
- Deploy-Status prüfen: `/deploy-check` (Config in `.claude/deploy.json`)

## Environment Variables (Backend)
- `DATABASE_URL` — Supabase PostgreSQL Connection String (required)
- `SUPABASE_URL` + `SUPABASE_ANON_KEY` — Supabase Client (required)
- `ACOUSTID_API_KEY` — Song-Identifikation via AcoustID (required)
- `CORS_ORIGINS` — Erlaubte Origins (Railway: `beattrack.app,www.beattrack.app,beattrack.vercel.app`)
- `SUPABASE_DB_URL` — Procrastinate-Connection (port 6543 Supavisor, optional fallback: DATABASE_URL)
- `SENTRY_DSN` — Error-Tracking (optional)

## Entwicklung
- `cd apps/api && uvicorn app.main:app --reload` — Backend lokal
- `cd apps/web && bun dev` — Frontend lokal
- Backend-Tests: `cd apps/api && pytest`
- Frontend-Tests: `cd apps/web && bun test` (Vitest, nicht Jest)

## Batch Scripts (langlebig)
- Scripts in `apps/api/scripts/` für DB-Operationen: `backfill_genre.py`, `extract_mert_batch.py`
- Ausführen: `.venv/bin/python scripts/xxx.py --apply` (Envvars SUPABASE_URL + SUPABASE_ANON_KEY nötig)
- Langlebige Jobs mit `nohup ... >> /tmp/xxx.log 2>&1 &` starten
- Haben Checkpoint/Resume-Support und Retry-Logic (3x mit Backoff, max 5 consecutive errors)
- MERT-Worker: `app/workers/mert.py` — direkt importieren, NICHT via `app/workers/__init__.py` (Procrastinate-Dep)

## Seeding & Maintenance Scripts
Alle in `apps/api/scripts/`, ausführen mit `.venv/bin/python`:
- **seed_deezer.py** — Deezer Electronic-Crawl + Essentia-Extraktion (`--crawl-only`, `--tracks-json`, `--resume`, `--workers`)
- **import_features.py** — JSONL → Supabase via REST RPC (braucht `--url` + `--key`, kein service_role_key nötig)
- **compute_stats.py** — Z-Score Stats berechnen + normalisieren (generiert SQL, `--format sql` für stdout)
- **cleanup_genres.py** — Songs nach Genre/Jahr filtern und löschen (`--execute`)
- **seed_fma.py** / **seed_jamendo.py** — Legacy-Seeder (nicht mehr aktiv)

## Similarity Engine
- **Tri-Signal Fusion**: MusiCNN 200d (HNSW-Index) + MERT 768d (re-ranking) + 44d handcrafted. Weights: 65/15/20 (with MERT) or 80/20 fallback
- **Pipeline**: HNSW → exclude → Late Fusion → Dedup → MMR → limit
- **MMR Diversity**: λ=0.7, re-ranks candidates to maximize inter-result embedding distance
- **Remix Dedup**: Strips (...), [...] and common suffixes to group versions, keeps best per base track
- **Genre-aware Fusion**: Feedback-learned per-genre weights (materialized view, 5min cache)
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
- **CORS www**: `CORS_ORIGINS` auf Railway muss BEIDE Varianten enthalten (`beattrack.app` + `www.beattrack.app`). Code auto-appended www wenn nur non-www gesetzt
- **pgvector HNSW + WHERE**: WHERE-Klauseln in der gleichen Query verhindern Index-Nutzung. Fix: Subquery-Pattern (innere Query = Index, äußere = Filter)
- **Vercel CRON_SECRET**: Darf kein Whitespace enthalten (inkl. trailing newline). Vercel validiert strikt seit 2026. `printf` statt `echo` beim Setzen
- **Deezer iframe Autoplay**: Browser blockiert cross-origin autoplay — User muss im Widget selbst auf Play klicken
- **Supabase Vektoren als Strings**: RPC/REST gibt `vector`-Spalten als JSON-String zurück (`"[0.1,...]"`) — `json.loads()` vor numpy nötig
- **RLS blockiert UPDATEs**: Anon-Key kann nur SELECT+INSERT. Für Updates SECURITY DEFINER RPCs nutzen
- **DB-Timeouts bei Batch-Jobs**: Supabase free-tier hat Statement-Timeout. Scripts brauchen Retry-Logic
- **MERT Batch-Inference**: Variable Audio-Längen verhindern echtes Batching — einzeln inferieren, I/O parallelisieren
- **workers/__init__.py**: Importiert Procrastinate global. Scripts die nur MERT brauchen: `importlib.util` direkt auf `mert.py`
- **Package Manager**: `uv pip install ... --python .venv/bin/python` (kein pip im venv)
- **Supabase MCP Project-ID**: MUSS `qpkemujemfnymtgmtkfg` sein. Bei "permission denied" → `list_projects` zum Verifizieren

## Security
- **Rate Limiting**: slowapi auf `/analyze` (10/min), `/identify/*` (20/min), `/feedback` (5/min geplant, aktuell 30/min)
- **HTTP Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options via `next.config.ts`
- **CORS**: Eingeschränkt auf GET/POST/OPTIONS, explizite Headers. `frame-src https://widget.deezer.com` in CSP
- **SSRF-Schutz**: YouTube URL-Validation via `urlparse` Host-Check (nicht Substring)
- **RLS**: Enabled auf allen Tabellen (anon=SELECT, service_role=ALL)

## SEO
- `sitemap.ts` + `robots.ts` im App-Root
- Open Graph + Twitter Cards in `layout.tsx` Metadata
- JSON-LD WebApplication Schema
- Canonical URL: `https://beattrack.app`

## Embedding-Space Analyse (Referenz)
- **MusiCNN**: Effective dim 11.3/200, 90% variance in 12 PCs. Cosine mean 0.59, std 0.24 (gut gespreizt)
- **MERT-v1-95M**: Effective dim 18.9/768, komplementär zu MusiCNN (Spearman ρ=0.035)
- **Genre Silhouette**: -0.13 (Genres nicht im Embedding separiert — codiert Klang, nicht Genre)

## Legal
- **Lizenz**: AGPLv3 (wegen Essentia-Abhängigkeit)
- **Seiten**: /impressum, /privacy, /nutzungsbedingungen
- **Domain**: beattrack.app (Vercel, SSL managed)
