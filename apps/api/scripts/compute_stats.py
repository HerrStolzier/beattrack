"""Compute handcrafted normalization stats and re-normalize all songs.

Usage:
    export SUPABASE_URL=https://xxx.supabase.co
    export SUPABASE_SERVICE_ROLE_KEY=eyJ...
    python scripts/compute_stats.py

Steps:
    1. Load all handcrafted_raw vectors from songs table
    2. Compute mean + std per dimension (44-dim)
    3. Upsert stats into config table as 'normalization_stats'
    4. Re-normalize all songs → update handcrafted_norm
"""
import json
import logging
import os
import sys

import numpy as np
from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def fetch_all_handcrafted(supabase) -> list[tuple[str, list[float]]]:
    """Fetch all (id, handcrafted_raw) pairs from songs table."""
    rows = []
    offset = 0
    while True:
        result = (
            supabase.table("songs")
            .select("id, handcrafted_raw")
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )
        if not result.data:
            break
        for row in result.data:
            raw = row["handcrafted_raw"]
            # pgvector returns string like "[0.1, 0.2, ...]"
            if isinstance(raw, str):
                raw = json.loads(raw.replace("(", "[").replace(")", "]"))
            rows.append((row["id"], raw))
        if len(result.data) < BATCH_SIZE:
            break
        offset += BATCH_SIZE
        if offset % 5000 == 0:
            logger.info("  Fetched %d rows...", offset)
    return rows


def compute_stats(vectors: list[list[float]]) -> dict:
    """Compute mean and std per dimension."""
    matrix = np.array(vectors, dtype=np.float64)
    mean = matrix.mean(axis=0).tolist()
    std = matrix.std(axis=0).tolist()
    # Avoid division by zero
    std = [s if s > 1e-10 else 1.0 for s in std]
    return {"mean": mean, "std": std, "dim": len(mean), "n_songs": len(vectors)}


def normalize(raw: list[float], mean: list[float], std: list[float]) -> list[float]:
    """Z-score normalize a single vector."""
    return [(v - m) / s for v, m, s in zip(raw, mean, std)]


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Error: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars")
        sys.exit(1)

    supabase = create_client(url, key)

    # 1. Fetch all handcrafted_raw vectors
    logger.info("Fetching handcrafted_raw vectors from songs table...")
    rows = fetch_all_handcrafted(supabase)
    logger.info("Fetched %d songs", len(rows))

    if not rows:
        logger.error("No songs found in database. Run seed_fma.py first.")
        sys.exit(1)

    # 2. Compute stats
    vectors = [raw for _, raw in rows]
    stats = compute_stats(vectors)
    logger.info(
        "Stats computed: dim=%d, n_songs=%d, mean_range=[%.3f, %.3f], std_range=[%.3f, %.3f]",
        stats["dim"],
        stats["n_songs"],
        min(stats["mean"]),
        max(stats["mean"]),
        min(stats["std"]),
        max(stats["std"]),
    )

    # 3. Upsert stats into config table
    logger.info("Saving normalization stats to config table...")
    supabase.table("config").upsert(
        {"key": "normalization_stats", "value": json.dumps(stats)}
    ).execute()
    logger.info("Stats saved as 'normalization_stats'")

    # 4. Re-normalize all songs
    logger.info("Re-normalizing %d songs...", len(rows))
    updated = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        for song_id, raw in batch:
            norm = normalize(raw, stats["mean"], stats["std"])
            try:
                supabase.table("songs").update(
                    {"handcrafted_norm": str(norm)}
                ).eq("id", song_id).execute()
                updated += 1
            except Exception as exc:
                logger.warning("Failed to update song %s: %s", song_id, exc)

        if updated % 1000 == 0 or updated == len(rows):
            logger.info("  %d/%d updated", updated, len(rows))

    logger.info("Done! %d songs re-normalized.", updated)


if __name__ == "__main__":
    main()
