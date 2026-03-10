# Beattrack - Sonically Similar Song Finder

## Context

Plattform-Radios (Spotify, YouTube, etc.) empfehlen Songs mit einem Mix aus kollaborativem Filtering und Audio-Features (Spotify nutzt seit 2014 Echonest-DNA). Beattrack verfolgt einen **transparenten, Open-Source-Ansatz**: Audio-Features (Timbre, Rhythmus, Harmonie, Spektral-Eigenschaften) werden direkt analysiert und dem User erklärt — keine Black-Box, kein Engagement-Optimierung, kein Lock-in.

**Differenzierung**: Nicht "besser als Spotify", sondern **anders** — transparent, erklärbar, unabhängig. Der User sieht *warum* Songs ähnlich klingen (Feature-Radar-Chart mit 5 menschlichen Kategorien), nicht nur *dass* sie es tun. Es gibt aktuell kein gutes Open-Source-Tool für "Audio hochladen → ähnliche Songs finden" — Cyanite.ai macht das kommerziell/B2B, Musly ist seit 2014 tot, beets-xtractor taggt nur Features ohne Similarity Search.

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
│  Python FastAPI      │  ← Essentia MusicExtractor (in Subprocess, Segfault-Schutz)
│  (Railway Hobby)     │  ← AcoustID Song-Identifikation (Chromaprint serverseitig)
│                      │  ← Postgres Job-Queue (Procrastinate, kein Redis nötig)
│                      │  ← Rate-Limiting (slowapi, 10 req/min/IP auf /analyze)
│                      │  ← Sentry Error Tracking
└────────┬────────────┘
         │ Vector Query
         ▼
┌─────────────────────┐
│  Supabase            │  ← pgvector Cosine Similarity (HNSW)
│  (Postgres + Storage)│  ← Song-Metadata + Feature-Vektoren (raw + normalized)
│                      │  ← Job-Queue-Tabelle (Procrastinate)
└─────────────────────┘
```

### Zwei Input-Wege

1. **Datei-Upload**: User lädt MP3/WAV/FLAC hoch (max 50 MB) → Upload direkt an Python API (nicht über Next.js BFF) → Postgres Job-Queue → Essentia `MusicExtractor` extrahiert Features (in isoliertem Subprocess) → pgvector Similarity Search → Ergebnis via SSE
2. **URL (YouTube/Spotify/SoundCloud)**: Metadaten extrahieren → Song in DB suchen → wenn gefunden: Features aus DB nutzen → wenn nicht gefunden: User auffordern, Audio-Datei hochzuladen

**URL-Input lädt kein Audio herunter** — nur öffentliche Metadaten.

### Async-Analyse-Flow (kritisch)

Feature-Extraktion mit Essentia dauert **10-60 Sekunden** je nach Track-Länge und Server-Last. Synchrone HTTP-Requests brechen bei Vercel (30s Timeout). Deshalb:

```
POST /analyze (File Upload)
  → Validiert Audio mit ffprobe (Format, Integrität)
  → Speichert Datei temporär
  → Erstellt Job in Postgres Queue (Procrastinate)
  → Returns: { job_id: "abc-123", status: "processing" }

GET /analyze/{job_id}/stream  (SSE)
  → Server-Sent Events: { status: "processing" | "completed" | "failed", progress?: 0.0-1.0 }
  → Bei "completed": enthält Result-Daten inline

GET /analyze/{job_id}/results  (Fallback)
  → Returns: { song: {...}, similar: [...] }  (wenn completed)
