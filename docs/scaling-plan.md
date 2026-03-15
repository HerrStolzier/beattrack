# Beattrack Scaling Plan

> Stand: 2026-03-15 | Aktuell: ~33K Songs | Ziel: 500K–1M Songs

## Scope

**Iteration 1: Nur Electronic, ab 2000:**
- Elektronische Musik (EDM, House, Techno, Trance, Schranz, Hardtechno, IDM, Ambient Electronic, ...)

**Spätere Iterationen:**
- Deutschrap / Hip-Hop
- Metal (alle Subgenres)

Kein Mainstream-Pop, kein Jazz, keine Klassik, nichts vor 2000.

## Realistische Katalog-Größen

| Genre | Total existierend (ab 2000) | Frei verfügbar (Audio) | Metadaten (kein Audio) |
|-------|---------------------------|----------------------|----------------------|
| Deutschrap | ~200–350K Tracks | ~15–50K (Bandcamp, Jamendo) | ~50–100K (MusicBrainz) |
| Electronic | ~2–5M Tracks | ~200–300K (FMA + Jamendo + Bandcamp) | ~3–5M (MusicBrainz) |
| Metal | ~3.2M Tracks | ~100–500K (Bandcamp) | ~3.2M (Metal Archives) |
| **Summe (Scope)** | **~5–8M** | **~300K–850K** | **~6–8M** |

### Datenquellen pro Genre

| Quelle | Electronic | Metal | Deutschrap | Audio? | Lizenz |
|--------|-----------|-------|------------|--------|--------|
| **FMA** | ~30–40K ✓✓ | ~500–2K ✗ | ~100–500 ✗ | Ja | CC |
| **Jamendo** | ~150–250K ✓✓ | ~10–30K ✓ | ~5–15K ✓ | Ja | CC |
| **Bandcamp (free)** | ~5–10M ✓✓✓ | ~500K–1M ✓✓✓ | ~50K ✓ | Ja | Artist-Lizenz |
| **Metal Archives** | — | 4.1M ✓✓✓ | — | Nein | Metadaten |
| **MusicBrainz** | ~3–5M | ~2–3M | ~50–100K | Nein | CC0 |

**Fazit:** Mit FMA + Jamendo + Bandcamp-Free sind **300K–500K Songs** realistisch erreichbar — **ohne YouTube-Scraping**.

## Architektur-Entscheidung

### pgvector bleibt (vorerst)

Der Critic hat richtig erkannt: FAISS bringt mehr Ops-Komplexität als Nutzen bei <1M Songs.

**Warum pgvector reicht:**
- 500K Songs × 200d × 4 Bytes = ~400 MB Embeddings
- HNSW-Index: ~600 MB
- Gesamt: ~1 GB — Supabase Small (2 GB RAM, $50/Mo) reicht
- Kein Cold-Start-Problem, ACID-Garantien, Backups inklusive

**Wann migrieren:** Erst wenn pgvector-Queries >100ms dauern (erfahrungsgemäß ab ~2–5M Songs).

```
┌─────────────────────────────────────────────┐
│  Mac Mini (lokal)                           │
│  • Essentia-Analyse (~10s/Song, 8 Worker)   │
│  • Batch-Seeding-Pipeline                   │
│  • Audio downloaden → analysieren → löschen │
└──────────────┬──────────────────────────────┘
               │ Metadaten + Embeddings
               ▼
┌─────────────────────────────────────────────┐
│  Railway (API, Pro)               ~$20/Mo   │
│  • FastAPI (wie bisher)                     │
│  • Similarity via Supabase RPC              │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Supabase (Pro, Small)             $50/Mo   │
│  • songs + Embeddings (pgvector)            │
│  • config, feedback                         │
│  • HNSW-Index auf learned_embedding         │
└─────────────────────────────────────────────┘
```

**Kosten: ~$70/Mo** für bis zu 500K–1M Songs. Keine Architektur-Migration nötig.

## Seeding-Pipeline

### Reihenfolge

