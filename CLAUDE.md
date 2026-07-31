# Beattrack

Sonically similar song finder — findet Songs die ähnlich klingen.

## Stack
- **Frontend**: Next.js 15 + TypeScript + TailwindCSS v4 + framer-motion → Docker auf infra-01 (Hetzner)
- **Backend**: Python 3.12+ FastAPI + Essentia → Docker auf infra-01 (`apps/api/Dockerfile`, ROLE=api)
- **Worker**: Procrastinate-Worker als eigener Container (gleiches Image, ROLE=worker, cpus=1)
- **Database**: eigene PostgreSQL 17 + pgvector auf infra-01; Zugriff via PostgREST unter `https://beattrack.app/rest/v1`
- **Job Queue**: Procrastinate (Postgres-based, kein Redis); Job-Status in `analysis_jobs` (`app/services/jobs.py`)
- **Build-Tools**: Bun (Frontend), uv (Python/Backend)
- **Hosting-Details/Runbooks**: Repo `infra-migration` (docs/server.md, runbooks/)

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
- **Aktuell** (2026-07-31, gegen die Live-DB gezählt): **588.707 Songs**. Auto-Ingest und
  Neighbor-Expansion haben den Katalog vervielfacht, die Backfills sind nicht mitgewachsen:
  `learned_embedding` und `genre` 100 %, `mert_embedding` 314.101 (53 %),
  `handcrafted_norm` 121.773 (21 %). Folge: Für ~79 % der Songs fehlen die Radar-Features,
  Late Fusion fällt dort auf learned-only zurück
- **Legacy (inaktiv)**: FMA-large, MTG-Jamendo — Seeder-Scripts existieren noch in `scripts/`, werden nicht mehr verwendet

## Deployment (seit 2026-07-30: infra-01, Hetzner)
- Alles läuft als Docker-Container auf infra-01 (95.217.222.246, Helsinki), orchestriert über
  `/opt/stack/docker-compose.yml` (Quelle: `infra-migration/stack/docker-compose.yml`).
- Deploy: auf dem Server `cd /opt/apps/beattrack && git pull`, dann
  `cd /opt/stack && docker compose build beattrack-api beattrack-web beattrack-worker && docker compose up -d`.
- DNS/Registrar: beattrack.app liegt bei Vercel (nur noch Registrar+DNS, kein Hosting).
- DB-Migrations: direkt gegen die eigene Postgres (`docker exec postgres psql -U postgres -d beattrack`).
- Health-Cron: `/etc/cron.d/beattrack-health` auf infra-01. Uptime-Alarm: UptimeRobot (Konto Basti).
- Alt-Anbieter: Railway **gekündigt (2026-07-31)**, kein Fallback mehr. Vercel nur noch
  Registrar/DNS. Supabase wird von der Produktion nicht mehr angesprochen (`SUPABASE_URL`
  zeigt auf den eigenen PostgREST unter `https://beattrack.app`); das Projekt existiert noch.

## Environment Variables (Backend)
- `DATABASE_URL` — Postgres Connection String (required; auf infra-01: stack-db)
- `SUPABASE_URL` + `SUPABASE_ANON_KEY` — PostgREST-Endpunkt + anon-JWT (required)
- `SUPABASE_SERVICE_ROLE_KEY` — service-JWT; auf infra-01 Pflicht (anon hat keinen songs-Zugriff)
- `ROLE` — `api` (Default) oder `worker` (startet Procrastinate-Worker)
- `BEATTRACK_TEMP_DIR` — gemeinsames Upload-Volume von API+Worker (`/data/uploads`)
- `ACOUSTID_API_KEY` — Song-Identifikation via AcoustID (required)
- `CORS_ORIGINS` — Erlaubte Origins (auf infra-01 gesetzt auf `beattrack.app`; die www-Variante hängt der Code selbst an)
- `SUPABASE_DB_URL` — Procrastinate-Connection (port 6543 Supavisor, optional fallback: DATABASE_URL)
- `SENTRY_DSN` — Error-Tracking (optional)

## Entwicklung
- Setup: `bun install` (Root) und `cd apps/api && uv sync` (Python-venv ist nicht Teil des Workspace-Kopiervorgangs — nach frischem Checkout/Kopie neu anlegen)
- `cd apps/api && uvicorn app.main:app --reload` — Backend lokal
- `cd apps/web && bun dev` — Frontend lokal
- Backend-Tests: `cd apps/api && pytest`
- Frontend-Tests: `cd apps/web && bun run test` (Vitest, nicht Jest — siehe Gotchas: raw `bun test` funktioniert nicht)

## Batch Scripts (langlebig)
- Scripts in `apps/api/scripts/` für DB-Operationen: `backfill_genre.py`, `extract_mert_batch.py`
- Ausführen: `.venv/bin/python scripts/xxx.py --apply` (Envvars SUPABASE_URL + SUPABASE_ANON_KEY nötig — ACHTUNG: SUPABASE_ANON_KEY braucht den **service_role** Key als Wert, nicht den Anon Key, weil die Scripts via RPC schreiben)
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