```

Frontend verbindet sich per SSE auf `/stream` und zeigt Progress-Animation. Kein Polling nötig — Server pushed Updates in Echtzeit. FastAPI 0.135.0+ hat natives SSE via `fastapi.sse.EventSourceResponse`.

**Fallback**: Wenn SSE-Connection abbricht, pollt Frontend `/results` mit exponential Backoff.

---

## Tech Stack

### Frontend
- **Next.js 15** (App Router) — deployed auf Vercel
- **TailwindCSS v4** — Styling
- **Framer Motion** — staggered Reveal der Results, Progress-Animation während Analyse
- **Font**: Space Grotesk (geometric, modern, music-passend)

### Backend
- **Python 3.12 + FastAPI 0.135.0+** — API Server mit nativem SSE Support
- **Essentia** (AGPL v3, `pip install essentia`) — Audio Feature-Extraktion via `MusicExtractor`
  - Gleiche Algorithmen wie AcousticBrainz → Features im selben Space
  - ~2x schneller als librosa (C++ Core mit FFTW)
  - Pip-Wheel ist self-contained (keine System-Dependencies nötig)
  - **Docker-Image wird ~1.5 GB** (Python + Essentia + numpy/scipy) — berücksichtigt bei Deployment-Wahl
  - **Essentia läuft in isoliertem Subprocess** (`subprocess.run()` mit Timeout) — C++ Segfaults bei korrupten Files (GitHub Issue #847) crashen sonst den Worker-Prozess
- **Procrastinate** (MIT, v3.7.2, aktiv maintained) — Postgres-basierte Job-Queue für async Feature-Extraktion
  - Nutzt `LISTEN/NOTIFY` + `FOR UPDATE SKIP LOCKED` — echte Queue-Semantik
  - **Kein Redis nötig** — eliminiert Upstash als externe Abhängigkeit
  - Job + DB-Write in einer ACID-Transaktion möglich
- **uv** — Python Package Manager
- **Pydantic v2** — Request/Response Validation
- **slowapi** — IP-basiertes Rate-Limiting (10 req/min unauthentifiziert auf `/analyze`)
- **Sentry** (Free Tier, 5K Events/Monat) — Error Tracking + Exception Alerting
- **Chromaprint** (`pyacoustid` + `fpcalc` binary im Docker-Image) — AcoustID Fingerprinting serverseitig

### Audio-Validierung (vor Essentia)
- **ffprobe** — Vorab-Validierung von Audio-Dateien (Format, Integrität, Codec-Check)
- Korrupte/unsupported Files werden abgefangen bevor sie Essentia erreichen
- Essentia-Call läuft in `subprocess.run(timeout=120)` — Segfault killt nur den Child-Prozess

### Datenbank
- **Supabase** (Free Tier: 500MB DB, 1GB Storage)
- **pgvector** Extension — HNSW Index für Cosine Similarity Search
- **Speicher-Budget**:
  - 300K Songs × 44 floats × 4 bytes = ~50 MB (normalized vectors)
  - 300K Songs × 44 floats × 4 bytes = ~50 MB (raw vectors, für Re-Normalisierung)
  - Metadata (Titel, Artist, Album, MBID) × 300K = ~90 MB
  - HNSW Index = ~70-100 MB
  - Procrastinate Job-Tabellen = ~10 MB
  - **Total: ~280-350 MB** — passt in Free Tier (500 MB)
- **Kein Audio-Storage auf Supabase** — User-Uploads werden nur temporär für Analyse gespeichert, dann gelöscht
- **Supabase Free Tier pausiert nach 7 Tagen Inaktivität** — Cron-Ping gegen DB (`SELECT 1`) alle 3 Tage nötig

### Song-Identifikation
- **AcoustID** (free, non-commercial, 3 req/s) — Fingerprint → MusicBrainz Recording ID
  - Nur für User-Uploads, NICHT für ETL
  - Chromaprint + `fpcalc` binary im Docker-Image (serverseitig)
  - **Fallback wenn AcoustID keinen Match findet**: Analyse trotzdem durchführen, Song als "Unknown" mit User-Metadata speichern
- **MusicBrainz API** (free, 1 req/s) — Metadata (Titel, Artist, Album)
  - **User-Agent Pflicht**: `Beattrack/1.0 (https://github.com/user/beattrack)` — ohne wird man nach ~100 Requests geblockt

### Streaming-Links
- **Keine direkten URLs** von Spotify/YouTube in der DB
- Stattdessen **Search-Links**: `https://open.spotify.com/search/{title} {artist}` / `https://www.youtube.com/results?search_query={title}+{artist}`
- Kein API-Key nötig, keine ToS-Verletzung
- MusicBrainz hat Spotify-IDs als Relations, aber Coverage nur ~10-25% — lohnt sich nicht als primäre Strategie

### Testing
- **Vitest** — Frontend Unit Tests
- **pytest** — Backend Unit/Integration Tests
- **Playwright** — E2E Tests
- **standardized-audio-context-mock** — Web Audio API Mocking
- **Claude in Chrome / Playwright MCP** — visuelle Frontend-Verifikation

### Deployment
- **Vercel** — Frontend (free)
- **Railway Hobby Plan ($5/Monat)** — Python Backend
  - Railway Free Tier (512 MB RAM) reicht **nicht** für Essentia — Hobby Plan ist Pflicht
  - Hobby Plan: bis 48 GB RAM, $5/Monat Basis + $5 Usage Credit
  - Docker-Image ~1.5 GB, Cold Start ~15-30s (akzeptabel mit Job-Queue)
  - Multi-stage Dockerfile um Image auf <800 MB zu bringen (reduziert Cold Start)
  - `/health` Endpoint + Vercel Cron Ping alle 5 Min → warm halten
- **Supabase** — Datenbank + Job-Queue (free)
  - Cron-Ping alle 3 Tage gegen DB → verhindert Auto-Pause
- **GitHub Actions** — CI/CD

### Kosten-Realität

| Service | Plan | Kosten/Monat |
|---|---|---|
| Vercel | Free | $0 |
| Railway | Hobby | ~$5 |
| Supabase | Free | $0 |
| Sentry | Free | $0 |
| AcoustID | Free (non-commercial) | $0 |
| **Total** | | **~$5/Monat** |

Kein $0-Projekt — Essentia braucht 1 GB+ RAM, Railway Free Tier reicht nicht.

---

## Daten-Strategie

### Seed: AcousticBrainz Dataset (free, open)
- 29M Tracks mit vorberechneten Essentia-Features (MFCCs, Chroma, Spektral, Rhythmus)
- **Eingefroren seit 2022** — kein Post-2022-Katalog, aber deckt breiten historischen Katalog ab
- Jeder Track hat eine MusicBrainz Recording ID → Metadata verfügbar
- **Dump-Größen**: Lowlevel = 589 GB, Highlevel = 39 GB (zstandard-komprimiert). Sample-Dump = 2 GB (100K Items)
- **Downloads aktuell noch verfügbar** — aber kein permanentes Hosting-Versprechen von MetaBrainz. **Dump jetzt archivieren** (eigene Kopie sichern)
- **Bekannte Qualitätsprobleme**: ~20-30% fehlende Metadata, mögliche MBID-Duplikate, Genre-Bias (Pop/Rock überrepräsentiert, nicht Electronic wie manchmal behauptet)
- AcoustID wird NICHT für ETL gebraucht (MBIDs sind bereits im Dataset)

### Metadata im AcousticBrainz-Dump

AcousticBrainz enthält **bereits Metadata** in `metadata.tags`:
- `artist`, `title`, `album`, `date`, `genre`, `label`
- Aber: aus ID3-Tags der Submitter extrahiert — nicht normalisiert, inkonsistent, teils leer
- **MusicBrainz API nur noch für Lücken** (~20-30% der Tracks) — nicht für alle 300K
- Das reduziert API-Calls von 300K auf ~60-90K → ~17-25 Stunden statt ~83 Stunden

### Phase 0: Feature-Validierung (VOR dem großen ETL)

**Bevor 300K Songs geladen werden, erst mit 1.000 Tracks validieren:**

1. 1.000 Tracks aus AcousticBrainz extrahieren via **stratified Sampling** (s.u.)
2. 44-dim Vektoren berechnen + normalisieren
3. **Mindestens 50 Query-Songs** mit bekannten "ähnlich klingenden" Tracks definieren:
   - Covers, Remixes, gleicher Produzent (einfache Positive)
   - Songs die Hörer als ähnlich wahrnehmen, aber nicht offensichtlich verwandt (harte Positive)
   - Zufällige Paare als Negative
4. **Präzisions-Metrik**: Top-10 Ergebnisse pro Query — wie viele davon sind plausibel ähnlich?
5. **Baseline-Vergleich**: Random Similarity Score als untere Schranke
6. Existierende Benchmarks nutzen falls verfügbar (Covers80, Second Hand Songs)
7. **Go/No-Go Entscheidung**: Wenn Ergebnisse nicht brauchbar → Feature-Gewichtung überarbeiten

### Stratified Sampling (statt Hash-Prefix)

MusicBrainz Recording IDs sind UUID v4 (kryptographisch zufällig) — Hash-Prefix-Sampling ist **nicht genre-korreliert** und bringt keine Diversität.

**Strategie**: Highlevel-Dump (39 GB, separat downloadbar) enthält Genre-Classifier-Daten:
- `highlevel.genre_dortmund.value` — 9 Genres (alternative, blues, electronic, folkcountry, funksoulrnb, jazz, pop, raphiphop, rock)
- Accuracy ~60% — reicht für grobes stratified Sampling
- **Ziel-Verteilung**: ~11% pro Genre (gleichverteilt), mit Toleranz ±5%
- Zuerst Highlevel-Dump scannen → MBID-Liste pro Genre → dann Lowlevel-Features für ausgewählte MBIDs extrahieren

### ETL Pipeline

**Realistische Aufwandsschätzung**: Mehrtägiger Batch-Job. Braucht Maschine mit ~100 GB freiem Speicher (nicht Laptop — Cloud-Instanz empfohlen für den Download).

1. AcousticBrainz Highlevel-Dump downloaden (39 GB) → Genre-Tags pro MBID extrahieren → stratified MBID-Liste erstellen
2. AcousticBrainz Lowlevel-Dump downloaden (589 GB, zstandard-komprimiert)
3. Streaming-ETL-Script mit **Resume-Fähigkeit** und **Error-Handling**:
   - Zstandard-Archive stream-parsen
   - **Stratified Sampling**: Nur MBIDs aus der vorberechneten Genre-Liste
   - Pro Track extrahieren:
     - `lowlevel.mfcc.mean` (13 dims) + `lowlevel.mfcc.var` (13 dims)
     - `tonal.hpcp.mean` (36 dims → auf 12 reduzieren, **korrekte Bin-Reduktion**, s.u.)
     - `lowlevel.spectral_centroid.mean` (1)
     - `lowlevel.spectral_rolloff.mean` (1)
     - `rhythm.bpm` (1)
     - `lowlevel.zerocrossingrate.mean` (1)
     - `lowlevel.average_loudness` (1)
     - `rhythm.danceability` (1)
     - **Total: ~44 Dimensionen**
   - **Metadata aus `metadata.tags` extrahieren** (Artist, Title, Album) — direkt in DB speichern
   - Tracks ohne `metadata.tags` als `metadata_status: 'pending'` markieren → MusicBrainz API nur für diese
   - **Checkpoint alle 10K Records** (Resume bei Abbruch)
   - Records mit fehlenden Features oder NaN-Werten überspringen
4. Nach 300K Records stoppen
5. **Globale Normalisierung**: Mean + Std pro Dimension über gesamten Seed-Corpus berechnen
6. **Zwei Vektoren speichern**: Raw-Vektor + Normalized-Vektor (ermöglicht Re-Normalisierung)
7. In Supabase pgvector laden (mit MusicBrainz Recording ID als Key)
8. MusicBrainz Metadata-Enrichment nur für `metadata_status: 'pending'` Tracks:
   - **1 req/s Rate-Limit** → bei ~60-90K Tracks = ~17-25 Stunden (statt 83h für alle)
   - Registrierter User-Agent: `Beattrack/1.0 (https://github.com/user/beattrack)`
   - Retry-Logic mit exponential Backoff
   - Resume-Fähigkeit (Checkpoint pro Batch von 1.000)
   - Auf Cloud-Instanz mit stabiler Verbindung ausführen, nicht lokal

### Normalisierung (kritisch!)

Z-Score Normalisierung muss **global** sein, nicht per-Vektor:
```python
# Bei ETL: globale Stats berechnen und speichern
global_mean = np.mean(all_vectors, axis=0)  # shape: (44,)
global_std = np.std(all_vectors, axis=0)    # shape: (44,)
save_json({"mean": global_mean, "std": global_std}, "normalization_stats.json")

# Bei Runtime (User-Upload): gleiche globale Stats anwenden
normalized = (raw_vector - global_mean) / global_std
```

### MFCC-Dominanz-Problem

Von 44 Dimensionen sind 26 MFCC-bezogen (59%). Cosine Similarity wird faktisch fast nur durch MFCCs bestimmt — BPM, Spectral Features mit je 1 Dimension sind dagegen nahezu irrelevant.

**Mitigation (Phase 0 evaluieren)**: Gewichtete Similarity statt reines Cosine über den Gesamt-Vektor:
```python
# Feature-Gruppen separat vergleichen und gewichten
similarity = (
    0.30 * cosine(mfcc_mean_a, mfcc_mean_b) +     # Klangfarbe (13 dims)
    0.10 * cosine(mfcc_std_a, mfcc_std_b) +        # Klangfarbe-Varianz (13 dims)
    0.25 * cosine(hpcp_a, hpcp_b) +                # Harmonie (12 dims)
    0.20 * cosine(spectral_a, spectral_b) +         # Helligkeit/Wärme (3 dims)
    0.15 * rhythm_similarity(bpm_a, bpm_b,          # Tempo/Groove (2 dims)
                             dance_a, dance_b)
)
```

**Alternative**: Separate Embedding-Spalten pro Feature-Gruppe in pgvector und Weighted Sum auf DB-Ebene. Aufwändiger, aber besser. In Phase 0 mit beiden Ansätzen experimentieren.

### Normalisierungs-Drift und Re-Normalisierung

**Problem**: Wenn User-Uploads die Verteilung signifikant verändern, werden die globalen Stats ungenau.

**Lösung**:
- **Raw-Vektoren werden immer mitgespeichert** (raw_embedding VECTOR(44) in songs-Tabelle)
- Normalisierungs-Stats werden **nicht** automatisch angepasst — die Seed-Stats sind die Baseline
- Erst bei >50K User-Uploads: neue Stats berechnen und alle Vektoren re-normalisieren (Batch-Job)
- `normalization_stats.json` wird **nicht im Repo committed**, sondern bei Deploy von Supabase geladen (DB-Tabelle `config`)
- **Startup-Validierung**: API prüft beim Start ob Stats geladen werden können, sonst Fehler statt Silent Fail

### Wachstum
- User-Uploads: Features werden nach Analyse in DB gespeichert (wenn User zustimmt — opt-in)
- Community-getrieben: DB wächst mit jeder Nutzung
- **Realistisches Ziel**: 300K Seed + organisches Wachstum. Bei 1% Katalog-Abdeckung werden viele Uploads "Unknown" sein — das ist OK, da die Feature-basierte Similarity trotzdem funktioniert
- **"Unbekannter Song"-Flow** als Feature positionieren, nicht als Fallback: "Wir haben Ihren Song nicht erkannt, aber wir suchen trotzdem nach ähnlich klingenden Songs"

### Datenschutz / DSGVO

- **Kein User-Account nötig** — anonyme Nutzung, kein Login
- Audio-Files werden nach Analyse **sofort gelöscht** — kein Audio-Storage
- Feature-Vektoren (44 Floats) ohne User-Link sind wahrscheinlich anonymisierte Daten (GDPR Recital 26)
- Wenn Feature-Vektoren mit Opt-in gespeichert werden: kein PII, kein Session-Link → außerhalb GDPR-Scope
- Railway = US-Server, aber ohne personenbezogene Daten ist das unproblematisch
- **Privacy Policy** auf der Website einbinden: "Keine Audio-Dateien gespeichert. Berechnete mathematische Merkmale (Feature-Vektoren) sind keine personenbezogenen Daten."

---

## Feature-Extraktion Pipeline (Essentia)

```python
import subprocess
import json
import numpy as np

def extract_features_safe(audio_path: str, timeout: int = 120) -> np.ndarray:
    """Essentia in isoliertem Subprocess ausführen — Segfault-Schutz."""
    result = subprocess.run(
        ["python", "-m", "app.workers.extract", audio_path],
        capture_output=True, timeout=timeout, text=True
    )
    if result.returncode != 0:
        raise FeatureExtractionError(f"Essentia failed: {result.stderr[:500]}")
    return np.array(json.loads(result.stdout))


# Im Worker-Subprocess (app/workers/extract.py):
import essentia.standard as es
import numpy as np
import sys, json

def extract_features(audio_path: str) -> np.ndarray:
    features, _ = es.MusicExtractor(
        lowlevelStats=['mean', 'stdev'],
        rhythmStats=['mean', 'stdev'],
        tonalStats=['mean', 'stdev']
    )(audio_path)

    vector = np.concatenate([
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

    return vector  # Raw — Normalisierung separat


def reduce_hpcp(hpcp_36: np.ndarray) -> np.ndarray:
    """Reduce 36-bin HPCP to 12-bin chroma by summing sub-semitone bins.

    Essentia HPCP mit 36 Bins = 3 Sub-Bins pro Halbton innerhalb EINER Oktave.
    Bin-Reihenfolge: [A_sub1, A_sub2, A_sub3, A#_sub1, A#_sub2, A#_sub3, ...]
    NICHT 3 Oktaven × 12 Töne!
    """
    # Korrekt: 12 Halbtöne × 3 Sub-Bins → summiere Sub-Bins pro Halbton
    return hpcp_36.reshape(12, 3).sum(axis=1)
    # FALSCH wäre: hpcp_36.reshape(3, 12).sum(axis=0) — mischt Pitch-Classes!

if __name__ == "__main__":
    vector = extract_features(sys.argv[1])
    print(json.dumps(vector.tolist()))
```

### HPCP Bin-Ordering (verifiziert)

Essentia HPCP mit `size=36` nutzt **3 Sub-Bins pro Halbton** innerhalb einer Oktave (sub-semitone resolution), **nicht** 12 Bins pro Oktave über 3 Oktaven. Essentia-Docs: "HPCP is a k*12 dimensional vector which represents the intensities of the twelve (k==1) semitone pitch classes, or subdivisions of these (k>1)."

- Bin 0-2: A (sub1, sub2, sub3)
- Bin 3-5: A# (sub1, sub2, sub3)
- ...
- Bin 33-35: G# (sub1, sub2, sub3)

Korrekte Reduktion: `hpcp_36.reshape(12, 3).sum(axis=1)` — gruppiert je 3 konsekutive Bins (Sub-Bins desselben Halbtons) und summiert sie.

### Bekannte Limitierungen der 44-dim Features

Diese Feature-Kombination erkennt **gut**:
- Timbre-Ähnlichkeit (MFCCs)
- Harmonische Struktur (HPCP/Chroma)
- Tempo und Rhythmus (BPM, Danceability)
- Spektrale Helligkeit/Dumpfheit (Centroid, Rolloff)

Diese Feature-Kombination erkennt **schlecht**:
- Produktionsstil (analog vs. digital, Kompression)
- Instrumentierung (Gitarren-Rock vs. Synth-Rock bei ähnlichem Timbre)
- Gesangsstil (oft das dominanteste Feature für Hörer)
- Stimmung/Energie (langsame Ballade vs. schneller Pop mit ähnlichen MFCCs)

**MFCC-Dominanz**: 26 von 44 Dims (59%) sind MFCC-bezogen → Cosine Similarity wird primär durch Timbre bestimmt. Gewichtete Similarity (s.o.) ist die primäre Mitigation.

**UX-Mitigation**: Feature-Radar-Chart zeigt dem User *welche* Dimensionen ähnlich sind → Transparenz statt Magie. User kann selbst beurteilen ob die Ähnlichkeit für ihn relevant ist.

---

## Similarity Search (pgvector)

```sql
CREATE EXTENSION vector;
CREATE EXTENSION pg_trgm;  -- für Fuzzy-Text-Suche

CREATE TABLE songs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    musicbrainz_id TEXT UNIQUE,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT,
    duration_sec FLOAT,
    bpm FLOAT,
    musical_key TEXT,
    raw_embedding VECTOR(44) NOT NULL,     -- Roh-Vektor (für Re-Normalisierung)
    embedding VECTOR(44) NOT NULL,          -- Normalisierter Vektor (für Suche)
    source TEXT DEFAULT 'acousticbrainz',   -- 'acousticbrainz' | 'user_upload'
    metadata_status TEXT DEFAULT 'complete', -- 'complete' | 'pending' | 'failed'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Normalisierungs-Config
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
-- INSERT INTO config (key, value) VALUES ('normalization_stats', '{"mean": [...], "std": [...]}');

-- User-Feedback
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_song_id UUID REFERENCES songs(id),
    result_song_id UUID REFERENCES songs(id),
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),  -- -1 = thumbs down, 1 = thumbs up
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW Index (bei 44 dims und 300K Vektoren ist HNSW OK)
CREATE INDEX ON songs USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Fuzzy-Text-Index für URL-Suche
CREATE INDEX ON songs USING gin (title gin_trgm_ops);
CREATE INDEX ON songs USING gin (artist gin_trgm_ops);

CREATE OR REPLACE FUNCTION find_similar_songs(
    query_embedding VECTOR(44),
    match_count INT DEFAULT 20,
    exclude_id UUID DEFAULT NULL
) RETURNS TABLE (id UUID, title TEXT, artist TEXT, album TEXT, bpm FLOAT, similarity FLOAT)
LANGUAGE sql AS $$
    SELECT id, title, artist, album, bpm,
           1 - (embedding <=> query_embedding) AS similarity
    FROM songs
    WHERE id IS DISTINCT FROM exclude_id
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
```

---

## URL-Input: Metadata-Extraktion

### YouTube
- **oEmbed API** gibt nur `title` und `author_name` (Kanal-Name) zurück
- Kanal-Name ist oft nicht der Artist (z.B. "VEVO", Label-Name, "Topic"-Kanäle)
- **Strategie**: `title` parsen mit Heuristik (`"Artist - Song Title"` ist das häufigste Format), `author_name` als Fallback
- DB-Suche: Fuzzy-Match auf `title` + `artist` (pg_trgm Extension)

### Spotify
- Spotify-URLs enthalten Track-ID, aber API braucht OAuth
- **Strategie**: URL parsen → Track-Name aus URL-Slug extrahieren (z.B. `/track/abc123/song-name`) → DB-Suche
- Kein API-Call nötig für Basic-Match

### Fallback
- Wenn kein DB-Match: User klar kommunizieren *warum* und als Feature positionieren:
  - "Dieser Song ist noch nicht in unserer Datenbank — aber du kannst die Audio-Datei hochladen und wir finden trotzdem ähnlich klingende Songs!"
  - Upload-CTA prominent anzeigen

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
│   │   │   └── api/              # BFF Routes (Metadata-Proxy, KEIN File-Upload-Proxy)
│   │   ├── components/
│   │   │   ├── upload-zone.tsx   # Drag & Drop, max 50MB, Format-Validierung
│   │   │   ├── analysis-progress.tsx  # SSE-Connection + Progress-Animation
│   │   │   ├── song-card.tsx     # Title, Artist, Similarity, Search-Links, Feedback
│   │   │   ├── feature-radar.tsx # Radar-Chart: 5 menschliche Kategorien
│   │   │   └── url-input.tsx
│   │   ├── lib/
│   │   │   ├── api.ts            # Backend API client (Upload direkt an Python API)
│   │   │   └── sse.ts            # SSE-Client mit Reconnect-Logic
│   │   ├── __tests__/
│   │   ├── vitest.config.ts
│   │   └── package.json
│   │
│   └── api/                      # Python FastAPI Backend
│       ├── app/
│       │   ├── main.py           # FastAPI app + /health + Startup-Validierung + Sentry
│       │   ├── routes/
│       │   │   ├── analyze.py    # POST /analyze → Job, GET /analyze/{id}/stream (SSE)
│       │   │   ├── search.py     # POST /search (URL → metadata lookup)
│       │   │   └── identify.py   # POST /identify (AcoustID lookup)
│       │   ├── services/
│       │   │   ├── features.py   # Essentia Subprocess-Wrapper + normalization
│       │   │   ├── similarity.py # pgvector query (+ gewichtete Similarity)
│       │   │   ├── acoustid.py   # AcoustID + Chromaprint client
│       │   │   ├── metadata.py   # YouTube oEmbed parser, Spotify URL parser
│       │   │   └── validation.py # ffprobe Audio-Validierung
│       │   ├── workers/
│       │   │   ├── analyze.py    # Procrastinate Worker: Feature-Extraktion Job
│       │   │   └── extract.py    # Essentia-Subprocess (isoliert, crasht nicht den Worker)
│       │   ├── models/
│       │   │   └── schemas.py    # Pydantic models
│       │   └── db/
│       │       └── supabase.py
│       ├── tests/
│       │   ├── fixtures/         # Test audio files (sine waves + corrupt files)
│       │   ├── test_features.py
│       │   ├── test_similarity.py
│       │   ├── test_metadata.py  # YouTube/Spotify URL-Parsing
│       │   ├── test_validation.py # ffprobe Validierung, corrupt file handling
│       │   └── test_api.py
│       ├── pyproject.toml
│       └── Dockerfile            # Multi-stage: Python 3.12 + Essentia + fpcalc (<800 MB)
│
├── scripts/
│   ├── seed_acousticbrainz.py    # Streaming-ETL mit Resume + Checkpoints + stratified Sampling
│   ├── extract_genre_mbids.py    # Highlevel-Dump → Genre-stratified MBID-Liste
│   ├── enrich_metadata.py        # MusicBrainz Metadata nur für Lücken
│   ├── validate_features.py      # Phase-0-Validierung: 50+ Queries, Präzisions-Metrik
│   └── generate_test_audio.py    # Generate sine wave test fixtures
│
├── supabase/
│   └── migrations/
│       ├── 001_init.sql          # Schema + pgvector + pg_trgm setup
│       ├── 002_config.sql        # Config-Tabelle für Normalisierungs-Stats
│       ├── 003_feedback.sql      # Feedback-Tabelle
│       └── 004_procrastinate.sql # Procrastinate Job-Queue Schema
│
├── .github/
│   └── workflows/
│       ├── ci.yml                # Tests + Lint
│       ├── deploy.yml
│       └── keepalive.yml         # Cron: Ping Railway + Supabase alle 3 Tage
│
├── package.json                  # Bun workspace (nur apps/web)
└── README.md
```

Kein Turborepo — ein simples bun workspace + Makefile reicht für 2 Apps.

---

## Implementierungs-Phasen

### Phase 0: Feature-Validierung (Gate — vor allem anderen)
1. AcousticBrainz Sample-Dump downloaden (2 GB, 100K Items)
2. `scripts/extract_genre_mbids.py`: Genre-Tags aus Highlevel-Daten extrahieren → stratified MBID-Liste
3. 1.000 Tracks via stratified Sampling extrahieren (gleichverteilt über 9 Genres)
4. 44-dim Vektoren berechnen + normalisieren
5. **HPCP-Reduktion verifizieren**: Reines A-440Hz muss dominantes A in 12-bin Chroma zeigen
6. **50+ Query-Songs** mit Ground-Truth-Paaren definieren (einfache + harte Positive + Negative)
7. Cosine Similarity + gewichtete Similarity (s. MFCC-Dominanz) testen
8. **Präzisions-Metrik**: Top-10 Precision, verglichen mit Random Baseline
9. **Go/No-Go Entscheidung**: Wenn Top-10 Precision < 30% → Feature-Auswahl/Gewichtung überarbeiten

### Phase 1: Projekt-Setup & Infrastruktur
1. GitHub Repo erstellen (`beattrack`)
2. Bun workspace aufsetzen (root `package.json` mit `workspaces: ["apps/web"]`)
3. Next.js 15 App initialisieren (TailwindCSS, Vitest, Playwright)
4. Python FastAPI Projekt initialisieren (uv, pytest, essentia, procrastinate)
5. Supabase Projekt erstellen, pgvector + pg_trgm + config + procrastinate Migration
6. CI/CD Pipeline (GitHub Actions)
7. Multi-stage Dockerfile für Python Backend (inkl. Essentia + fpcalc, Ziel <800 MB)
8. **Railway Hobby Plan** Deployment testen (1 GB RAM Minimum verifizieren)
9. Sentry Free Tier einrichten (`sentry_sdk.init(dsn=...)`)
10. Keepalive Cron (GitHub Actions → Railway `/health` + Supabase `SELECT 1`)

### Phase 2: Backend — Async Feature-Extraktion (TDD)
1. Test-Audio-Fixtures generieren (Sinuswellen, bekannte Frequenzen, **plus korrupte Files**)
2. Tests schreiben:
   - Vektor-Shape == (44,)
   - Keine NaN-Werte
   - Deterministische Outputs für gleichen Input
   - HPCP-Reduktion: A-440 Hz → dominantes A in Chroma
   - Normalisierung mit globalen Stats aus DB
   - File-Size-Validierung (max 50 MB)
   - Format-Validierung (MP3, WAV, FLAC, OGG)
   - **ffprobe-Validierung blockt korrupte Files**
   - **Essentia-Subprocess crasht gracefully** (kein Worker-Kill)
3. Audio-Validierung mit ffprobe implementieren
4. Essentia `MusicExtractor` Pipeline als Subprocess implementieren
5. **Procrastinate Worker** implementieren (async Feature-Extraktion via Postgres Queue)
6. Tests für FastAPI Endpoints schreiben (inkl. SSE-Stream)
7. Endpoints implementieren:
   - `POST /analyze` → Job erstellen (mit Rate-Limiting)
   - `GET /analyze/{job_id}/stream` → SSE Progress-Stream
   - `GET /analyze/{job_id}/results` → Ergebnisse (Fallback)
   - `POST /search` → URL-Metadata-Lookup
   - `GET /health` → Health Check inkl. DB + Stats-Validierung
8. Supabase pgvector Integration (Insert + Similarity Query)
9. **Startup-Validierung**: Normalisierungs-Stats aus `config`-Tabelle laden, Fehler bei fehlenden Stats

### Phase 3: Daten — AcousticBrainz Seeding
1. **Jetzt AcousticBrainz Dumps archivieren** (eigene Kopie, Zukunftssicherheit)
2. Genre-stratified MBID-Liste erstellen (`scripts/extract_genre_mbids.py`)
3. Streaming-ETL-Script (`scripts/seed_acousticbrainz.py`)
   - Zstandard-Archive stream-parsen
   - **Stratified Sampling**: Nur MBIDs aus Genre-Liste
   - Feature-Vektoren (44 dims) + Metadata aus `metadata.tags` extrahieren
   - Records mit fehlenden Features oder NaN überspringen
   - **Checkpoints alle 10K Records** (Resume bei Abbruch)
   - Globale Normalisierungs-Stats berechnen → in `config`-Tabelle speichern
   - Raw + Normalized Vektoren in Supabase laden
   - **Ziel: 300K Songs** (genre-diversifiziert)
4. MusicBrainz Metadata-Enrichment nur für Lücken (`scripts/enrich_metadata.py`)
   - Nur Tracks mit `metadata_status: 'pending'` (~60-90K statt 300K)
   - Registrierter User-Agent
   - 1 req/s Rate-Limit → ~17-25 Stunden (auf Cloud-Instanz, nicht lokal)
   - Retry mit exponential Backoff
   - Resume-Fähigkeit (Checkpoint pro 1.000er-Batch)
5. Validierung: Similarity Search mit bekannten ähnlichen Songs testen

### Phase 4: Backend — Song-Identifikation & URL-Input
1. AcoustID Integration (Chromaprint `fpcalc` serverseitig → MusicBrainz ID)
   - Fallback: Song als "Unknown" analysieren wenn kein AcoustID-Match
2. MusicBrainz API Client (Metadata-Lookup, mit Rate-Limiting)
3. URL-Metadata-Extraktion:
   - YouTube: oEmbed API → Titel parsen (Heuristik: "Artist - Title"), Kanal-Name als Fallback
   - Spotify: URL-Slug parsen → Track-Name extrahieren
   - Fuzzy DB-Suche (pg_trgm) auf Titel + Artist
4. Endpoint: `POST /identify`, `POST /search`

### Phase 5: Frontend — Upload & Analyse-Flow (TDD)
1. Landing Page mit Upload-Zone (Drag & Drop)
   - **Client-seitige Validierung**: Max 50 MB, nur MP3/WAV/FLAC/OGG
   - Upload direkt an Python API (nicht über Next.js API Route — umgeht 4.5 MB Limit)
   - CORS-Konfiguration Backend ↔ Frontend
2. **Analysis-Progress-Komponente**: SSE-Connection mit Reconnect-Logic, Progress-Animation
   - Fallback auf Polling mit exponential Backoff wenn SSE nicht supportet wird
3. URL-Input Komponente
4. API-Integration (Upload → Job → SSE Stream → Results)
5. Visuell mit Chrome Extension / Playwright MCP verifizieren

### Phase 6: Frontend — Results & Feedback
1. Song-Card Komponente (Titel, Artist, Similarity %, BPM, Key)
   - Search-Links: "Auf Spotify suchen", "Auf YouTube suchen"
   - **Feedback-Buttons**: Daumen hoch/runter pro Ergebnis → in `feedback`-Tabelle speichern
2. **Feature-Radar-Chart**: 5 menschliche Kategorien statt roher Dimensionen:
   - **Klangfarbe** (MFCC Mean/Stdev) — "Wie ähnlich klingt die Instrumentierung?"
   - **Harmonie** (HPCP Chroma) — "Ähnliche Akkorde und Tonart?"
   - **Tempo** (BPM + Danceability) — "Ähnliches Tempo und Groove?"
   - **Helligkeit** (Spectral Centroid + Rolloff) — "Ähnlich hell oder warm?"
   - **Intensität** (Loudness + Zero Crossing Rate) — "Ähnliche Energie und Dynamik?"
   - Tooltips pro Achse mit kurzer Erklärung
3. Results Page mit staggered Reveal Animation (Framer Motion)
4. **Ergebnis-Filter**: Nach BPM-Range, Key, Similarity-Threshold
5. Responsive Design (Mobile, Tablet, Desktop)
6. Visuell verifizieren

### Phase 7: Polish & Deploy
1. Error Handling & Loading States
   - **Cold-Start UX**: "Wir wachen gerade auf..." Message wenn Backend kalt ist
   - Analyse-Timeout nach 120s mit Retry-Option
2. Privacy Policy Seite (Audio wird nicht gespeichert, Features sind keine PII)
3. SEO (Metadata, OG Tags)
4. Deploy: Vercel (Frontend) + Railway Hobby (Backend) + Supabase
5. Health-Ping Cron (GitHub Actions → Railway + Supabase)
6. End-to-End Test Suite
7. **"Nicht in DB" UX**: Als Feature positionieren, nicht als Fehler + Upload-CTA

---

## Testing-Strategie

### Backend (pytest, TDD)
```python
def test_feature_vector_shape():
    features = extract_features_safe("tests/fixtures/sine_440hz.wav")
    assert features.shape == (44,)
    assert not np.any(np.isnan(features))

def test_deterministic_output():
    f1 = extract_features_safe("tests/fixtures/sine_440hz.wav")
    f2 = extract_features_safe("tests/fixtures/sine_440hz.wav")
    np.testing.assert_array_almost_equal(f1, f2)

def test_hpcp_reduction_correct():
    """A-440 Hz muss dominantes A in 12-bin Chroma zeigen."""
    features = extract_features_safe("tests/fixtures/sine_440hz.wav")
    hpcp_12 = features[26:38]  # HPCP dims in vector
    assert np.argmax(hpcp_12) == 0  # Bin 0 = A (Essentia default reference)

def test_normalization_uses_global_stats():
    raw = extract_raw_features("tests/fixtures/sine_440hz.wav")
    normalized = apply_global_normalization(raw)
    assert normalized.mean() != 0.0  # wäre 0 bei per-Vektor z-score

def test_file_size_validation():
    with pytest.raises(ValidationError):
        validate_upload(large_file_path)

def test_corrupt_file_handled_gracefully():
    """Korrupte Files dürfen den Worker nicht crashen."""
    with pytest.raises(FeatureExtractionError):
        extract_features_safe("tests/fixtures/corrupt.mp3")

def test_ffprobe_rejects_invalid_audio():
    assert not validate_audio_file("tests/fixtures/not_audio.txt")
    assert not validate_audio_file("tests/fixtures/corrupt.mp3")
    assert validate_audio_file("tests/fixtures/sine_440hz.wav")

def test_startup_fails_without_normalization_stats():
    with pytest.raises(StartupError):
        load_normalization_stats(empty_config_table)

def test_youtube_title_parsing():
    assert parse_youtube_title("Artist - Song Title") == ("Artist", "Song Title")
    assert parse_youtube_title("Song Title") == (None, "Song Title")
```

### Frontend (Vitest)
```typescript
test('upload zone rejects files over 50MB', () => { ... })
test('upload zone rejects non-audio files', () => { ... })
test('SSE connection receives progress updates', () => { ... })
test('SSE reconnects on connection drop', () => { ... })
test('results display song cards with search links', () => { ... })
test('feature radar chart renders 5 categories', () => { ... })
test('feedback buttons send rating to API', () => { ... })
```

### E2E (Playwright)
```typescript
test('full flow: upload → analyze → SSE progress → results', async ({ page }) => {
  await page.goto('/');
  await page.setInputFiles('[data-testid="upload"]', 'fixtures/test.mp3');
  await expect(page.locator('[data-testid="analysis-progress"]')).toBeVisible();
  await expect(page.locator('[data-testid="results"]')).toBeVisible({ timeout: 120000 });
  await expect(page.locator('[data-testid="song-card"]')).toHaveCount({ min: 1 });
  await expect(page.locator('[data-testid="feature-radar"]')).toBeVisible();
});
```

### Visuelle Verifikation
Jede Frontend-Änderung mit Claude in Chrome Extension oder Playwright MCP Screenshot prüfen.

---

## Verifizierung

1. **Unit Tests**: `cd apps/api && pytest` + `cd apps/web && bun test`
2. **E2E Tests**: `bunx playwright test`
3. **Phase-0 Validierung**: `python scripts/validate_features.py` → Top-10 Precision über 50+ Queries
4. **HPCP Sanity**: A-440 Hz → Bin 0 dominant in 12-bin Chroma
5. **Corrupt File Handling**: Korrupte MP3/WAV hochladen → saubere Fehlermeldung, kein Worker-Crash
6. **Manuell**: Audio hochladen → prüfen ob Results Genre/Stil-kohärent sind
7. **Visuell**: Jede UI-Änderung per Chrome Extension Screenshot verifizieren
8. **API**: `curl -X POST /analyze -F "file=@test.mp3"` → Job-ID → SSE → Results
9. **Similarity-Sanity**: Tracks vom selben Album müssen hohe Similarity haben
10. **Cold-Start-Test**: Railway Instance komplett kalt starten → UX prüfen
11. **Radar-Chart-Check**: 5 Kategorien müssen für bekannte Paare plausibel sein
12. **Rate-Limiting**: >10 Requests/Min von gleicher IP → 429 Response

---

## Risiken & Mitigationen

| Risiko | Impact | Mitigation |
|---|---|---|
| 44-dim Features liefern schlechte Similarity | Hoch | Phase 0 Gate mit 50+ Queries + Präzisions-Metrik, gewichtete Similarity |
| MFCC-Dominanz (59% der Dimensionen) verzerrt Ergebnisse | Hoch | Gewichtete Feature-Gruppen-Similarity statt reines Cosine |
| Essentia crasht bei korrupten Files (C++ Segfault) | Hoch | Subprocess-Isolation + ffprobe Pre-Validierung |
| Essentia zu groß für Free Tier Hosting | Hoch | Railway Hobby Plan ($5/Monat), Multi-stage Dockerfile |
| Analyse dauert >60s | Mittel | Procrastinate Job-Queue + SSE Progress-Stream |
| AcousticBrainz-Daten veraltet (post-2022 fehlt) | Mittel | User-Uploads als Wachstum, transparent kommunizieren |
| AcousticBrainz-Downloads könnten offline gehen | Mittel | Dump jetzt archivieren (eigene Kopie) |
| MusicBrainz Metadata-Enrichment dauert lange | Niedrig | Metadata aus `metadata.tags` nutzen, API nur für Lücken (~70% weniger Calls) |
| Supabase Free Tier pausiert nach 7 Tagen | Mittel | Cron-Ping alle 3 Tage (GitHub Actions → `SELECT 1`) |
| Supabase Free Tier Storage voll | Mittel | Kein Audio-Storage, nur Vektoren + Metadata (~350 MB bei 300K Songs) |
| AcoustID "non-commercial" Konflikt | Niedrig | Beattrack bleibt non-commercial, kein Monetarisierungsplan |
| YouTube oEmbed gibt keinen Artist | Mittel | Titel-Heuristik + Fuzzy-Search (pg_trgm), Fallback auf Upload |
| Normalisierungs-Drift bei vielen User-Uploads | Niedrig | Raw-Vektoren gespeichert, Re-Normalisierung als Batch möglich |
| API-Missbrauch (kein Auth, öffentlich) | Mittel | Rate-Limiting (slowapi, 10 req/min/IP), Concurrent-Request-Cap |

---

## Lizenz-Übersicht

| Komponente | Lizenz | Kosten | Hinweis |
|---|---|---|---|
| Essentia | AGPL v3 | Free | Beattrack ist Open Source → OK |
| AcousticBrainz Data | CC0 / Open | Free | Eingefroren seit 2022, Downloads aktuell noch online |
| AcoustID API | Free (non-commercial) | Free | Beattrack muss non-commercial bleiben |
| MusicBrainz API | Free | Free | User-Agent Pflicht |
| Procrastinate | MIT | Free | Postgres-basierte Job-Queue (v3.7.2, aktiv maintained) |
| Supabase | Free Tier | Free | 500 MB DB, kein Audio-Storage |
| Vercel | Free Tier | Free | |
| Railway | Hobby | $5/mo | Min. 1 GB RAM für Essentia — Free Tier reicht nicht |
| Sentry | Free Tier | Free | 5K Events/Monat |
| slowapi | MIT | Free | Rate-Limiting |
| Next.js | MIT | Free | |
| FastAPI | MIT | Free | |

**AGPL v3 (Essentia)**: Kein Problem, da Beattrack selbst Open Source auf GitHub ist. Deployment-Configs (mit API-Keys) müssen **nicht** veröffentlicht werden — nur der Quellcode.

**AcoustID non-commercial**: Beattrack darf keine Werbung, Affiliate-Links oder Premium-Features haben, solange AcoustID genutzt wird. Falls Monetarisierung geplant wird, muss AcoustID durch eine Alternative ersetzt werden.
