# Data Pipeline

Beattrack's active catalog pipeline is Deezer-first.

The current product depends on commercial Electronic tracks with 30-second previews, extracted audio features, normalized handcrafted vectors, and optional MERT embeddings.

★ ʕ ᵔᴥᵔ ʔ Erklaerbaer
Think of the catalog as the app's record shelf. The pipeline decides which records are added, which labels are written on them, and which sound fingerprints are attached.

## Active Sources

- Deezer API: active source for commercial Electronic tracks and preview URLs.
- Deezer album/track metadata: active source for genre and Deezer IDs.
- Uploaded user audio: active runtime source for temporary analysis and similarity search.

## Maintenance Backfills

- `backfill_genre.py`: fills or corrects genre metadata.
- `extract_mert_batch.py`: adds MERT embeddings as a secondary ranking signal.
- `compute_stats.py`: recalculates normalization stats for handcrafted features.
- `cleanup_genres.py`: dangerous maintenance script for deleting out-of-scope catalog rows. Use only with `--execute` after review.

## Legacy Sources

- `seed_fma.py`: legacy FMA seeding. Not part of the current production catalog direction.
- `seed_jamendo.py`: legacy Jamendo seeding. Not part of the current production catalog direction.

## Health Check

Use the read-only catalog health script:

```bash
cd apps/api
.venv/bin/python scripts/catalog_health.py
```

It reports estimated total songs, estimated missing genre count, estimated missing MERT count, duplicate Deezer IDs in a bounded scan, duplicate title/artist pairs in a bounded scan, and normalization stats metadata.

Supabase exact counts can hit statement timeouts on this project, so the script uses planned counts for the broad totals and a limited paged scan for duplicate checks.

Required env vars:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

For production-like checks, `SUPABASE_ANON_KEY` may need the service role value if RLS blocks reads.

## MERT Strategy

MERT should stay a partial quality signal for now, not a hard requirement for every track.

Practical meaning: songs without MERT still work through MusiCNN and handcrafted features. MERT coverage should improve over time, but missing MERT should not block ingest or search.

Target for the next quality cycle:

- Track MERT coverage in `catalog_health.py`.
- Prioritize MERT backfill for high-traffic or high-quality Deezer rows.
- Compare recommendation quality with and without MERT using `scripts/eval_similarity.py`.
