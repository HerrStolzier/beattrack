# Backend Scripts

Run scripts from `apps/api` with the project virtualenv:

```bash
.venv/bin/python scripts/<script>.py
```

## Active

- `seed_deezer.py`: Deezer Electronic crawl and feature extraction.
- `import_features.py`: imports JSONL feature rows through Supabase RPC.
- `eval_similarity.py`: read-only recommendation quality evaluation.
- `catalog_health.py`: read-only catalog health report.

## Maintenance

- `backfill_deezer_id.py`: fills Deezer IDs where possible.
- `backfill_genre.py`: fills genre metadata from Deezer.
- `compute_stats.py`: recalculates normalization stats.
- `extract_mert_batch.py`: MERT embedding backfill.
- `eval_mert.py`: MERT quality/coverage evaluation helper.
- `analyze_embeddings.py`: embedding-space analysis helper.
- `feed_batch_ingest.py`: batch ingest feeder.

## Dangerous Maintenance

- `cleanup_genres.py`: can delete catalog rows when run with `--execute`.

## Legacy

- `seed_fma.py`: legacy FMA source, inactive.
- `seed_jamendo.py`: legacy Jamendo source, inactive.

## Generated Data

Large JSONL, checkpoint, log, and image files in this folder are generated artifacts from previous runs. Treat them carefully: do not commit new generated data unless it is intentionally part of a reproducible dataset or fixture.
