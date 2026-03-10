# Beattrack - Sonically Similar Song Finder (v2.0)

## Context

Plattform-Radios (Spotify, YouTube, etc.) empfehlen Songs mit einem Mix aus kollaborativem Filtering und Audio-Features. Beattrack verfolgt einen **transparenten, Open-Source-Ansatz**: Audio-Features werden direkt analysiert und dem User erklärt — keine Black-Box, keine Engagement-Optimierung, kein Lock-in.

**Differenzierung**: Nicht "besser als Spotify", sondern **anders** — transparent, erklärbar, unabhängig. Der User sieht *warum* Songs ähnlich klingen (Feature-Radar-Chart mit 5 menschlichen Kategorien), nicht nur *dass* sie es tun.

**Constraints**: Keine Lizenzen, keine gekauften Songs/Daten, 100% legal, Open Source (AGPL-kompatibel), non-commercial.

---

## Architektur

```
User Input (File Upload / URL)
        │
        ▼
┌─────────────────────┐
│   Next.js Frontend   │  ← Waveform-Visualizer (Upload-Feedback)
│   (Vercel)           │  ← Drag & Drop Upload (direkt an Backend)
└────────┬────────────┘
         │ Direct Upload (kein BFF-Proxy für Files)
         ▼
┌─────────────────────┐
│  Python FastAPI      │  ← Essentia MusicExtractor + MusiCNN/EffNet (Subprocess)
│  (Railway Hobby)     │  ← AcoustID Song-Identifikation (Chromaprint serverseitig)
│                      │  ← Postgres Job-Queue (Procrastinate, concurrency=1)
│                      │  ← Rate-Limiting (slowapi) + Semaphore (concurrent uploads)
│                      │  ← Sentry Error Tracking
└────────┬────────────┘
         │ Vector Query
         ▼
┌─────────────────────┐
│  Supabase            │  ← pgvector Cosine Similarity (HNSW)
│  (Postgres + Storage)│  ← Dual Embeddings: Learned (200d) + Handcrafted (44d)
│                      │  ← Job-Queue (Procrastinate, via Supavisor port 6543)
└─────────────────────┘
```

### Zwei Input-Wege

1. **Datei-Upload**: User lädt MP3/WAV/FLAC hoch (max 50 MB) → Upload direkt an Python API → Postgres Job-Queue → Essentia extrahiert Features + Learned Embedding (in isoliertem Subprocess mit RAM-Cap) → pgvector Similarity Search → Ergebnis via SSE
2. **URL (YouTube/Spotify)**: Metadaten extrahieren → Song in DB suchen → wenn gefunden: Features aus DB nutzen → wenn nicht gefunden: User auffordern, Audio-Datei hochzuladen

**URL-Input lädt kein Audio herunter** — nur öffentliche Metadaten.

### Async-Analyse-Flow (kritisch)

Feature-Extraktion dauert **10-60 Sekunden**. Synchrone HTTP-Requests brechen bei Vercel (30s Timeout). Deshalb:

```
POST /analyze (File Upload)
  → MIME-Type-Validierung VOR Disk-Write (python-magic)
  → Validiert Audio mit ffprobe (Format, Integrität)
  → Speichert Datei temporär
  → Erstellt Job in Postgres Queue (Procrastinate)
  → Returns: { job_id: "abc-123", status: "queued" }

GET /analyze/{job_id}/stream  (SSE)
  → Server-Sent Events: { status: "queued" | "processing" | "completed" | "failed", progress?: 0.0-1.0 }
  → Bei "completed": enthält Result-Daten inline

GET /analyze/{job_id}/results  (Fallback)
  → Returns: { song: {...}, similar: [...] }  (wenn completed)
```

Frontend verbindet sich per SSE auf `/stream`. Kein Polling nötig — Server pushed Updates.

**Fallback**: Wenn SSE-Connection abbricht, pollt Frontend `/results` mit exponential Backoff.

### Load Control (NEU — kritisch für Stabilität)

```python
# === Concurrent Upload Limiter ===
UPLOAD_SEMAPHORE = asyncio.Semaphore(3)       # Max 3 gleichzeitige Uploads
SSE_LIMITER = asyncio.Semaphore(50)           # Max 50 offene SSE-Connections

@app.post("/analyze")
async def analyze_audio(file: UploadFile):
    if UPLOAD_SEMAPHORE._value == 0:
        raise HTTPException(503, "Server at capacity. Retry shortly.")
    async with UPLOAD_SEMAPHORE:
        # MIME-Check → ffprobe → enqueue
        ...

# === Procrastinate Worker ===
app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(
        host="db.PROJECT.supabase.co",
        port=6543,                        # Supavisor Transaction Mode
        kwargs={"prepare_threshold": None},
        open_kwargs={"max_size": 5},      # Pool auf 5 Connections begrenzt
    ),
    worker_defaults={
        "concurrency": 1,                 # NUR 1 Analyse gleichzeitig
        "listen_notify": False,           # Spart 1 Connection, Fallback auf Polling
        "shutdown_graceful_timeout": 300.0,
    }
)

# === Subprocess RAM-Cap ===
import resource

def limit_memory(max_bytes: int = 2 * 1024**3):  # 2 GB
    resource.setrlimit(resource.RLIMIT_AS, (max_bytes, resource.RLIM_INFINITY))

subprocess.run(
    ["python", "-m", "app.workers.extract", audio_path],
    preexec_fn=lambda: limit_memory(2 * 1024**3),
    timeout=180
)
```

**Connection-Budget (Supabase Free Tier: 60 direct, 200 via Supavisor)**:

| Consumer | Connections |
|---|---|
| FastAPI asyncpg Pool | 5 |
| Procrastinate Worker Pool | 3 |
| Supabase interne Services | ~15 |
| Safety Margin | 5 |
| **Total** | **~28** (von 200 Supavisor) |

---

## Dual-Embedding-Strategie (NEU — Kernänderung v2.0)

### Problem mit reinen Handcrafted Features (v1.0)

44-dim MFCCs + Chroma + Spectral sind **~40% schlechter** als Learned Embeddings für Musik-Empfehlungen (RecSys 2024, "Comparative Analysis of Pretrained Audio Representations in Music Recommender Systems"):

| Ansatz | HitRate@50 |
|---|---|
| Raw MFCCs (104-dim) | 0.231 |
| MusiCNN Embeddings | **0.385** |
| MERT Embeddings | 0.360 |

MFCCs erfassen nur Timbre — Produktionsstil, Gesangsstil, Stimmung werden nicht erkannt.

### Lösung: Learned Embeddings + Handcrafted Features

**Primär: MusiCNN oder EffNet-Discogs** (via `essentia-tensorflow`):

| Modell | Dim | Size | CPU-Inference | Lizenz | Stärke |
|---|---|---|---|---|---|
| **MusiCNN** | 200 | 18 MB | ~2-4s/Song | AGPL | Bestes Recommendation-Modell im 2024-Benchmark |
| **EffNet-Discogs (artist)** | 1280 | 18 MB | ~3-6s/Song | AGPL | Trainiert auf stilistische Ähnlichkeit (same-artist clustering) |
| MAEST | 768+ | ~90 MB | ~5-10s/Song | AGPL | Bestes Downstream-Modell laut Essentia-Docs |

**Empfehlung Phase 0**: MusiCNN (200-dim) als Default testen. Wenn Budget erlaubt: EffNet-Discogs `discogs_artist_embeddings` (1280-dim) — explizit für "more like this" trainiert.