1. **FMA-large** (106K, ~100 GB) → sofort, bereits getestet
2. **Jamendo API** (~200K Electronic + Metal) → API-Key beantragen, Genre-Filter
3. **Bandcamp Free** (~100K–500K) → Crawler für Free-Download-Tracks

### Pipeline pro Song

```
1. Metadaten holen (API/Dump)
2. Genre-Filter: nur Deutschrap / Electronic / Metal
3. Jahr-Filter: nur >= 2000
4. Duplikat-Check: AcoustID oder title+artist ILIKE
5. Audio downloaden (MP3, niedrige Qualität reicht)
6. Essentia-Analyse: MusiCNN (200d) + Handcrafted (44d)
7. Audio löschen
8. Metadaten + Embeddings → Supabase INSERT
```

### Zeitschätzung (Mac Mini, 8 Worker)

| Phase | Songs | Dauer |
|-------|-------|-------|
| FMA-large | 106K | ~1.5 Tage |
| Jamendo | 200K | ~3 Tage |
| Bandcamp | 200K | ~3 Tage |
| **Total** | **~500K** | **~7–8 Tage** |

## HNSW-Index Tuning

| Songs | m | ef_construction | ef_search | Erwartete Latenz |
|-------|---|----------------|-----------|-----------------|
| 33K (jetzt) | 16 | 64 | 40 (default) | <10ms |
| 100K | 16 | 64 | 40 | ~10ms |
| 500K | 24 | 128 | 80 | ~20–30ms |
| 1M | 32 | 200 | 100 | ~30–50ms |

Migration bei 500K:
```sql
-- Drop + Rebuild mit besseren Params
DROP INDEX idx_songs_learned_embedding;
CREATE INDEX idx_songs_learned_embedding
    ON songs USING hnsw (learned_embedding vector_cosine_ops)
    WITH (m = 24, ef_construction = 128);
```

## Phasen

### Phase 1: Bestehende Songs bereinigen + FMA-large seeden (jetzt)
- [x] Migration 010: `genre` + `release_year` Spalten hinzugefügt
- [x] `seed_fma.py` um `--genres` und `--min-year` Filter erweitert
- [x] `cleanup_genres.py` Script zum Taggen + Bereinigen bestehender Songs
- [ ] Cleanup ausführen: nicht-Electronic Songs löschen
- [ ] FMA-large (~100 GB) downloaden
- [ ] Seeding mit `--genres Electronic --min-year 2000` laufen lassen
- [ ] `compute_stats.py` nach Seeding ausführen (Normalisierung)
- [ ] Ziel: ~35K Electronic Songs aus FMA

### Phase 2: Jamendo Integration
- [ ] Jamendo API-Key beantragen
- [ ] Genre-Endpoint nutzen: Electronic, Metal, Hip-Hop
- [ ] Batch-Download + Essentia-Analyse
- [ ] Ziel: +150–200K Songs

### Phase 3: Bandcamp Free Tracks
- [ ] Crawler für Free-Download-Seiten (nach Genre-Tags)
- [ ] Nur Tracks mit explizitem Free-Download
- [ ] Ziel: +100–200K Songs

### Phase 4: Supabase Upgrade + Index-Tuning (bei ~500K)
- [ ] Upgrade MICRO → Small (2 GB RAM)
- [ ] HNSW-Index mit m=24, ef_construction=128 neu bauen
- [ ] Query-Performance benchmarken

### Phase 5: Qdrant-Migration (nur falls nötig, ab 1M+)
- [ ] Erst evaluieren wenn pgvector-Queries >100ms
- [ ] Qdrant als Docker-Container auf Railway
- [ ] Eingebaute Persistenz + Snapshots (besser als FAISS)

## Offene Fragen

- [ ] Jamendo API-Limits und Bulk-Download-Möglichkeiten?
- [ ] Bandcamp: Gibt es eine API oder muss man scrapen?
- [ ] Genre-Klassifikation: Was wenn FMA/Jamendo-Tags ungenau sind?
- [ ] User-Uploads: Gehen direkt in pgvector (kein Pipeline-Problem)
- [ ] Feedback-System: Skaliert bei 500K ohne Änderung
