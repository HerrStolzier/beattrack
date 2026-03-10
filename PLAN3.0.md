# Beattrack - Sonically Similar Song Finder (v3.0)

## Context

Plattform-Radios (Spotify, YouTube, etc.) empfehlen Songs mit einem Mix aus kollaborativem Filtering und Audio-Features. Beattrack verfolgt einen **transparenten, Open-Source-Ansatz**: Audio-Features werden direkt analysiert und dem User erklaert — keine Black-Box, keine Engagement-Optimierung, kein Lock-in.

**Differenzierung**: Nicht "besser als Spotify", sondern **anders** — transparent, erklärbar, unabhängig. Der User sieht *warum* Songs ähnlich klingen (Feature-Radar-Chart mit 5 menschlichen Kategorien), nicht nur *dass* sie es tun.

**Constraints**: Keine Lizenzen, keine gekauften Songs/Daten, 100% legal, Open Source (AGPL-kompatibel), non-commercial (AcoustID-Requirement — bewusste Entscheidung, siehe Lizenz-Abschnitt).

---

## Architektur

```
User Input (File Upload / URL)
        │
        ▼
┌─────────────────────┐
│   Next.js Frontend   │  ← Drag & Drop Upload (direkt an Backend)
│   (Vercel)           │  ← SSE Progress + Reconnect
└────────┬────────────┘
         │ Direct Upload (kein BFF-Proxy für Files)
         ▼
┌─────────────────────┐
│  Python FastAPI      │  ← Essentia MusicExtractor + MusiCNN (Subprocess)
│  (Railway Hobby)     │  ← AcoustID Song-Identifikation (via eigene Queue)
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

1. **Datei-Upload**: User lädt MP3/WAV/FLAC hoch (max 50 MB, max 15 Min Dauer) → Upload direkt an Python API → Postgres Job-Queue → Essentia extrahiert Features + Learned Embedding (in isoliertem Subprocess mit RAM-Cap) → pgvector Similarity Search → Ergebnis via SSE
2. **URL (YouTube)**: Metadaten via oEmbed extrahieren → Song in DB suchen (Fuzzy-Match) → wenn gefunden: Features aus DB nutzen → wenn nicht gefunden: User auffordern, Audio-Datei hochzuladen

**URL-Input lädt kein Audio herunter** — nur öffentliche Metadaten.

**Spotify-URLs**: Spotify-URLs enthalten keinen Track-Namen im URL-Slug (nur Track-ID). Ohne Spotify-API kein Metadata-Zugriff → **Spotify-URL-Support entfernt**. Stattdessen: Spotify Search-Links in den Ergebnissen (z.B. `https://open.spotify.com/search/{title} {artist}`).

### Async-Analyse-Flow (kritisch)

Feature-Extraktion dauert **10-60 Sekunden**. Synchrone HTTP-Requests brechen bei Vercel (30s Timeout). Deshalb:

```
POST /analyze (File Upload)
  → MIME-Type-Validierung VOR Disk-Write (python-magic)
  → File-Size Check (max 50 MB)
  → Validiert Audio mit ffprobe (Format, Integrität, Dauer ≤ 15 Min)
  → Speichert Datei temporär
  → Erstellt Job in Postgres Queue (Procrastinate)
  → Returns: { job_id: "abc-123", status: "queued" }

GET /analyze/{job_id}/stream  (SSE)
  → Server-Sent Events: { status: "queued" | "processing" | "completed" | "failed", progress?: 0.0-1.0 }
  → Heartbeat alle 15s (": keepalive\n\n") — verhindert Zombie-Connections
  → Bei "completed": enthält Result-Daten inline
  → Stale-Connection-Timeout: 300s ohne Client-Activity → serverseitiger Close

GET /analyze/{job_id}/results  (Fallback)
  → Returns: { song: {...}, similar: [...] }  (wenn completed)
```

Frontend verbindet sich per SSE auf `/stream`. Kein Polling nötig — Server pushed Updates.

**Fallback**: Wenn SSE-Connection abbricht, pollt Frontend `/results` mit exponential Backoff.

### Load Control

```python
# === Concurrent Upload Limiter ===
UPLOAD_SEMAPHORE = asyncio.Semaphore(3)       # Max 3 gleichzeitige Uploads
SSE_LIMITER = asyncio.Semaphore(50)           # Max 50 offene SSE-Connections
SSE_HEARTBEAT_INTERVAL = 15                   # Sekunden — verhindert Zombie-Connections
SSE_STALE_TIMEOUT = 300                       # 5 Min ohne Client-Activity → Close

@app.post("/analyze")
async def analyze_audio(file: UploadFile):
    if UPLOAD_SEMAPHORE._value == 0:
        raise HTTPException(503, "Server at capacity. Retry shortly.")
    async with UPLOAD_SEMAPHORE:
        # MIME-Check → ffprobe (inkl. Dauer-Check) → enqueue
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
        "listen_notify": False,           # Spart 1 Connection, Polling (5s Intervall → ~2.5s avg Latenz)
        "shutdown_graceful_timeout": 300.0,
    }
)

# === Subprocess RAM-Cap (NUR auf Linux wirksam) ===
import resource, platform

def limit_memory(max_bytes: int = 2 * 1024**3):  # 2 GB
    """RLIMIT_AS — nur auf Linux (Railway) wirksam. Auf macOS ignoriert der Kernel das Limit."""
    if platform.system() == "Linux":
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

## Dual-Embedding-Strategie (Kernänderung seit v2.0)

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

**Empfehlung Phase 0**: MusiCNN (200-dim) als Default testen. Fallback: EffNet-Discogs.

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

def weighted_handcrafted(a: np.ndarray, b: np.ndarray) -> float:
    """Gewichtete Similarity über Handcrafted-Feature-Gruppen.
    Input: normalisierte 44-dim Vektoren (Z-Score).
    Output: Skalar in [-1, 1] (gewichtete Cosine-Similarities)."""
    return (
        0.30 * cosine(a[0:13], b[0:13]) +      # MFCC mean
        0.10 * cosine(a[13:26], b[13:26]) +     # MFCC stdev
        0.25 * cosine(a[26:38], b[26:38]) +     # HPCP 12-bin
        0.20 * cosine(a[38:40], b[38:40]) +     # Spectral (centroid + rolloff)
        0.15 * rhythm_similarity(a[40:44], b[40:44])  # BPM, ZCR, Loudness, Danceability
    )

def rhythm_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Rhythm-Feature-Similarity (4 dims: BPM, ZCR, Loudness, Danceability).
    BPM hat überproportionalen Einfluss — wird separat gewichtet."""
    bpm_sim = 1.0 - min(abs(a[0] - b[0]) / 50.0, 1.0)  # ±50 BPM = 0 Similarity
    other_sim = cosine(a[1:], b[1:])                      # ZCR, Loudness, Danceability
    return 0.5 * bpm_sim + 0.5 * other_sim
```