**Sekundär: 44-dim Handcrafted Features** (wie in v1.0) als:
- **Hard Filters**: BPM-Range, Key-Matching
- **Erklärbare Achsen** im Feature-Radar-Chart
- **Fallback** bei Model-Loading-Fehler

### Late Fusion Similarity

```python
similarity = (
    0.80 * cosine(learned_emb_a, learned_emb_b) +    # MusiCNN/EffNet
    0.20 * weighted_handcrafted(feat_a, feat_b)        # BPM, Key, Spektral
)

def weighted_handcrafted(a, b):
    return (
        0.30 * cosine(mfcc_mean_a, mfcc_mean_b) +
        0.10 * cosine(mfcc_std_a, mfcc_std_b) +
        0.25 * cosine(hpcp_a, hpcp_b) +
        0.20 * cosine(spectral_a, spectral_b) +
        0.15 * rhythm_similarity(bpm_a, dance_a, bpm_b, dance_b)
    )
```

### pgvector Schema (aktualisiert)

```sql
CREATE TABLE songs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    musicbrainz_id TEXT UNIQUE,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT,
    duration_sec FLOAT,
    bpm FLOAT,
    musical_key TEXT,
    -- Dual Embeddings
    learned_embedding VECTOR(200) NOT NULL,   -- MusiCNN (oder 1280 für EffNet)
    handcrafted_raw VECTOR(44) NOT NULL,      -- Roh-Vektor (für Re-Normalisierung)
    handcrafted_norm VECTOR(44) NOT NULL,     -- Normalisierter Vektor
    -- Metadata
    source TEXT DEFAULT 'acousticbrainz',
    metadata_status TEXT DEFAULT 'complete',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW Index auf Learned Embedding (primäre Suche)
CREATE INDEX ON songs USING hnsw (learned_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Optional: Index auf Handcrafted für Filter-Queries
CREATE INDEX ON songs USING hnsw (handcrafted_norm vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**Speicher-Budget (300K Songs)**:

| Komponente | Größe |
|---|---|
| Learned Embedding (200-dim × 4 bytes × 300K) | ~24 MB |
| Handcrafted Raw (44-dim × 4 bytes × 300K) | ~5 MB |
| Handcrafted Norm (44-dim × 4 bytes × 300K) | ~5 MB |
| Metadata (Titel, Artist, Album, MBID) × 300K | ~90 MB |
| HNSW Index (learned, 200-dim) | ~80-120 MB |
| HNSW Index (handcrafted, 44-dim) | ~40-60 MB |
| Procrastinate Job-Tabellen | ~10 MB |
| **Total** | **~260-320 MB** (passt in Free Tier 500 MB) |

Falls EffNet-Discogs (1280-dim): Learned Embedding = ~154 MB, HNSW Index = ~200-300 MB → **~500-550 MB** — knapp über Free Tier, Micro ($25/mo) nötig. Deshalb MusiCNN (200-dim) als Default.

---

## Feature-Space-Kompatibilität (NEU — kritisches Problem gelöst)

### Das Problem

AcousticBrainz-Features wurden mit **Essentia v2.1_beta2** berechnet. `pip install essentia` liefert **v2.1b6.dev1389**. Confirmed Breaking Changes:

| Feature | Änderung | Impact |
|---|---|---|
| MFCC | `logType` Default: `dbpow` → `dbamp` (Faktor-2-Differenz in Log-Skala) | **HOCH** |
| MelBands | `warpingFormula` + `normalize` Parameter hinzugefügt | MITTEL |
| HPCP | `size` Default-Inkonsistenzen (32 vs 36 Bins je nach Extractor) | MITTEL |
| BPM | `BeatTrackerDegara` jetzt deterministisch (war randomisiert in beta2) | NIEDRIG |
| MusicExtractor Keys | Renames: `end_time` → `length`, neue Outputs hinzugefügt | NIEDRIG |

**Es gibt keinen `--legacy-mode` Flag** und **keine pip-installierbare beta2-Version**.

### Lösung: Drei-Schichten-Strategie

**Schicht 1 — Learned Embeddings umgehen das Problem komplett**:
MusiCNN/EffNet-Discogs-Modelle produzieren Embeddings im **selben Raum** unabhängig von der Essentia-Version, da das Modell-Gewicht fixiert ist. Die Input-Pipeline (Resampling, Framing) ist stabil. **Das ist der Hauptgrund für den Wechsel zu Learned Embeddings.**

Für die AcousticBrainz-Seed-Daten: Learned Embeddings müssen **neu berechnet werden** (AcousticBrainz hat keine MusiCNN-Embeddings). Das bedeutet: Audio-Files sind nötig. **Alternative**: Nur die Handcrafted Features aus AcousticBrainz für den Feature-Radar-Chart nutzen, aber die Similarity Search ausschließlich auf Learned Embeddings basieren.

**Schicht 2 — Handcrafted Features mit YAML-Profil alignen** (für Radar-Chart):

```yaml
# essentia_profile_beta2_compat.yaml
lowlevelFrameSize: 2048
lowlevelHopSize: 1024
lowlevelWindowType: blackmanharris62
lowlevelSilentFrames: noise
tonalFrameSize: 4096
tonalHopSize: 2048
rhythmMethod: degara
rhythmMinTempo: 40
rhythmMaxTempo: 208
analysisSampleRate: 44100
```

Plus explizite MFCC-Parameter um `logType=dbpow` zu erzwingen (sofern MusicExtractor das unterstützt — in Phase 0 verifizieren).

**Schicht 3 — Empirische Validierung in Phase 0** (Pflicht):
1. 50 Tracks auswählen, die in AcousticBrainz vorhanden sind
2. Deren AcousticBrainz-JSON herunterladen (API noch live)
3. Dieselben Audio-Files durch aktuelle Essentia mit YAML-Profil laufen lassen
4. MFCC-Koeffizienten, HPCP, BPM paarweise vergleichen
5. Wenn systematischer Offset: Korrekturfaktor berechnen (linear regression auf MFCCs)
6. **Go/No-Go**: Wenn Korrelation < 0.95 und kein Korrekturfaktor möglich → Handcrafted Features NUR aus eigener Essentia-Runtime nutzen, AcousticBrainz-Features verwerfen

### Konsequenz für Daten-Strategie

Die Seed-Datenbank kann **nicht mehr blind auf vorberechneten AcousticBrainz-Features basieren**. Stattdessen:

- **AcousticBrainz Feature CSVs** (3 GB): Für Metadata + grobe Filter (BPM, Key, Loudness) — diese Einzelwerte sind versionsstabil
- **Learned Embeddings**: Müssen für jeden Song separat berechnet werden — entweder via Audio-Analyse oder via ein Proxy-Modell das auf AcousticBrainz-Features trainiert wurde
- **Handcrafted 44-dim Vektoren**: Nur für Songs aus User-Uploads berechnen (eigene Essentia-Version, konsistent)

Siehe "Daten-Strategie" unten für die aktualisierte Pipeline.

---

## Tech Stack

### Frontend
- **Next.js 15** (App Router) — deployed auf Vercel
- **TailwindCSS v4** — Styling
- **Framer Motion** — staggered Reveal der Results, Progress-Animation während Analyse
- **Font**: Space Grotesk (geometric, modern, music-passend)

### Backend
- **Python 3.12 + FastAPI 0.135.0+** — API Server mit nativem SSE Support
- **Essentia** (AGPL v3) — Audio Feature-Extraktion via `MusicExtractor`
- **essentia-tensorflow** (AGPL v3) — MusiCNN / EffNet-Discogs Inference (18 MB Modell, CPU-only)
- **Procrastinate** (MIT, v3.7.2) — Postgres-basierte Job-Queue
  - `concurrency=1` (max 1 paralleler Analyse-Job)
  - `listen_notify=False` (spart 1 DB-Connection, Fallback auf Polling)
  - Pool via Supavisor Port 6543, `max_size=5`
- **python-magic** — MIME-Type-Validierung vor Disk-Write
- **uv** — Python Package Manager
- **Pydantic v2** — Request/Response Validation
- **slowapi** — IP-basiertes Rate-Limiting (5 req/min auf `/analyze`)
- **Sentry** (Free Tier) + **UptimeRobot** (Free, 5-Min-Ping) — Error Tracking + Uptime
- **Chromaprint** (`pyacoustid` + `fpcalc` im Docker-Image) — AcoustID Fingerprinting

### Audio-Validierung (Reihenfolge!)
1. **python-magic**: MIME-Type prüfen BEVOR Datei auf Disk geschrieben wird
2. **File-Size**: Max 50 MB Check auf Content-Length Header
3. **ffprobe**: Format-Integrität, Codec-Check nach Disk-Write
4. **Essentia in Subprocess**: `preexec_fn=limit_memory(2GB)`, `timeout=180`

### Datenbank
- **Supabase** (Free Tier: 500 MB DB, 200 Supavisor Connections)
- **pgvector** Extension — HNSW Index für Cosine Similarity
- **pg_trgm** — Fuzzy-Text-Suche für URL-Input
- Verbindung **ausschließlich über Supavisor** (Port 6543, Transaction Mode)
- `prepare_threshold=None` (Supavisor-kompatibel)

### Song-Identifikation
- **AcoustID** (free, non-commercial, 3 req/s) — Fingerprint → MusicBrainz Recording ID
- **MusicBrainz API** (free, 1 req/s) — Metadata
  - User-Agent Pflicht: `Beattrack/1.0 (https://github.com/user/beattrack)`

### Streaming-Links
- **Search-Links** statt direkter URLs: `https://open.spotify.com/search/{title} {artist}`
- Kein API-Key nötig, keine ToS-Verletzung

### Testing
- **Vitest** — Frontend Unit Tests
- **pytest** — Backend Unit/Integration Tests
- **Playwright** — E2E Tests
- **FMA-small Dataset** (8K Tracks, Genre-Labels) — Embedding-Qualitäts-Evaluation

### Deployment
- **Vercel** — Frontend (free)
- **Railway Hobby Plan** — Python Backend
  - Docker-Image ~1.8 GB (Essentia + essentia-tensorflow + MusiCNN-Modell)
  - Multi-stage Dockerfile → Ziel <1 GB
  - Service Memory Limit: 3 GB (Railway Setting)
  - Restart Policy: "On Failure" (nicht "Always" — verhindert OOM-Loops)
  - `/health` Endpoint
- **Supabase** — Datenbank + Job-Queue (free)
- **UptimeRobot** — Uptime-Monitoring + Warm-Ping alle 5 Min (free, zuverlässiger als GitHub Actions Cron)
- **GitHub Actions** — CI/CD (NICHT für Keepalive — GitHub deaktiviert Scheduled Workflows bei inaktiven Repos)

### Kosten-Realität (korrigiert)

Railway rechnet CPU + RAM ab dem Moment wo der Container läuft:

| Ressource | Rate |
|---|---|
| RAM | $10.00 / GB / Monat |
| CPU | $20.00 / vCPU / Monat |
| Inkludiert | $5 Usage Credit |

**Realistische Kalkulation (1 GB RAM, 0.25 vCPU, 24/7)**:

| Posten | Kosten/Monat |
|---|---|
| RAM: 1 GB × 730h | ~$10 |
| CPU: 0.25 vCPU × 730h | ~$5 |
| Abzgl. Usage Credit | -$5 |
| Railway Plan-Basis | $5 |
| **Railway Total** | **~$15/Monat** |

| Service | Plan | Kosten/Monat |
|---|---|---|
| Vercel | Free | $0 |
| Railway | Hobby | **~$15** |
| Supabase | Free | $0 |
| Sentry | Free | $0 |
| UptimeRobot | Free | $0 |
| **Total** | | **~$15/Monat** |

**Kosten-Optimierung**: Railway "Sleep on Inactivity" aktivieren statt 24/7 Warm-Halten. Cold Start ~15-30s ist akzeptabel mit "Wir wachen auf..."-UX. Reduziert auf **~$5-8/Monat** bei sporadischer Nutzung.

---

## Daten-Strategie (komplett überarbeitet)

### Das Feature-Space-Problem ändert alles

AcousticBrainz-Features (Essentia v2.1_beta2) sind **nicht direkt kompatibel** mit Runtime-Features (Essentia v2.1b6.dev). Das bedeutet:

1. Vorberechnete 44-dim Vektoren aus AcousticBrainz können NICHT direkt mit Runtime-Vektoren verglichen werden
2. Learned Embeddings (MusiCNN/EffNet) existieren NICHT im AcousticBrainz-Dump
3. Die Seed-Strategie muss grundlegend anders sein

### Neuer Ansatz: Feature CSVs + API + Eigene Embedding-Berechnung

#### Verfügbare AcousticBrainz-Ressourcen

| Ressource | Größe | Inhalt | Nutzen |
|---|---|---|---|
| **Feature CSVs** | 3 GB (3 Dateien) | 10 Features für alle 29.46M Submissions | BPM, Loudness, Key, Danceability — für Filter/Metadata |
| **Highlevel-Dump** | 39 GB | Genre-Classifier-Daten (9 Genres) | Stratified Sampling |
| **API** (noch live) | — | Voller JSON pro MBID, Batch bis 25 MBIDs | Vollständige Lowlevel-Features on demand |
| **Sample-Dump** | 2 GB | ~80K unique MBIDs | Pipeline-Testing |
| **Lowlevel-Dump** | 589 GB | Alles | NICHT nötig — API ist effizienter für 300K |
| **Genre Dataset** (Zenodo) | ~83 GB unkomprimiert | 1.35M Recordings mit Features | Alternative Datenquelle |

**Kritisch**: Die AcousticBrainz-API ist noch live (`https://acousticbrainz.org/api/v1/<mbid>/low-level`), unterstützt Batch-Requests (25 MBIDs/Call), aber ohne SLA. **Jetzt archivieren**.

#### Warum NICHT den 589 GB Dump

- Tar + Zstd erlaubt kein Seeking — voller sequentieller Scan nötig für stratified Sampling
- MBIDs sind NICHT sortiert innerhalb der 30 Archive
- 589 GB Download + ~2 TB unkomprimiert = signifikante Cloud-Kosten
- Für 300K Songs ist die **API 10x effizienter**: 300K / 25 MBIDs pro Batch = 12.000 API-Calls ≈ 20-40 Minuten

### Seed-Pipeline (neu)

#### Schritt 1: MBID-Auswahl via Feature CSVs + Highlevel

1. Feature CSVs downloaden (3 GB) → BPM, Loudness, Key für alle 29.46M
2. Highlevel-Dump downloaden (39 GB) → Genre-Tags (`genre_dortmund`, ~60% Accuracy)
3. Stratified Sampling: ~11% pro Genre (9 Genres), gleichverteilt
4. **Qualitätsfilter**:
   - Nur Tracks mit valider Metadata (`title` und `artist` nicht leer)
   - BPM im Bereich 40-250 (Ausreißer raus)
   - Keine MBID-Duplikate
5. **Output**: 300K MBID-Liste mit Genre-Label + Basic Metadata

#### Schritt 2: Lowlevel-Features via API

1. 300K MBIDs in Batches à 25 an AcousticBrainz API
2. ~12.000 API-Calls à ~5-10 req/s = **20-40 Minuten**
3. Retry-Logic + Resume-Fähigkeit (Checkpoint pro 1.000er-Batch)
4. Extrahierte Features pro Track:
   - `lowlevel.mfcc.mean` (13 dims) + `lowlevel.mfcc.stdev` (13 dims)
   - `tonal.hpcp.mean` (→ auf 12 reduziert)
   - `lowlevel.spectral_centroid.mean`, `spectral_rolloff.mean`
   - `rhythm.bpm`, `lowlevel.zerocrossingrate.mean`
   - `lowlevel.average_loudness`, `rhythm.danceability`
   - **Total: 44 Dimensionen** (für Radar-Chart und Filter)
5. Metadata aus `metadata.tags` extrahieren
6. **Alle JSON-Responses lokal archivieren** (für spätere Re-Extraktion)

#### Schritt 3: Learned Embeddings (das eigentliche Problem)

MusiCNN/EffNet-Embeddings brauchen **Audio-Input** — AcousticBrainz hat kein Audio. Drei Optionen:

**Option A — Proxy-Modell (empfohlen für MVP)**:
- Kleines NN trainieren das AcousticBrainz-Features (44-dim) auf MusiCNN-Embeddings (200-dim) mappt
- Trainingsdata: ~5.000 Songs mit Audio beschaffen (z.B. FMA-small, 8K CC-lizenzierte Tracks)
- Für diese 5.000: sowohl AcousticBrainz-Features als auch MusiCNN-Embeddings berechnen
- Linear Regression oder MLP (44 → 200) trainieren
- Auf restliche 295K AcousticBrainz-Tracks anwenden
- **Vorteil**: Kein Audio für 300K Songs nötig
- **Nachteil**: Approximation — Qualität hängt vom Proxy-Modell ab
- **Risiko**: Wenn Korrelation AcousticBrainz→MusiCNN < 0.7, ist der Proxy unbrauchbar

**Option B — FMA Dataset als Seed (einfacher, kleiner)**:
- FMA-large: 106K Tracks mit Audio (CC-lizenziert), ~100 GB Download
- FMA-medium: 25K Tracks, ~22 GB
- Direkt MusiCNN + Handcrafted Features berechnen — kein Kompatibilitätsproblem
- **Vorteil**: Kein Feature-Space-Problem, Audio verfügbar, Genre-Labels vorhanden
- **Nachteil**: Nur 25K-106K Songs statt 300K, weniger Mainstream-Katalog
- **MusicBrainz-Integration**: FMA hat keine MBIDs — Artist/Title-Matching nötig

**Option C — Hybrid (empfohlen langfristig)**:
- Phase 1: FMA-medium (25K) als initiale Seed → volle Embedding-Qualität, sofort nutzbar
- Phase 2: AcousticBrainz 300K via Proxy-Modell hinzufügen (nur Handcrafted + approx. Learned)
- Phase 3: User-Uploads erweitern DB mit echten Learned Embeddings
- Songs mit echten Embeddings werden bei Similarity bevorzugt

**Empfehlung**: **Option C** — FMA-medium als Start, AcousticBrainz als Erweiterung.

#### Schritt 4: Normalisierung + DB-Load

1. Globale Z-Score-Normalisierung der Handcrafted Features (Mean + Std über gesamten Corpus)
2. Learned Embeddings werden NICHT z-score-normalisiert (bereits im Modell-Space normiert)
3. Beide Vektoren + Metadata in Supabase laden
4. Normalisierungs-Stats in `config`-Tabelle speichern

#### Schritt 5: MusicBrainz Metadata-Enrichment

- Nur für Tracks mit `metadata_status: 'pending'` (~20-30%)
- 1 req/s Rate-Limit → ~17-25 Stunden (Cloud-Instanz, nicht lokal)
- **Realistische Erwartung**: 2-4 Tage mit MusicBrainz-503-Phasen und Retries
- Tracks die nach Enrichment immer noch `title: null` haben: **aus Suchergebnissen ausblenden** (nicht löschen, aber `metadata_status: 'failed'`)

### ETL-Kosten (Einmalig)

| Posten | Kosten |
|---|---|
| Cloud-Instanz (EC2 spot, 4h) | ~$0.30 |
| EBS Storage (100 GB, 1 Tag) | ~$0.30 |
| FMA Download (22 GB, Ingress free) | $0 |
| AcousticBrainz API (12K Calls) | $0 |
| **Total** | **~$1** |

Massiv günstiger als der 589 GB Dump-Ansatz aus v1.0.

### Normalisierung

Z-Score Normalisierung der Handcrafted Features muss **global** sein:

```python
global_mean = np.mean(all_vectors, axis=0)  # shape: (44,)
global_std = np.std(all_vectors, axis=0)    # shape: (44,)
# In config-Tabelle speichern
# Bei Runtime: normalized = (raw_vector - global_mean) / global_std
```

**Re-Normalisierung**: Raw-Vektoren werden immer mitgespeichert. Bei >50K User-Uploads: neue Stats berechnen (Batch-Job).

### Normalisierungs-Drift

- Seed-Stats sind Baseline, werden **nicht** automatisch angepasst
- `normalization_stats` in DB-Tabelle `config` (nicht im Repo committed)
- **Startup-Validierung**: API prüft beim Start ob Stats vorhanden, sonst Fehler

---

## Feature-Extraktion Pipeline (Essentia + MusiCNN)

```python
import subprocess, json, resource
import numpy as np

# === RAM-Cap für Subprocesses ===
def limit_memory(max_bytes: int = 2 * 1024**3):
    resource.setrlimit(resource.RLIMIT_AS, (max_bytes, resource.RLIM_INFINITY))

def extract_features_safe(audio_path: str, timeout: int = 180) -> dict:
    """Essentia + MusiCNN in isoliertem Subprocess mit RAM-Cap."""
    result = subprocess.run(
        ["python", "-m", "app.workers.extract", audio_path],
        capture_output=True, timeout=timeout, text=True,
        preexec_fn=lambda: limit_memory(2 * 1024**3),
    )
    if result.returncode != 0:
        # NICHT stderr an Client durchleiten — generischer Fehler
        logger.error(f"Essentia failed for {audio_path}: {result.stderr[:500]}")
        raise FeatureExtractionError("Audio analysis failed. Please try a different file.")
    return json.loads(result.stdout)


# === Worker-Subprocess (app/workers/extract.py) ===
import essentia.standard as es
from essentia.standard import TensorflowPredictMusiCNN
import numpy as np
import sys, json

def extract_all(audio_path: str) -> dict:
    """Extrahiert Learned Embedding + Handcrafted Features."""

    # 1. MusiCNN Learned Embedding (200-dim)
    audio = es.MonoLoader(filename=audio_path, sampleRate=16000)()
    model = TensorflowPredictMusiCNN(
        graphFilename="models/msd-musicnn-1.pb",
        output="model/dense/BiasAdd"  # Penultimate layer = 200-dim
    )
    embeddings = model(audio)  # Shape: (n_frames, 200)
    learned_embedding = np.mean(embeddings, axis=0)  # Mean-Pool über Frames

    # 2. Handcrafted Features (44-dim)
    features, _ = es.MusicExtractor(
        lowlevelStats=['mean', 'stdev'],
        rhythmStats=['mean', 'stdev'],
        tonalStats=['mean', 'stdev'],
        # YAML-Profil für beta2-Kompatibilität:
        # profile="essentia_profile_beta2_compat.yaml"
    )(audio_path)

    handcrafted = np.concatenate([
        features['lowlevel.mfcc.mean'],                # 13
        features['lowlevel.mfcc.stdev'],               # 13
        reduce_hpcp(features['tonal.hpcp.mean']),      # 12 (36 → 12)
        [features['lowlevel.spectral_centroid.mean']], # 1
        [features['lowlevel.spectral_rolloff.mean']],  # 1
        [features['rhythm.bpm']],                      # 1
        [features['lowlevel.zerocrossingrate.mean']],  # 1
        [features['lowlevel.average_loudness']],       # 1
        [features['rhythm.danceability']],             # 1
    ])  # Total: 44 dims

    return {
        "learned": learned_embedding.tolist(),
        "handcrafted": handcrafted.tolist(),
        "bpm": float(features['rhythm.bpm']),
        "key": str(features.get('tonal.key_edma.key', 'Unknown')),
    }


def reduce_hpcp(hpcp_36: np.ndarray) -> np.ndarray:
    """36-bin HPCP → 12-bin Chroma (3 Sub-Bins pro Halbton summieren)."""
    return hpcp_36.reshape(12, 3).sum(axis=1)


if __name__ == "__main__":
    result = extract_all(sys.argv[1])
    print(json.dumps(result))
```

### Temporäre Dateien + Cleanup

```python
import tempfile, os, atexit

TEMP_DIR = tempfile.mkdtemp(prefix="beattrack_")
atexit.register(lambda: shutil.rmtree(TEMP_DIR, ignore_errors=True))

# Zusätzlich: Cleanup-Job alle 30 Min für verwaiste Temp-Files
@app.on_event("startup")
async def schedule_cleanup():
    asyncio.create_task(periodic_cleanup(TEMP_DIR, max_age_minutes=30))
```

---

## Similarity Search

```sql
CREATE EXTENSION vector;
CREATE EXTENSION pg_trgm;

-- Haupttabelle (siehe oben für vollständiges Schema)

-- Normalisierungs-Config
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User-Feedback
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_song_id UUID REFERENCES songs(id),
    result_song_id UUID REFERENCES songs(id),
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Similarity-Funktion (primär auf Learned Embedding)
CREATE OR REPLACE FUNCTION find_similar_songs(
    query_embedding VECTOR(200),
    match_count INT DEFAULT 20,
    exclude_id UUID DEFAULT NULL,
    min_bpm FLOAT DEFAULT 0,
    max_bpm FLOAT DEFAULT 999
) RETURNS TABLE (id UUID, title TEXT, artist TEXT, album TEXT, bpm FLOAT, similarity FLOAT)
LANGUAGE sql AS $$
    SELECT id, title, artist, album, bpm,
           1 - (learned_embedding <=> query_embedding) AS similarity
    FROM songs
    WHERE id IS DISTINCT FROM exclude_id
      AND bpm BETWEEN min_bpm AND max_bpm
      AND metadata_status != 'failed'  -- Songs ohne Metadata ausblenden
    ORDER BY learned_embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Fuzzy-Text-Indexe für URL-Suche
CREATE INDEX ON songs USING gin (title gin_trgm_ops);
CREATE INDEX ON songs USING gin (artist gin_trgm_ops);
```

---

## URL-Input: Metadata-Extraktion

### YouTube
- **oEmbed API** → `title` + `author_name`
- Titel-Heuristik: `"Artist - Song Title"` parsen, `author_name` als Fallback
- DB-Suche: Fuzzy-Match (pg_trgm)

### Spotify
- URL parsen → Track-Name aus URL-Slug
- DB-Suche: Fuzzy-Match
- Kein API-Call nötig

### Fallback
- "Dieser Song ist noch nicht in unserer Datenbank — lade die Audio-Datei hoch und wir finden trotzdem ähnlich klingende Songs!"
- Upload-CTA prominent anzeigen

**Hinweis**: SoundCloud aus v1.0 entfernt — keine zugängliche Metadata-API ohne OAuth.

---

## Projekt-Struktur

```
beattrack/
├── apps/
│   ├── web/                      # Next.js Frontend
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx          # Landing + Upload
│   │   │   ├── results/
│   │   │   │   └── [jobId]/
│   │   │   │       └── page.tsx  # Similar Songs Results (SSE-basiert)
│   │   │   ├── privacy/
│   │   │   │   └── page.tsx      # Privacy Policy
│   │   │   └── api/              # BFF Routes (Metadata-Proxy, KEIN File-Upload-Proxy)
│   │   ├── components/
│   │   │   ├── upload-zone.tsx   # Drag & Drop, max 50MB, Format-Validierung
│   │   │   ├── analysis-progress.tsx  # SSE + Progress + "Wir wachen auf..."
│   │   │   ├── song-card.tsx     # Title, Artist, Similarity, Search-Links, Feedback
│   │   │   ├── feature-radar.tsx # Radar-Chart: 5 menschliche Kategorien
│   │   │   ├── url-input.tsx
│   │   │   └── opt-in-dialog.tsx # DSGVO: "Features in DB speichern?" (NEU)
│   │   ├── lib/
│   │   │   ├── api.ts            # Backend API client
│   │   │   └── sse.ts            # SSE-Client mit Reconnect-Logic
│   │   ├── __tests__/
│   │   ├── vitest.config.ts
│   │   └── package.json
│   │
│   └── api/                      # Python FastAPI Backend
│       ├── app/
│       │   ├── main.py           # FastAPI + /health + Startup-Validierung + Sentry
│       │   ├── middleware/
│       │   │   ├── rate_limit.py # slowapi + Semaphore
│       │   │   └── mime_check.py # MIME-Validierung vor Disk-Write (NEU)
│       │   ├── routes/
│       │   │   ├── analyze.py    # POST /analyze → Job, GET /analyze/{id}/stream (SSE)
│       │   │   ├── search.py     # POST /search (URL → metadata lookup)
│       │   │   └── identify.py   # POST /identify (AcoustID lookup)
│       │   ├── services/
│       │   │   ├── features.py   # Subprocess-Wrapper + RAM-Cap + Normalization
│       │   │   ├── similarity.py # pgvector query + Late Fusion
│       │   │   ├── acoustid.py   # AcoustID + Chromaprint client
│       │   │   ├── metadata.py   # YouTube oEmbed, Spotify URL parser
│       │   │   └── validation.py # MIME + ffprobe Validierung
│       │   ├── workers/
│       │   │   ├── analyze.py    # Procrastinate Worker (concurrency=1)
│       │   │   └── extract.py    # Essentia + MusiCNN Subprocess (isoliert)
│       │   ├── models/
│       │   │   └── schemas.py    # Pydantic models
│       │   └── db/
│       │       └── supabase.py   # Supavisor port 6543, pool max_size=5
│       ├── models/
│       │   └── msd-musicnn-1.pb  # MusiCNN Modell (18 MB)
│       ├── tests/
│       │   ├── fixtures/         # Test audio files (sine waves + corrupt + FMA samples)
│       │   ├── test_features.py
│       │   ├── test_similarity.py
│       │   ├── test_metadata.py
│       │   ├── test_validation.py
│       │   ├── test_load_control.py  # Semaphore, Concurrency, RAM-Cap (NEU)
│       │   └── test_api.py
│       ├── pyproject.toml
│       └── Dockerfile            # Multi-stage: Python 3.12 + Essentia + TF + MusiCNN
│
├── scripts/
│   ├── seed_fma.py               # FMA-medium Seed (25K Tracks, eigene Embeddings)
│   ├── seed_acousticbrainz.py    # AcousticBrainz API-basiertes Seeding (300K)
│   ├── train_proxy_model.py      # AcousticBrainz→MusiCNN Proxy (Option A)
│   ├── extract_genre_mbids.py    # Highlevel CSV → Genre-stratified MBID-Liste
│   ├── enrich_metadata.py        # MusicBrainz Metadata für Lücken
│   ├── validate_features.py      # Phase-0: Embedding-Qualität + Feature-Alignment
│   ├── evaluate_similarity.py    # FMA Genre-Precision Benchmark (NEU)
│   └── generate_test_audio.py    # Sine wave test fixtures
│
├── supabase/
│   └── migrations/
│       ├── 001_init.sql          # Schema + pgvector + pg_trgm
│       ├── 002_config.sql        # Config-Tabelle
│       ├── 003_feedback.sql      # Feedback-Tabelle
│       └── 004_procrastinate.sql # Job-Queue Schema
│
├── .github/
│   └── workflows/
│       ├── ci.yml                # Tests + Lint
│       └── deploy.yml            # Deploy (KEIN keepalive.yml — UptimeRobot stattdessen)
│
├── package.json                  # Bun workspace (nur apps/web)
└── README.md
```

---

## Implementierungs-Phasen

### Phase 0: Feature-Validierung & Embedding-Evaluation (Gate)

1. **Essentia-Version-Alignment testen** (ERSTER Schritt):
   - 50 Tracks auswählen die in AcousticBrainz existieren
   - AcousticBrainz-JSON via API downloaden
   - Audio für diese 50 Tracks beschaffen (FMA oder Freemusicarchive)
   - MFCCs mit aktueller Essentia + YAML-Profil extrahieren
   - Paarweiser Vergleich: Korrelation muss > 0.95 sein
   - **Go/No-Go**: Wenn < 0.95 → Handcrafted Features NUR aus eigener Runtime, AcousticBrainz nur für Metadata
2. **Learned Embedding evaluieren**:
   - FMA-small (8K Tracks mit Genre-Labels) downloaden
   - MusiCNN-Embeddings + Handcrafted Features berechnen
   - **Same-Genre Precision@10**: Für jeden Track Top-10 Nachbarn finden, Genre-Match-Rate messen
   - Vergleich: MusiCNN vs. Handcrafted vs. Late Fusion
   - **Ziel**: MusiCNN P@10 > 50% (Handcrafted Baseline ~25-35%)
3. **Gewichtungs-Optimierung**: α für Late Fusion via Grid Search auf FMA-Validierungsset
4. **HPCP-Sanity**: A-440 Hz → Bin 0 dominant in 12-bin Chroma
5. **Go/No-Go Entscheidung**: Wenn MusiCNN P@10 < 40% → alternatives Modell testen (EffNet-Discogs)

### Phase 1: Projekt-Setup & Infrastruktur

1. GitHub Repo erstellen (`beattrack`)
2. Bun workspace aufsetzen
3. Next.js 15 App initialisieren (TailwindCSS, Vitest, Playwright)
4. Python FastAPI Projekt initialisieren (uv, pytest, essentia, essentia-tensorflow, procrastinate)
5. MusiCNN Modell downloaden (`msd-musicnn-1.pb`, 18 MB)
6. Supabase Projekt erstellen, Migrationen ausführen
7. CI/CD Pipeline (GitHub Actions)
8. Multi-stage Dockerfile (Essentia + TF + MusiCNN, Ziel <1 GB)
9. Railway Hobby Plan: Service Memory Limit 3 GB, Restart "On Failure"
10. Sentry + UptimeRobot einrichten
11. CORS-Konfiguration: Explizite Origin-Whitelist (Vercel Domain), nicht `*`

### Phase 2: Backend — Async Feature-Extraktion (TDD)

1. Test-Audio-Fixtures generieren (Sinuswellen, korrupte Files, FMA-Samples)
2. Tests schreiben:
   - Handcrafted-Vektor Shape == (44,), keine NaN
   - Learned-Embedding Shape == (200,), keine NaN
   - Deterministische Outputs
   - HPCP-Reduktion korrekt
   - MIME-Validierung blockt non-Audio
   - ffprobe blockt korrupte Files
   - Subprocess crasht graceful (kein Worker-Kill)
   - **RAM-Cap Test**: Subprocess wird bei 2 GB gekillt
   - **Semaphore Test**: 4. gleichzeitiger Upload → 503
   - **Connection-Pool**: Max 5 Connections zu Supabase
3. Validation-Pipeline: python-magic → ffprobe → Essentia Subprocess
4. Essentia + MusiCNN Extraction Pipeline implementieren
5. Procrastinate Worker (concurrency=1, Supavisor port 6543)
6. FastAPI Endpoints:
   - `POST /analyze` → Job erstellen (Semaphore + Rate-Limiting)
   - `GET /analyze/{job_id}/stream` → SSE (mit Connection-Limiter)
   - `GET /analyze/{job_id}/results` → Fallback
   - `POST /search` → URL-Metadata-Lookup
   - `GET /health` → DB + Stats + Model-Loading Check
7. Supabase pgvector Integration (Insert + Late-Fusion Similarity Query)
8. Startup-Validierung: Normalisierungs-Stats + MusiCNN-Modell laden
9. Temp-File-Cleanup (atexit + periodischer Cleanup-Task)
10. **Error-Responses**: Generische Fehler an Client, Details nur im Server-Log

### Phase 3: Daten — FMA + AcousticBrainz Seeding

1. FMA-medium downloaden (25K Tracks, ~22 GB, CC-lizenziert)
2. MusiCNN-Embeddings + Handcrafted Features für alle 25K berechnen (Batch-Job, ~1 Tag)
3. Normalisierungs-Stats berechnen → `config`-Tabelle
4. In Supabase laden → **25K Songs als initiale Seed-DB**
5. AcousticBrainz Feature CSVs + Highlevel-Dump downloaden
6. Stratified MBID-Liste erstellen (300K, genre-diversifiziert)
7. AcousticBrainz API: Lowlevel-JSON für 300K MBIDs fetchen
8. **Optional**: Proxy-Modell trainieren (AcousticBrainz-Features → MusiCNN-Embeddings)
9. AcousticBrainz Tracks in DB laden (mit/ohne Proxy-Embeddings)
10. MusicBrainz Metadata-Enrichment für Lücken
11. **Songs ohne Metadata (`metadata_status: 'failed'`) aus Suchergebnissen ausblenden**

### Phase 4: Backend — Song-Identifikation & URL-Input

1. AcoustID Integration (Chromaprint `fpcalc` → MusicBrainz ID)
   - Fallback: Song als "Unknown" analysieren
2. MusicBrainz API Client (Metadata, Rate-Limiting)
3. URL-Metadata-Extraktion (YouTube oEmbed, Spotify URL-Slug)
4. Fuzzy DB-Suche (pg_trgm)

### Phase 5: Frontend — Upload & Analyse-Flow (TDD)

1. Landing Page mit Upload-Zone
   - Client-seitige Validierung: Max 50 MB, nur MP3/WAV/FLAC/OGG
   - Upload direkt an Python API
   - CORS: Vercel-Domain explizit whitelisted
2. Analysis-Progress: SSE + Reconnect + "Wir wachen auf..."-Cold-Start-UX
3. **Opt-in Dialog** (NEU): "Dürfen wir die berechneten Merkmale speichern, um unsere Datenbank zu verbessern?" — vor Ergebnis-Anzeige, Checkbox, Default: Nein
4. URL-Input Komponente
5. Visuell verifizieren

### Phase 6: Frontend — Results & Feedback

1. Song-Card (Titel, Artist, Similarity %, BPM, Key, Search-Links, Feedback-Buttons)
2. Feature-Radar-Chart: 5 Kategorien (Klangfarbe, Harmonie, Tempo, Helligkeit, Intensität)
3. Results Page mit staggered Reveal (Framer Motion)
4. **Ergebnis-Filter**: BPM-Range, Similarity-Threshold
5. Responsive Design
6. **"Nicht in DB" als Feature-Positionierung** (Upload-CTA, nicht Fehler)

### Phase 7: Polish & Deploy

1. Error Handling & Loading States
   - Cold-Start UX: "Wir wachen gerade auf..."
   - Analyse-Timeout nach 180s mit Retry-Option
2. Privacy Policy (Audio nicht gespeichert, Features sind keine PII — "unsere Interpretation, keine Rechtsberatung")
3. SEO (Metadata, OG Tags)
4. Deploy: Vercel + Railway (Memory Limit 3 GB) + Supabase
5. UptimeRobot: 5-Min-Ping auf Railway `/health` + Supabase `SELECT 1`
6. E2E Test Suite
7. **Rollback-Plan**: Railway Deployment-History → Previous Deploy wiederherstellen

---

## Evaluation (NEU — quantitative Qualitätsmessung)

### FMA-Benchmark (Standard)

```python
# scripts/evaluate_similarity.py
# FMA-small: 8K Tracks mit Genre-Labels (8 Genres)

def evaluate_precision_at_k(embeddings, genre_labels, k=10):
    """Same-Genre Precision@K über gesamten Testset."""
    precisions = []
    for i, emb in enumerate(embeddings):
        distances = cosine_distances(emb, embeddings)
        top_k_indices = np.argsort(distances)[1:k+1]  # Skip self
        matches = sum(genre_labels[j] == genre_labels[i] for j in top_k_indices)
        precisions.append(matches / k)
    return np.mean(precisions)

# Erwartete Ergebnisse (basierend auf RecSys 2024 Paper):
# Handcrafted 44-dim:  P@10 ≈ 25-35%
# MusiCNN 200-dim:     P@10 ≈ 50-65%
# Late Fusion:         P@10 ≈ 55-70%
```

### Zusätzliche Evaluations-Methoden

1. **Same-Artist Precision**: Tracks desselben Künstlers müssen nah beieinander sein
2. **Cover Song Detection** (Covers80): Harmonische Similarity testen
3. **A/B User-Feedback**: Feedback-Tabelle in DB → Thumbs Up/Down aggregieren
4. **Random Baseline**: ~12.5% P@10 bei 8 Genres (1/8)

### Laufende Qualitäts-Monitoring

- Health-Check enthält **Canary Query**: Bekanntes Song-Paar muss Similarity > 0.8 haben
- Wenn Canary fehlschlägt → Sentry Alert → manuell prüfen ob Modell/Stats korrumpiert

---

## Testing-Strategie

### Backend (pytest, TDD)

```python
# Feature-Extraktion
def test_handcrafted_vector_shape():
    result = extract_features_safe("tests/fixtures/sine_440hz.wav")
    assert np.array(result["handcrafted"]).shape == (44,)
    assert not np.any(np.isnan(result["handcrafted"]))

def test_learned_embedding_shape():
    result = extract_features_safe("tests/fixtures/sine_440hz.wav")
    assert np.array(result["learned"]).shape == (200,)
    assert not np.any(np.isnan(result["learned"]))

def test_deterministic_output():
    r1 = extract_features_safe("tests/fixtures/sine_440hz.wav")
    r2 = extract_features_safe("tests/fixtures/sine_440hz.wav")
    np.testing.assert_array_almost_equal(r1["learned"], r2["learned"])

def test_hpcp_reduction_correct():
    result = extract_features_safe("tests/fixtures/sine_440hz.wav")
    hpcp_12 = np.array(result["handcrafted"])[26:38]
    assert np.argmax(hpcp_12) == 0  # Bin 0 = A

# Sicherheit
def test_mime_validation_rejects_non_audio():
    assert not validate_mime_type("tests/fixtures/not_audio.txt")
    assert not validate_mime_type("tests/fixtures/fake.mp3")  # PHP mit .mp3 Extension
    assert validate_mime_type("tests/fixtures/sine_440hz.wav")

def test_corrupt_file_handled_gracefully():
    with pytest.raises(FeatureExtractionError):
        extract_features_safe("tests/fixtures/corrupt.mp3")

# Load Control
def test_subprocess_memory_limit():
    """Subprocess darf nicht mehr als 2 GB RAM nutzen."""
    # Teste mit absichtlich großem Audio-File
    with pytest.raises(FeatureExtractionError):
        extract_features_safe("tests/fixtures/huge_synthetic.wav")

def test_upload_semaphore_returns_503():
    """4. gleichzeitiger Upload → 503."""
    # Mock Semaphore mit value=0
    ...

def test_supabase_pool_size():
    """Connection Pool darf max 5 Connections öffnen."""
    ...

# Error Handling
def test_error_response_no_stderr_leak():
    """Fehler-Responses dürfen keinen stderr-Inhalt enthalten."""
    response = client.post("/analyze", files={"file": corrupt_file})
    assert "stderr" not in response.json()["detail"].lower()
    assert "traceback" not in response.json()["detail"].lower()
```

### Frontend (Vitest)

```typescript
test('upload zone rejects files over 50MB', () => { ... })
test('upload zone rejects non-audio MIME types', () => { ... })
test('SSE connection receives progress updates', () => { ... })
test('SSE reconnects on connection drop', () => { ... })
test('results display song cards with search links', () => { ... })
test('feature radar chart renders 5 categories', () => { ... })
test('feedback buttons send rating to API', () => { ... })
test('opt-in dialog defaults to No', () => { ... })
test('cold-start message shown on 503/timeout', () => { ... })
```

### E2E (Playwright)

```typescript
test('full flow: upload → analyze → SSE → results', async ({ page }) => {
  await page.goto('/');
  await page.setInputFiles('[data-testid="upload"]', 'fixtures/test.mp3');
  await expect(page.locator('[data-testid="analysis-progress"]')).toBeVisible();
  await expect(page.locator('[data-testid="results"]')).toBeVisible({ timeout: 180000 });
  await expect(page.locator('[data-testid="song-card"]')).toHaveCount({ min: 1 });
  await expect(page.locator('[data-testid="feature-radar"]')).toBeVisible();
});
```

---

## Risiken & Mitigationen (aktualisiert)

| Risiko | Impact | Mitigation |
|---|---|---|
| MusiCNN-Embeddings liefern schlechte Similarity | Hoch | Phase 0 Gate mit FMA-Benchmark (P@10 > 40%), Fallback auf EffNet-Discogs |
| Essentia-Version inkompatibel mit AcousticBrainz | Hoch | Learned Embeddings als primäre Similarity (umgeht Problem), Handcrafted nur für Radar-Chart |
| Essentia crasht bei korrupten Files (C++ Segfault) | Hoch | Subprocess + RLIMIT_AS (2 GB) + MIME-Check + ffprobe |
| Concurrent Load sprengt Railway | Hoch | Procrastinate concurrency=1, Upload-Semaphore(3), SSE-Limiter(50), Service Memory Limit 3 GB |
| Railway OOM-Kill-Loop | Hoch | Restart "On Failure" (nicht "Always"), RLIMIT_AS, concurrency=1 |
| AcousticBrainz-API geht offline | Hoch | Alle Responses lokal archivieren, Feature CSVs als Backup |
| Railway-Kosten höher als $5/mo | Mittel | Realistisch ~$15/mo, Sleep-on-Inactivity Option für ~$5-8/mo |
| Supabase Connection-Limit (60 direct) | Mittel | Supavisor port 6543 (200 pooled), Pool max_size=5, listen_notify=False |
| Analyse dauert >60s | Mittel | Procrastinate Queue + SSE Progress + 180s Timeout |
| AcousticBrainz-Daten veraltet (post-2022 fehlt) | Mittel | FMA als frische Seed-Basis, User-Uploads als Wachstum |
| 30% leere Metadata in Ergebnissen | Mittel | `metadata_status: 'failed'` aus Suchergebnissen ausblenden |
| GitHub Actions Cron deaktiviert bei Inaktivität | Mittel | UptimeRobot statt GitHub Actions für Keepalive |
| Proxy-Modell (AcousticBrainz→MusiCNN) zu ungenau | Mittel | FMA als primäre Seed (echte Embeddings), AcousticBrainz optional |
| Supabase Free Tier pausiert nach 7 Tagen | Mittel | UptimeRobot Ping alle 5 Min |
| YouTube oEmbed gibt keinen Artist | Mittel | Titel-Heuristik + Fuzzy-Search, Fallback auf Upload |
| stderr-Leak in Error-Responses | Niedrig | Generische Fehler an Client, Details nur in Server-Log/Sentry |
| DSGVO Opt-in für Feature-Speicherung | Niedrig | Expliziter Opt-in-Dialog, Default: Nein |
| API-Missbrauch (kein Auth) | Mittel | Rate-Limiting (5 req/min) + Upload-Semaphore(3) + Connection-Limiter |

---

## Sicherheit (NEU — dedizierter Abschnitt)

### Upload-Sicherheit
1. **MIME-Type vor Disk-Write** (python-magic): Blockt PHP/EXE/etc. mit Audio-Extension
2. **File-Size Header-Check**: Max 50 MB, bevor Stream gelesen wird
3. **ffprobe Validierung**: Format-Integrität nach Disk-Write
4. **Temp-Directory Isolation**: Eigenes tmpdir, periodischer Cleanup, atexit-Cleanup
5. **Subprocess RAM-Cap**: `RLIMIT_AS = 2 GB` verhindert Memory-Bomb-Angriffe

### API-Sicherheit
1. **CORS**: Explizite Origin-Whitelist (Vercel-Domain), nicht `*`
2. **Rate-Limiting**: 5 req/min/IP auf `/analyze` (slowapi)
3. **Concurrent-Limit**: Semaphore(3) für Uploads, Semaphore(50) für SSE
4. **Error Sanitization**: Kein stderr/Traceback in API-Responses
5. **Metadata aus User-Uploads**: Pydantic-Validierung, parametrisierte SQL-Queries (kein String-Concat)

### DSGVO / Privacy
- **Kein User-Account** — anonyme Nutzung
- **Audio sofort gelöscht** nach Analyse (Temp-Dir + Cleanup-Cron)
- **Feature-Opt-in**: Expliziter Dialog vor Speicherung ("unsere Interpretation — keine Rechtsberatung")
- **Kein IP-Logging** über Rate-Limiting hinaus
- **Privacy Policy**: Klar formuliert, keine juristischen Garantien

---

## Lizenz-Übersicht

| Komponente | Lizenz | Kosten | Hinweis |
|---|---|---|---|
| Essentia | AGPL v3 | Free | Beattrack ist Open Source → OK |
| essentia-tensorflow | AGPL v3 | Free | MusiCNN/EffNet-Modelle |
| MusiCNN Modell | AGPL v3 | Free | 18 MB, via Essentia-Repo |
| AcousticBrainz Data | CC0 / Open | Free | Eingefroren seit 2022, API noch live |
| FMA Dataset | CC-BY | Free | 25K-106K Tracks mit Audio |
| AcoustID API | Free (non-commercial) | Free | Beattrack muss non-commercial bleiben |
| MusicBrainz API | Free | Free | User-Agent Pflicht |
| Procrastinate | MIT | Free | |
| python-magic | MIT | Free | |
| Supabase | Free Tier | Free | 500 MB DB |
| Vercel | Free Tier | Free | |
| Railway | Hobby | ~$15/mo | Realistisch, nicht $5 |
| Sentry | Free Tier | Free | 5K Events/Mo |
| UptimeRobot | Free Tier | Free | 50 Monitors |

---

## Changelog v1.0 → v2.0

| Bereich | v1.0 | v2.0 | Grund |
|---|---|---|---|
| **Similarity** | 44-dim Handcrafted only | MusiCNN (200-dim) + Handcrafted (Late Fusion) | MFCCs 40% schlechter als Learned Embeddings |
| **Feature-Space** | AcousticBrainz-Features direkt nutzen | Learned Embeddings umgehen Versionsproblem | Essentia beta2 ≠ beta6, confirmed Breaking Changes |
| **ETL** | 589 GB Dump sequential scan | Feature CSVs (3 GB) + API (20-40 min) | 200x weniger Daten, 100x schneller |
| **Seed-DB** | 300K AcousticBrainz only | FMA (25K echte Embeddings) + AcousticBrainz (300K optional) | Audio nötig für Learned Embeddings |
| **Load Control** | Nicht adressiert | Semaphore + concurrency=1 + RLIMIT_AS + Connection-Pool | Ohne das: OOM/Connection-Exhaustion unter Last |
| **Kosten** | ~$5/mo | ~$15/mo (oder ~$5-8 mit Sleep) | Railway rechnet CPU+RAM pro Minute ab |
| **Keepalive** | GitHub Actions Cron | UptimeRobot | GitHub deaktiviert Cron bei inaktiven Repos |
| **Sicherheit** | Nicht adressiert | MIME-Check, Error Sanitization, CORS Whitelist | Upload-Angriffe, Info-Leak via stderr |
| **DSGVO** | "Feature-Vektoren = keine PII" | Opt-in Dialog + "unsere Interpretation" Disclaimer | Vereinfachte Rechtsaussage war riskant |
| **Monitoring** | Sentry only | Sentry + UptimeRobot + Canary Query | 5K Events/Mo reicht nicht bei viral |
| **SoundCloud** | Im Diagramm | Entfernt | Keine zugängliche Metadata-API |
| **Metadata** | Unknown Songs in Ergebnissen | `metadata_status: 'failed'` ausblenden | "Artist: Unknown" ist inakzeptable UX |
| **Rollback** | Nicht adressiert | Railway Deployment-History | Kein Recovery-Plan bei kaputtem Deploy |