## Datenbestände
- Die großen Datendateien wurden NICHT in diesen Workspace kopiert: `apps/api/scripts/deezer_features.jsonl` (719M), `deezer_tracks.json` (214M), `seed_features.jsonl` (129M), `jamendo_features.jsonl` (81M)
- Sie liegen weiterhin im Desktop-Original unter `/Users/ten.december/Desktop/projekte-codex/beattrack/apps/api/scripts/`
- Kleinere Checkpoints sind mitkopiert: `mert_*`, `seed_*`, `feed_checkpoint.json`, `deezer_tracks_v1.json`

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
- URL-Identify: YouTube oEmbed, SoundCloud oEmbed, Spotify oEmbed+OG-Scraping, Apple Music iTunes API, Deezer API (`/identify/deezer` — resolves share links via redirect)
- Commit-Messages auf Englisch, UI-Texte auf Deutsch

## CI/CD & Quality
- GitHub Actions: Lint + Type-Check + Build (Frontend), pytest + pip-audit (Backend)
- Pre-commit hook: `.husky/pre-commit` → `bun run lint` in apps/web
- Frontend-Lint läuft nur in CI (lokal broken wegen Bun-Workspace-Hoisting von @next/eslint-plugin-next)

## Gotchas
- **React 19 ESLint Rules**: `react-hooks/set-state-in-effect`, `refs`, `purity`, `immutability` — viel strikter als React 18. Patterns: `useSyncExternalStore` statt `useState(false)+useEffect(setTrue)`, Ref-Updates in `useEffect` statt Render, `useCallback` entfernen (Compiler macht das)
- **javascript: URLs**: React blockiert `href="javascript:..."` — Bookmarklets via `useRef` + `useEffect` setzen
- **`next lint` deprecated**: Next.js 15+ — ESLint CLI direkt verwenden
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
- **CORS www**: Beide Varianten müssen erlaubt sein. `CORS_ORIGINS=beattrack.app` genügt, der Code hängt `www.` selbst an — der Traefik-Router auf infra-01 akzeptiert ebenfalls beide Hosts
- **pgvector HNSW + WHERE**: WHERE-Klauseln in der gleichen Query verhindern Index-Nutzung. Fix: Subquery-Pattern (innere Query = Index, äußere = Filter)
- **Vercel CRON_SECRET**: Env-Var kann trailing Whitespace enthalten (inkl. Newline). Fix: `.trim()` auf beiden Seiten des Vergleichs in `apps/web/app/api/cron/route.ts` — bereits implementiert. Beim manuellen Setzen: `printf` statt `echo` verwenden
- **Deezer iframe Autoplay**: Browser blockiert cross-origin autoplay — User muss im Widget selbst auf Play klicken
- **Supabase Vektoren als Strings**: RPC/REST gibt `vector`-Spalten als JSON-String zurück (`"[0.1,...]"`) — `json.loads()` vor numpy nötig
- **RLS blockiert UPDATEs**: Anon-Key kann nur SELECT+INSERT. Für Updates SECURITY DEFINER RPCs nutzen
- **DB-Timeouts bei Batch-Jobs**: Supabase free-tier hat Statement-Timeout. Scripts brauchen Retry-Logic
- **MERT Batch-Inference**: Variable Audio-Längen verhindern echtes Batching — einzeln inferieren, I/O parallelisieren
- **workers/__init__.py**: Importiert Procrastinate global. Scripts die nur MERT brauchen: `importlib.util` direkt auf `mert.py`
- **Package Manager**: `uv pip install ... --python .venv/bin/python` (kein pip im venv)
- **Supabase MCP Project-ID**: MUSS `qpkemujemfnymtgmtkfg` sein. Bei "permission denied" → `list_projects` zum Verifizieren
- **`body > *` CSS-Regel**: `globals.css` hatte `body > * { position: relative }` — überschreibt `position: fixed` auf allen body-Kindern (MeshGradient, MouseGlow, Overlays). Geändert zu `body > main`. Neue fixed-Overlays im body müssen das berücksichtigen
- **Raw `bun test` vs. Vitest**: `bun test` nutzt Buns eigenen Test-Runner ohne Vitest/jsdom-Setup (`document is not defined`, `vi.mocked is not a function`). Immer `cd apps/web && bun run test` verwenden
- **npm audit PostCSS-Finding**: `npm audit --workspaces --omit=dev` meldet `node_modules/next/node_modules/postcss <8.5.10` — stable Next.js pinnt internes `postcss@8.4.31`. Kein Canary-Upgrade nur fürs Audit; abwarten bis stable Next.js `postcss >=8.5.10` mitbringt (Details in `KNOWN_ERRORS.md`)

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
- **Domain**: beattrack.app (Registrar/DNS bei Vercel, Hosting auf infra-01; Let's-Encrypt-Zertifikat via Traefik)