**Normalisierungs-Garantie**: Beide Teile der Fusion liefern Werte in [-1, 1]:
- `cosine()` auf beliebigen Vektoren → [-1, 1]
- `rhythm_similarity()` → [0, 1] (konservativ — BPM-Distanz ist immer ≥ 0)
- Gesamt-Similarity: Gewichtete Summe → [-1, 1]

### pgvector Schema

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
    learned_embedding VECTOR(200) NOT NULL,   -- MusiCNN
    handcrafted_raw VECTOR(44) NOT NULL,      -- Roh-Vektor (für Re-Normalisierung)
    handcrafted_norm VECTOR(44) NOT NULL,     -- Z-Score-normalisierter Vektor
    -- Metadata
    source TEXT DEFAULT 'fma',                -- 'fma' | 'user_upload'
    embedding_type TEXT DEFAULT 'real',       -- 'real' (echtes MusiCNN) — kein Proxy
    metadata_status TEXT DEFAULT 'complete',  -- 'complete' | 'pending' | 'failed'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW Index auf Learned Embedding (primäre Suche)
CREATE INDEX ON songs USING hnsw (learned_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Optional: Index auf Handcrafted für Filter-Queries
CREATE INDEX ON songs USING hnsw (handcrafted_norm vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**Speicher-Budget (25K-100K Songs, FMA-basiert)**:

| Komponente | 25K Songs | 100K Songs |
|---|---|---|
| Learned Embedding (200-dim × 4B) | ~2 MB | ~8 MB |
| Handcrafted Raw + Norm (44-dim × 4B × 2) | ~0.9 MB | ~3.5 MB |
| Metadata (Titel, Artist, Album) | ~7 MB | ~30 MB |
| HNSW Index (learned) | ~10 MB | ~40 MB |
| HNSW Index (handcrafted) | ~5 MB | ~20 MB |
| Procrastinate Job-Tabellen | ~5 MB | ~5 MB |
| **Total** | **~30 MB** | **~107 MB** |

Massiv unter dem Supabase Free Tier Limit (500 MB). Raum für organisches Wachstum durch User-Uploads.

---

## Feature-Space-Kompatibilität

### Das Problem

AcousticBrainz-Features wurden mit **Essentia v2.1_beta2** berechnet. `pip install essentia` liefert **v2.1b6.dev1389**. Confirmed Breaking Changes (MFCC logType, MelBands, HPCP size defaults).

### Lösung: Eigene Runtime, kein Mischen

**v3.0-Entscheidung**: AcousticBrainz-Features werden **nicht** für Similarity verwendet — nur für Metadata (BPM, Key, Loudness als Filter/Anreicherung). Alle Embeddings und Handcrafted-Vektoren kommen aus **einer einzigen Essentia-Version** (eigene Runtime).

Begründung:
- Learned Embeddings (MusiCNN) brauchen Audio-Input → AcousticBrainz hat kein Audio
- Handcrafted Features aus verschiedenen Essentia-Versionen mischen → unzuverlässig
- FMA-Dataset hat Audio → konsistente Berechnung beider Vektoren möglich

**Das Proxy-Modell (v2.0 Option A) ist gestrichen** — informationstheoretisch kann ein MLP aus 44-dim MFCC-Features keine 200-dim MusiCNN-Embeddings erzeugen, die Produktionsstil und Gesangsstil kodieren. Das Risiko einer unbrauchbaren Approximation ist zu hoch.

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
- **essentia-tensorflow** (AGPL v3) — MusiCNN Inference (18 MB Modell, CPU-only)
- **Procrastinate** (MIT, v3.7.2) — Postgres-basierte Job-Queue
  - `concurrency=1` (max 1 paralleler Analyse-Job)
  - `listen_notify=False` (spart 1 DB-Connection, Polling mit ~2.5s avg Latenz)
  - Pool via Supavisor Port 6543, `max_size=5`
- **python-magic** — MIME-Type-Validierung vor Disk-Write
- **uv** — Python Package Manager
- **Pydantic v2** — Request/Response Validation
- **slowapi** — IP-basiertes Rate-Limiting (5 req/min auf `/analyze`)
- **Sentry** (Free Tier) + **UptimeRobot** (Free, 5-Min-Ping) — Error Tracking + Uptime
- **Chromaprint** (`pyacoustid` + `fpcalc` im Docker-Image) — AcoustID Fingerprinting
  - Eigene asyncio Queue (max 3 req/s, AcoustID Rate-Limit)

### Audio-Validierung (Reihenfolge!)
1. **python-magic**: MIME-Type prüfen BEVOR Datei auf Disk geschrieben wird
2. **File-Size**: Max 50 MB Check auf Content-Length Header
3. **ffprobe**: Format-Integrität, Codec-Check, **Dauer ≤ 15 Minuten** nach Disk-Write
4. **Essentia in Subprocess**: `preexec_fn=limit_memory(2GB)` (nur Linux), `timeout=180`

**Dauer-Validierung (NEU v3.0)**: Ein 50 MB FLAC kann unkomprimiert mehrere GB werden. Maximale Audio-Dauer = 15 Minuten begrenzt die unkomprimierte Größe auf ~300 MB (16-bit, 44.1 kHz, Stereo).

### Datenbank
- **Supabase** (Free Tier: 500 MB DB, 200 Supavisor Connections)
- **pgvector** Extension — HNSW Index für Cosine Similarity
- **pg_trgm** — Fuzzy-Text-Suche für URL-Input
- Verbindung **ausschließlich über Supavisor** (Port 6543, Transaction Mode)
- `prepare_threshold=None` (Supavisor-kompatibel)

### Song-Identifikation
- **AcoustID** (free, non-commercial, 3 req/s) — Fingerprint → MusicBrainz Recording ID
  - Eigene Rate-Limiting-Queue im Backend (asyncio, max 2 req/s mit Headroom)
  - Fallback: Song als "Unknown" analysieren — Similarity funktioniert trotzdem
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
- **UptimeRobot** — Uptime-Monitoring (free)
- **GitHub Actions** — CI/CD (NICHT für Keepalive)

### Keepalive-Strategie (überarbeitet)

**Problem**: Railway Sleep-on-Inactivity und Supabase Free Tier Pause (7 Tage ohne DB-Activity) beißen sich.

**Lösung**: Zwei UptimeRobot-Monitors:
1. **Railway `/health`** (alle 5 Min) — weckt Railway auf, Railway pingt DB via Health-Check
2. **Supabase Direct** (alle 6 Stunden) — `https://PROJECT.supabase.co/rest/v1/config?select=key&limit=1` mit `apikey` Header — unabhängig von Railway

**Fallback bei UptimeRobot-Ausfall**: Supabase pausiert nach 7 Tagen. Beim nächsten Request schlägt die DB-Verbindung fehl → Sentry Alert → manuell reaktivieren. Akzeptables Risiko für ein Side-Project.

### Kosten-Realität

Railway rechnet CPU + RAM ab dem Moment wo der Container läuft:

**Option A — 24/7 (empfohlen für aktive Nutzung)**:

| Posten | Kosten/Monat |
|---|---|
| RAM: 1 GB × 730h | ~$10 |
| CPU: 0.25 vCPU × 730h | ~$5 |
| Abzgl. Usage Credit | -$5 |
| Railway Plan-Basis | $5 |
| **Railway Total** | **~$15/Monat** |

**Option B — Sleep-on-Inactivity (sporadische Nutzung)**:

| Posten | Kosten/Monat |
|---|---|
| Aktive Stunden: ~50-100h/mo | ~$2-4 |
| Railway Plan-Basis | $5 |
| **Railway Total** | **~$7-9/Monat** |

**Cold-Start-Realität bei Sleep**: HTTP-Handler ~5-10s, aber TF-Modell-Loading beim ersten Job nach Sleep: **30-90s** realistisch. Die "Wir wachen auf..."-UX muss darauf kalibriert sein. Progress-Bar erst nach Modell-Loading starten.

| Service | Plan | Kosten/Monat |
|---|---|---|
| Vercel | Free | $0 |
| Railway | Hobby | **$7-15** |
| Supabase | Free | $0 |
| Sentry | Free | $0 |
| UptimeRobot | Free | $0 |
| **Total** | | **~$7-15/Monat** |

---

## Daten-Strategie (v3.0 — vereinfacht)

### Designentscheidung: Qualität > Quantität

**v2.0 wollte 300K Songs** via AcousticBrainz + Proxy-Modell. Das ist gestrichen.

**v3.0 startet mit FMA-Daten (echte Embeddings) + organisches Wachstum durch User-Uploads.**

Begründung:
1. **Proxy-Modell ist unzuverlässig** — 44-dim MFCC → 200-dim MusiCNN ist informationstheoretisch nicht fundiert
2. **FMA-Katalog-Limitation ist ein Feature, kein Bug** — ehrlich kommuniziert: "Unsere Datenbank enthält [X] Songs — jeder Upload erweitert sie für alle"
3. **Jeder User-Upload mit Opt-in erzeugt echte Embeddings** — das ist der nachhaltige Wachstumspfad

### Ehrliche Katalog-Kommunikation

FMA-medium = 25K CC-lizenzierte Tracks. Zu >90% Indie/Underground. Mainstream-Musik fehlt.

**UX-Lösung**: Nicht verstecken, sondern zum Feature machen:
- "Unsere Datenbank wächst mit jedem Upload"
- Similarity-Score zeigt an wie gut der Match ist — bei niedrigem Score: "Wir haben noch nicht viele Songs die ähnlich klingen. Dein Upload hilft!"
- Upload-Opt-in prominent positioniert: "Erlaube uns, die berechneten Merkmale zu speichern — so finden andere User ähnliche Songs"

### Seed-Pipeline

#### Schritt 1: FMA-medium Download + Processing

1. FMA-medium downloaden (25K Tracks, ~22 GB, CC-BY lizenziert)
2. Für alle 25K Tracks berechnen (Batch-Job auf EC2 Spot, ~1 Tag):
   - MusiCNN Learned Embedding (200-dim)
   - Handcrafted Features (44-dim)
   - BPM, Key, Dauer
3. Metadata aus FMA CSV extrahieren (Title, Artist, Genre)
4. **MusicBrainz MBID Matching** (optional, best-effort):
   - Artist/Title Fuzzy-Match gegen MusicBrainz
   - ~50-70% Match-Rate erwartet
   - Nicht-gematchte Songs bleiben ohne MBID — AcoustID Lookup findet sie nur via Fuzzy-Text

#### Schritt 2: Normalisierung + DB-Load

1. Globale Z-Score-Normalisierung der Handcrafted Features
2. Normalisierungs-Stats in `config`-Tabelle speichern
3. Raw + normalisierte Vektoren + Learned Embeddings in Supabase laden

#### Schritt 3 (optional): FMA-large Erweiterung

Wenn Phase 0 Evaluation positiv und Supabase-Storage reicht:
- FMA-large (106K Tracks, ~100 GB, CC-BY)
- Gleiche Pipeline wie Schritt 1, auf größerer Basis
- ~107 MB DB-Speicher (komfortabel unter 500 MB)

#### Schritt 4: AcousticBrainz Metadata-Enrichment (nur Metadata, keine Vektoren)

1. AcousticBrainz Feature CSVs downloaden (3 GB) — BPM, Key, Loudness für 29.46M Submissions
2. Cross-Reference mit FMA-Songs: Metadata anreichern wo FMA-Daten lückenhaft
3. **Keine Vektoren aus AcousticBrainz** — nur skalare Metadata-Werte (BPM, Key) sind versionsstabil

**Kritisch**: AcousticBrainz-API ist noch live aber ohne SLA. Feature CSVs jetzt downloaden und lokal archivieren.

### ETL-Kosten (Einmalig)

| Posten | Kosten |
|---|---|
| EC2 Spot (c5.xlarge, ~8h für 25K Tracks) | ~$1.20 |
| EBS Storage (100 GB, 1 Tag) | ~$0.30 |
| FMA Download (22 GB) | $0 |
| **Total** | **~$1.50** |

### Wachstums-Strategie

| Phase | Songs | Quelle | Timeline |
|---|---|---|---|
| Launch | 25K | FMA-medium | Phase 3 |
| Monat 1-3 | 25K + User-Uploads | Opt-in User-Uploads | Organisch |
| Optional | 100K+ | FMA-large | Wenn Storage reicht |

**Kein Proxy-Modell, keine approximierten Embeddings. Jeder Song in der DB hat echte MusiCNN-Embeddings.**

### Normalisierungs-Drift

- Seed-Stats sind Baseline, werden **nicht** automatisch angepasst
- `normalization_stats` in DB-Tabelle `config`
- **Startup-Validierung**: API prüft beim Start ob Stats vorhanden, sonst Fehler
- **Re-Normalisierung**: Raw-Vektoren immer mitgespeichert. Bei >50K User-Uploads: neue Stats berechnen (Batch-Job)

---

## Feature-Extraktion Pipeline (Essentia + MusiCNN)

```python
import subprocess, json, resource, platform
import numpy as np

# === RAM-Cap für Subprocesses (NUR Linux) ===
def limit_memory(max_bytes: int = 2 * 1024**3):  # 2 GB
    """RLIMIT_AS auf Linux. Auf macOS wirkungslos (Kernel ignoriert seit 10.15)."""
    if platform.system() == "Linux":
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
        "duration": float(features.get('metadata.audio_properties.length', 0)),
    }


def reduce_hpcp(hpcp_36: np.ndarray) -> np.ndarray:
    """36-bin HPCP → 12-bin Chroma (3 Sub-Bins pro Halbton summieren)."""
    return hpcp_36.reshape(12, 3).sum(axis=1)


if __name__ == "__main__":
    result = extract_all(sys.argv[1])
    print(json.dumps(result))
```

### AcoustID Rate-Limiting Queue (NEU v3.0)

```python
# === AcoustID eigene Queue — verhindert 429 bei concurrent Uploads ===
import asyncio

class AcoustIDQueue:
    """Rate-limited AcoustID client. Max 2 req/s (Headroom unter 3 req/s Limit)."""

    def __init__(self, api_key: str, max_rps: float = 2.0):
        self.api_key = api_key
        self.interval = 1.0 / max_rps
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def identify(self, fingerprint: str, duration: float) -> str | None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait = self.interval - (now - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = asyncio.get_event_loop().time()

        # AcoustID API call...
        return musicbrainz_id_or_none
```

### Temporäre Dateien + Cleanup

```python
import tempfile, shutil, atexit

TEMP_DIR = tempfile.mkdtemp(prefix="beattrack_")

# atexit: Best-effort Cleanup bei normalem Shutdown (SIGTERM)
# NICHT bei SIGKILL (Railway OOM-Kill) — deshalb ist der periodische Cleanup primär
atexit.register(lambda: shutil.rmtree(TEMP_DIR, ignore_errors=True))

# Primärer Cleanup: Periodischer Task (alle 15 Min)
@app.on_event("startup")
async def schedule_cleanup():
    asyncio.create_task(periodic_cleanup(TEMP_DIR, max_age_minutes=15))
```

---

## Similarity Search

```sql
CREATE EXTENSION vector;
CREATE EXTENSION pg_trgm;

-- Normalisierungs-Config
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User-Feedback (transparent: beeinflusst aktuell NICHT die Similarity)
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
      AND metadata_status != 'failed'
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

### Fallback
- "Dieser Song ist noch nicht in unserer Datenbank — lade die Audio-Datei hoch und wir finden trotzdem ähnlich klingende Songs!"
- Upload-CTA prominent anzeigen

**Hinweis**: Spotify-URL-Support entfernt (Track-Name nicht in URL, API-Key nötig). SoundCloud entfernt (keine zugängliche API).

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
│   │   │   └── api/              # BFF Routes (Metadata-Proxy)
│   │   ├── components/
│   │   │   ├── upload-zone.tsx   # Drag & Drop, max 50MB, Format-Validierung
│   │   │   ├── analysis-progress.tsx  # SSE + Progress + Cold-Start-UX
│   │   │   ├── song-card.tsx     # Title, Artist, Similarity, Search-Links, Feedback
│   │   │   ├── feature-radar.tsx # Radar-Chart: 5 menschliche Kategorien
│   │   │   ├── url-input.tsx     # YouTube only
│   │   │   └── opt-in-dialog.tsx # DSGVO: "Features in DB speichern?"
│   │   ├── lib/
│   │   │   ├── api.ts            # Backend API client
│   │   │   └── sse.ts            # SSE-Client mit Reconnect + Heartbeat-Detection
│   │   ├── __tests__/
│   │   ├── vitest.config.ts
│   │   └── package.json
│   │
│   └── api/                      # Python FastAPI Backend
│       ├── app/
│       │   ├── main.py           # FastAPI + /health + Startup-Validierung + Sentry
│       │   ├── middleware/
│       │   │   ├── rate_limit.py # slowapi + Semaphore
│       │   │   └── mime_check.py # MIME-Validierung vor Disk-Write
│       │   ├── routes/
│       │   │   ├── analyze.py    # POST /analyze → Job, GET /analyze/{id}/stream (SSE + Heartbeat)
│       │   │   ├── search.py     # POST /search (URL → metadata lookup)
│       │   │   └── identify.py   # POST /identify (AcoustID lookup, rate-limited)
│       │   ├── services/
│       │   │   ├── features.py   # Subprocess-Wrapper + RAM-Cap + Normalization
│       │   │   ├── similarity.py # pgvector query + Late Fusion + rhythm_similarity
│       │   │   ├── acoustid.py   # AcoustID client mit eigener Rate-Limiting Queue
│       │   │   ├── metadata.py   # YouTube oEmbed
│       │   │   └── validation.py # MIME + ffprobe + Dauer-Check
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
│       │   ├── fixtures/         # Test audio files
│       │   ├── test_features.py
│       │   ├── test_similarity.py
│       │   ├── test_metadata.py
│       │   ├── test_validation.py  # inkl. Dauer-Check
│       │   ├── test_load_control.py
│       │   ├── test_acoustid_queue.py  # Rate-Limiting Queue
│       │   └── test_api.py
│       ├── pyproject.toml
│       └── Dockerfile            # Multi-stage: Python 3.12 + Essentia + TF + MusiCNN
│
├── scripts/
│   ├── seed_fma.py               # FMA-medium/large Seed (eigene Embeddings)
│   ├── enrich_metadata.py        # MusicBrainz Metadata für Lücken
│   ├── validate_features.py      # Phase-0: Embedding-Qualität
│   ├── evaluate_similarity.py    # FMA Genre-Precision Benchmark
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
│       └── deploy.yml            # Deploy
│
├── package.json                  # Bun workspace (nur apps/web)
└── README.md
```

---

## Implementierungs-Phasen

Jede Phase ist in kleine, abgeschlossene **Iterationen** unterteilt. Eine Iteration = ein eigenständiger Task mit klarem Deliverable. Iterationen innerhalb einer Phase können sequentiell abgearbeitet werden ohne den gesamten Plan im Context zu brauchen — nur die aktuelle Phase + relevante Referenz-Sektionen.

**Regel**: Jede Iteration endet mit einem lauffähigen, testbaren Zustand. Kein "halb fertig".

---

### Phase 0: Embedding-Evaluation (Gate)

> **Ziel**: Go/No-Go-Entscheidung bevor eine Zeile Produktionscode geschrieben wird.
> **Kontext nötig**: Nur dieser Abschnitt + "Dual-Embedding-Strategie".

**Iteration 0.1 — Essentia + MusiCNN lokal zum Laufen bringen**
- `uv` Projekt mit essentia + essentia-tensorflow
- MusiCNN Modell downloaden (`msd-musicnn-1.pb`)
- 1 Sinuswelle (440 Hz) → Embedding extrahieren → Shape (200,) bestätigen
- Deliverable: Funktionierendes `extract.py` Script

**Iteration 0.2 — FMA-small Benchmark**
- FMA-small (8K Tracks, 8 Genres) downloaden
- MusiCNN-Embeddings + Handcrafted (44-dim) für alle 8K berechnen
- `evaluate_similarity.py`: Same-Genre Precision@10
- Deliverable: P@10 Zahlen für MusiCNN, Handcrafted, Late Fusion

**Iteration 0.3 — Go/No-Go Entscheidung**
- Wenn MusiCNN P@10 > 50% → Go. Weiter mit Phase 1.
- Wenn 40-50% → Late Fusion Gewichtung optimieren (Grid Search α)
- Wenn < 40% → EffNet-Discogs testen (gleicher Benchmark)
- Wenn EffNet auch < 40% → Projekt re-evaluieren

---

### Phase 1: Projekt-Skeleton

> **Ziel**: Monorepo steht, CI läuft, alle Services erreichbar.
> **Kontext nötig**: Nur dieser Abschnitt + "Tech Stack" + "Projekt-Struktur".

**Iteration 1.1 — Monorepo + Frontend Skeleton**
- GitHub Repo `beattrack`, Bun workspace
- Next.js 15 + TailwindCSS v4 + Vitest
- Leere Landing Page die "Hello Beattrack" zeigt
- Deliverable: `bun dev` → Seite im Browser

**Iteration 1.2 — Backend Skeleton**
- Python FastAPI Projekt (uv, pytest)
- `GET /health` → `{ status: "ok" }`
- Deliverable: `uv run uvicorn app.main:app` → Health-Check erreichbar

**Iteration 1.3 — Supabase + Migrations**
- Supabase Projekt erstellen
- Migrationen: Schema (songs, config, feedback, procrastinate)
- pgvector + pg_trgm Extensions
- Deliverable: `supabase db push` → Tabellen existieren

**Iteration 1.4 — Docker + CI**
- Multi-stage Dockerfile (Essentia + TF + MusiCNN, Ziel <1 GB)
- GitHub Actions CI: lint + pytest + vitest
- Deliverable: CI grün auf `main`

**Iteration 1.5 — Railway + Vercel Deploy**
- Railway Hobby Plan: Memory Limit 3 GB, Restart "On Failure"
- Vercel: Frontend deployen
- CORS Whitelist (Vercel-Domain)
- UptimeRobot: 2 Monitors (Railway + Supabase Direct)
- Sentry einrichten
- Deliverable: Frontend + Backend live erreichbar

---

### Phase 2: Backend Core (TDD)

> **Ziel**: Audio rein → Features + Embedding raus → in DB → Similar Songs zurück.
> **Kontext nötig**: Nur dieser Abschnitt + "Feature-Extraktion Pipeline" + "Similarity Search".

**Iteration 2.1 — Audio-Validierung**
- Test-Fixtures: Sinuswelle, korruptes File, Fake-MP3 (PHP mit .mp3 Extension), File >15 Min
- TDD: MIME-Check (python-magic), File-Size, ffprobe (Format + Dauer ≤ 15 Min)
- Deliverable: `validation.py` mit Tests grün

**Iteration 2.2 — Feature-Extraktion Subprocess**
- TDD: Handcrafted (44,) Shape, Learned (200,) Shape, keine NaN, deterministisch
- TDD: HPCP-Reduktion (36→12), rhythm_similarity Bounds [0,1]
- Subprocess mit RAM-Cap (Linux-only), timeout=180
- Deliverable: `extract.py` + `features.py` mit Tests grün

**Iteration 2.3 — Procrastinate Job-Queue**
- Worker mit concurrency=1, Supavisor port 6543
- Job-Lifecycle: queued → processing → completed/failed
- Deliverable: Job enqueuen → Worker verarbeitet → Status in DB

**Iteration 2.4 — API Endpoints (Analyze)**
- `POST /analyze` → Validierung → Job erstellen (+ Semaphore + Rate-Limiting)
- `GET /analyze/{job_id}/stream` → SSE mit Heartbeat (15s) + Stale-Timeout (300s)
- `GET /analyze/{job_id}/results` → Fallback-Polling
- TDD: Semaphore(3) → 4. Upload = 503, SSE Heartbeat, Stale-Timeout
- Deliverable: Upload → SSE Progress → Completed mit Features

**Iteration 2.5 — Similarity Search + Late Fusion**
- pgvector Insert (Learned + Handcrafted + Metadata)
- `find_similar_songs()` SQL-Funktion
- Late Fusion in Python (80/20 Learned/Handcrafted)
- Normalisierungs-Stats aus config-Tabelle laden, Startup-Validierung
- Deliverable: Song einfügen → Similar Songs zurückbekommen

**Iteration 2.6 — Temp-Cleanup + Error Handling**
- Periodischer Cleanup alle 15 Min (primär), atexit (Best-Effort)
- Error Sanitization: kein stderr/Traceback in Responses
- Deliverable: Cleanup läuft, Fehler-Responses sauber

---

### Phase 3: Daten-Seeding

> **Ziel**: 25K echte Songs in der DB.
> **Kontext nötig**: Nur dieser Abschnitt + "Daten-Strategie".

**Iteration 3.1 — FMA Batch-Processing Script**
- `seed_fma.py`: FMA-medium (25K) Tracks laden, MusiCNN + Handcrafted berechnen
- Resume-fähig (Checkpoint pro 1000 Tracks)
- Deliverable: Script lokal getestet mit FMA-small Subset (100 Tracks)

**Iteration 3.2 — Seeding auf Cloud ausführen**
- EC2 Spot Instance, FMA-medium downloaden (~22 GB)
- Batch-Job laufen lassen (~1 Tag)
- Normalisierungs-Stats berechnen → config-Tabelle
- Deliverable: 25K Songs in Supabase, Stats in config

**Iteration 3.3 — Metadata-Qualität sichern**
- Songs ohne Title/Artist: `metadata_status: 'failed'` → aus Suche ausblenden
- Optional: MusicBrainz MBID-Matching (best-effort Fuzzy)
- Deliverable: Saubere Suchergebnisse, keine "Unknown"-Einträge

---

### Phase 4: Song-Identifikation

> **Ziel**: Upload → Song erkennen → Metadata anreichern.
> **Kontext nötig**: Nur dieser Abschnitt + "AcoustID Rate-Limiting Queue".

**Iteration 4.1 — AcoustID Integration**
- Chromaprint `fpcalc` im Docker-Image
- AcoustID Rate-Limiting Queue (2 req/s)
- TDD: Queue-Rate-Limiting, Fallback bei API-Fehler
- Deliverable: Audio → Fingerprint → MBID (oder None)

**Iteration 4.2 — MusicBrainz + Fuzzy-Suche**
- MusicBrainz API Client (1 req/s Rate-Limit)
- Fallback-Kette: MBID-Lookup → Fuzzy pg_trgm → "Unknown"
- Deliverable: Erkannter Song bekommt Metadata, unerkannter wird trotzdem analysiert

**Iteration 4.3 — YouTube URL-Input**
- oEmbed API → Title + Author
- Titel-Heuristik ("Artist - Song Title")
- DB Fuzzy-Match
- Deliverable: YouTube-URL → Song-Match oder Upload-CTA

---

### Phase 5: Frontend — Upload & Progress

> **Ziel**: User kann Datei hochladen und sieht Live-Progress.
> **Kontext nötig**: Nur dieser Abschnitt. Backend-API ist bereits fertig.

**Iteration 5.1 — Upload-Zone**
- Drag & Drop, Client-seitige Validierung (50 MB, Audio-MIME)
- Upload direkt an Python API
- TDD: Rejects >50 MB, rejects non-audio
- Deliverable: Datei hochladen → Job-ID zurück

**Iteration 5.2 — SSE Progress + Cold-Start UX**
- SSE-Client mit Reconnect + Heartbeat-Detection
- Cold-Start: "Wir wachen gerade auf..." (kalibriert auf 30-90s)
- Progress-Bar startet nach Modell-Loading
- TDD: SSE Updates empfangen, Reconnect bei Drop
- Deliverable: Upload → Live-Progress → "Completed"

**Iteration 5.3 — Opt-in Dialog + YouTube-Input**
- DSGVO Opt-in: "Merkmale speichern?", Default: Nein
- YouTube-URL Eingabefeld
- Deliverable: Beide Inputs funktional

---

### Phase 6: Frontend — Results

> **Ziel**: Ergebnisse schön darstellen mit Feedback-Möglichkeit.
> **Kontext nötig**: Nur dieser Abschnitt.

**Iteration 6.1 — Song-Cards + Results Page**
- Song-Card: Titel, Artist, Similarity %, BPM, Key, Spotify/YouTube Search-Links
- Staggered Reveal (Framer Motion)
- Responsive Design
- Deliverable: Ergebnisse werden angezeigt

**Iteration 6.2 — Feature-Radar-Chart**
- 5 Kategorien: Klangfarbe, Harmonie, Tempo, Helligkeit, Intensität
- Query-Song vs. Result-Song Overlay
- Deliverable: Radar-Chart pro Ergebnis sichtbar

**Iteration 6.3 — Filter + Feedback + Katalog-Transparenz**
- BPM-Range Filter, Similarity-Threshold
- Thumbs Up/Down (transparent: "für zukünftige Verbesserungen")
- DB-Song-Count anzeigen, niedrige Scores erklären
- Deliverable: Filter funktional, Feedback wird gespeichert

---

### Phase 7: Polish & Deploy

> **Ziel**: Production-ready.
> **Kontext nötig**: Nur dieser Abschnitt + "Sicherheit" + "Lizenz-Übersicht".

**Iteration 7.1 — Error States + Loading**
- Alle Fehler-Zustände abdecken (Timeout, 503, korrupte Datei, kein Match)
- Retry-Option bei Timeout (180s)
- Deliverable: Kein unbehandelter Fehler-Zustand

**Iteration 7.2 — Privacy + Legal + SEO**
- Privacy Policy Page
- AGPL-Compliance: Source-Code Link im Footer
- FMA Attribution (CC-BY)
- OG Tags, Metadata
- Deliverable: Legal-Pages live

**Iteration 7.3 — E2E Tests**
- Playwright: Full Flow (Upload → Progress → Results)
- Canary Query im Health-Check
- Deliverable: E2E grün

**Iteration 7.4 — Final Deploy + Monitoring**
- Railway Memory Limit verifizieren
- UptimeRobot Monitors bestätigen (Railway + Supabase)
- Sentry Alerts konfigurieren
- Rollback-Plan dokumentieren
- Deliverable: Alles live, Monitoring aktiv

---

## Evaluation

### FMA-Benchmark (Phase 0 Gate)

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
# Random Baseline:     P@10 ≈ 12.5% (1/8 Genres)
# Handcrafted 44-dim:  P@10 ≈ 25-35%
# MusiCNN 200-dim:     P@10 ≈ 50-65%
# Late Fusion:         P@10 ≈ 55-70%
```

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

def test_rhythm_similarity_bounds():
    a = np.array([120.0, 0.05, 0.8, 0.7])  # BPM, ZCR, Loudness, Danceability
    b = np.array([130.0, 0.03, 0.6, 0.5])
    sim = rhythm_similarity(a, b)
    assert 0.0 <= sim <= 1.0

def test_weighted_handcrafted_bounds():
    a = np.random.randn(44)
    b = np.random.randn(44)
    sim = weighted_handcrafted(a, b)
    assert -1.0 <= sim <= 1.0

# Validierung
def test_mime_validation_rejects_non_audio():
    assert not validate_mime_type("tests/fixtures/not_audio.txt")
    assert not validate_mime_type("tests/fixtures/fake.mp3")
    assert validate_mime_type("tests/fixtures/sine_440hz.wav")

def test_duration_validation_rejects_long_files():
    """Audio > 15 Minuten wird abgelehnt."""
    assert not validate_duration("tests/fixtures/20min_silence.wav")
    assert validate_duration("tests/fixtures/sine_440hz.wav")

def test_corrupt_file_handled_gracefully():
    with pytest.raises(FeatureExtractionError):
        extract_features_safe("tests/fixtures/corrupt.mp3")

# Load Control
@pytest.mark.skipif(platform.system() != "Linux", reason="RLIMIT_AS only works on Linux")
def test_subprocess_memory_limit():
    """Subprocess darf nicht mehr als 2 GB RAM nutzen."""
    with pytest.raises(FeatureExtractionError):
        extract_features_safe("tests/fixtures/huge_synthetic.wav")

def test_upload_semaphore_returns_503():
    """4. gleichzeitiger Upload → 503."""
    ...

def test_acoustid_queue_rate_limiting():
    """3. concurrent AcoustID Request wartet statt 429."""
    ...

def test_sse_heartbeat_sent():
    """SSE sendet Heartbeat alle 15s."""
    ...

def test_sse_stale_connection_closed():
    """SSE Connection nach 300s Inaktivität geschlossen."""
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
test('SSE detects missing heartbeat after 20s', () => { ... })
test('results display song cards with search links', () => { ... })
test('feature radar chart renders 5 categories', () => { ... })
test('feedback buttons send rating to API', () => { ... })
test('opt-in dialog defaults to No', () => { ... })
test('cold-start message shown on 503/timeout', () => { ... })
test('low similarity results show catalog growth message', () => { ... })
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

## Risiken & Mitigationen

| Risiko | Impact | Mitigation |
|---|---|---|
| MusiCNN P@10 < 40% auf FMA | **Kritisch** | Phase 0 Gate. Fallback: EffNet-Discogs. Wenn auch schlecht → Projekt re-evaluieren |
| Essentia C++ Segfault bei korrupten Files | Hoch | Subprocess + RLIMIT_AS (Linux) + MIME-Check + ffprobe + Dauer-Check |
| Concurrent Load sprengt Railway | Hoch | concurrency=1, Upload-Semaphore(3), SSE-Limiter(50) + Heartbeat + Stale-Timeout |
| Railway OOM-Kill-Loop | Hoch | Restart "On Failure", RLIMIT_AS (Linux), concurrency=1 |
| TF Cold-Start 30-90s nach Sleep | Hoch | UX kalibriert auf echte Zeiten, Progress erst nach Modell-Loading |
| SSE Zombie-Connections | Hoch | Heartbeat alle 15s + Stale-Timeout 300s |
| AcoustID 429 bei concurrent Requests | Mittel | Eigene asyncio Queue (2 req/s), Fallback auf "Unknown" |
| FMA-Katalog zu nischig für Mainstream | Mittel | Transparent kommunizieren, User-Uploads als Wachstum |
| Railway Sleep + Supabase Pause Konflikt | Mittel | 2 UptimeRobot Monitors (Railway + Supabase Direct) |
| AcoustID non-commercial bindet Projekt | Mittel | Bewusste Entscheidung, dokumentiert. Optional: eigener Fingerprinting-Service langfristig |
| Analyse dauert >60s | Mittel | Procrastinate Queue + SSE Progress + 180s Timeout |
| Metadata-Lücken (FMA hat nicht immer Artist/Title) | Mittel | MusicBrainz Enrichment, `metadata_status: 'failed'` ausblenden |
| UptimeRobot-Ausfall → Supabase Pause | Niedrig | Nach 7 Tagen manuell reaktivieren, Sentry Alert |
| stderr-Leak in Error-Responses | Niedrig | Generische Fehler, Details nur in Server-Log/Sentry |
| DSGVO Opt-in | Niedrig | Expliziter Dialog, Default: Nein, "unsere Interpretation" Disclaimer |
| Feedback-Loop ohne Effekt auf Similarity | Niedrig | Transparent kommunizieren: "für zukünftige Verbesserungen" |
| RLIMIT_AS auf macOS wirkungslos | Niedrig | Tests nur auf Linux (CI), macOS-Entwicklung hat timeout=180 als Fallback |
| Disk-Exhaustion durch große unkomprimierte Audio | Niedrig | Dauer-Check (max 15 Min ≈ max 300 MB unkomprimiert) |
| AGPL Section 13 Compliance | Niedrig | Code auf GitHub öffentlich, Link im Footer |

---

## Sicherheit

### Upload-Sicherheit
1. **MIME-Type vor Disk-Write** (python-magic): Blockt PHP/EXE/etc. mit Audio-Extension
2. **File-Size Header-Check**: Max 50 MB, bevor Stream gelesen wird
3. **ffprobe Validierung**: Format-Integrität + **Dauer ≤ 15 Minuten** nach Disk-Write
4. **Temp-Directory Isolation**: Eigenes tmpdir, periodischer Cleanup (alle 15 Min), atexit als Best-Effort
5. **Subprocess RAM-Cap**: `RLIMIT_AS = 2 GB` auf Linux (Railway), `timeout=180` als universeller Fallback

### API-Sicherheit
1. **CORS**: Explizite Origin-Whitelist (Vercel-Domain), nicht `*`
2. **Rate-Limiting**: 5 req/min/IP auf `/analyze` (slowapi)
3. **Concurrent-Limit**: Semaphore(3) für Uploads, Semaphore(50) für SSE
4. **SSE-Schutz**: Heartbeat alle 15s, Stale-Timeout 300s — verhindert Zombie-Connections
5. **AcoustID Rate-Limiting**: Eigene Queue (2 req/s), verhindert 429 bei concurrent Uploads
6. **Error Sanitization**: Kein stderr/Traceback in API-Responses
7. **SQL**: Parametrisierte Queries, kein String-Concat

### DSGVO / Privacy
- **Kein User-Account** — anonyme Nutzung
- **Audio sofort gelöscht** nach Analyse (Temp-Dir + Cleanup alle 15 Min)
- **Feature-Opt-in**: Expliziter Dialog vor Speicherung ("unsere Interpretation — keine Rechtsberatung")
- **Kein IP-Logging** über Rate-Limiting hinaus
- **Privacy Policy**: Klar formuliert, keine juristischen Garantien

---

## Lizenz-Übersicht

| Komponente | Lizenz | Kosten | Hinweis |
|---|---|---|---|
| Essentia | AGPL v3 | Free | Beattrack ist Open Source → AGPL Section 13: Code muss öffentlich sein |
| essentia-tensorflow | AGPL v3 | Free | MusiCNN-Modelle. Alle Modifikationen müssen veröffentlicht werden |
| MusiCNN Modell | AGPL v3 | Free | 18 MB, via Essentia-Repo |
| FMA Dataset | CC-BY | Free | Attribution im README/Footer |
| AcoustID API | Free (non-commercial) | Free | **Bewusste Entscheidung**: Beattrack bleibt non-commercial. Kein Ads, kein Premium, keine Monetarisierung solange AcoustID genutzt wird |
| MusicBrainz API | Free | Free | User-Agent Pflicht |
| AcousticBrainz Data | CC0 | Free | Nur für Metadata, nicht für Vektoren |
| Supabase | Free Tier | Free | 500 MB DB |
| Vercel | Free Tier | Free | |
| Railway | Hobby | ~$7-15/mo | Abhängig von Sleep-Konfiguration |
| Sentry | Free Tier | Free | 5K Events/Mo |
| UptimeRobot | Free Tier | Free | 50 Monitors |

**AGPL-Compliance-Pflicht**: Da Essentia und essentia-tensorflow AGPL v3 sind und als Network-Service betrieben werden (Section 13), muss der vollständige Quellcode inklusive aller Modifikationen öffentlich zugänglich sein. Link im Footer: "Source Code on GitHub".

---

## Changelog v2.0 → v3.0

| Bereich | v2.0 | v3.0 | Grund |
|---|---|---|---|
| **Proxy-Modell** | AcousticBrainz→MusiCNN MLP (Option A) | **Gestrichen** | Informationstheoretisch nicht fundiert (44-dim kann keine 200-dim Infos erzeugen) |
| **Seed-DB** | 300K (FMA + AcousticBrainz + Proxy) | **25K-100K (nur FMA, echte Embeddings)** | Qualität > Quantität. Kein Mixed-Quality-Katalog |
| **Spotify URLs** | URL-Slug parsen | **Entfernt** | Track-Name nicht in URL, API-Key nötig |
| **RLIMIT_AS** | Implizit überall wirksam | **Nur Linux (Railway)**, macOS-Skip in Tests | macOS ignoriert RLIMIT_AS seit 10.15 |
| **SSE** | Kein Heartbeat/Timeout | **Heartbeat 15s + Stale-Timeout 300s** | Zombie-Connections blockierten Semaphore-Slots |
| **AcoustID** | Direkte API-Calls | **Eigene asyncio Queue (2 req/s)** | 3 concurrent Uploads → 429 bei 3 req/s Limit |
| **rhythm_similarity** | Undefiniert (in Formel aber nicht implementiert) | **Definiert**: BPM-Distanz + Cosine über ZCR/Loudness/Dance | Missing Piece behoben |
| **Dauer-Check** | Fehlte | **ffprobe: max 15 Min** | 50 MB FLAC → mehrere GB unkomprimiert möglich |
| **Cold-Start** | 15-30s geschätzt | **30-90s (TF-Loading)** realistisch | UX-Kalibrierung auf echte Zeiten |
| **Keepalive** | 1 UptimeRobot Monitor | **2 Monitors** (Railway + Supabase Direct) | Railway Sleep verhindert DB-Ping |
| **Temp-Cleanup** | atexit primär, Cron sekundär | **Cron primär (15 Min), atexit Best-Effort** | SIGKILL (OOM) ruft atexit nicht auf |
| **Feedback** | Implizit "verbessert Ergebnisse" | **Transparent: aktuell nur gesammelt** | Ehrliche Kommunikation |
| **FMA-Katalog** | Problem nicht adressiert | **Transparent kommuniziert, Upload als Wachstum** | 90% Indie statt Mainstream |
| **AcoustID non-commercial** | Nebenbei erwähnt | **Bewusste Entscheidung, dokumentiert** | Projekt permanent non-commercial |
| **AGPL Section 13** | Nicht adressiert | **Compliance-Pflicht dokumentiert, Link im Footer** | Network-Service → Code muss öffentlich sein |
| **AcousticBrainz Vektoren** | Für Similarity geplant | **Nur für skalare Metadata** | Versionsinkompatibilität, kein Mischen |
