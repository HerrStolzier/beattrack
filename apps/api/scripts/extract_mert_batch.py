"""Batch-extract MERT embeddings for all songs missing them.

Downloads Deezer previews, extracts MERT-v1-95M embeddings, stores
in mert_embedding column via RPC.

Usage:
    python scripts/extract_mert_batch.py                  # Dry run
    python scripts/extract_mert_batch.py --apply           # Apply all
    python scripts/extract_mert_batch.py --apply --limit 100  # First 100

Performance: ~1.3s/song on Apple Silicon MPS. 121K songs ~ 44 hours.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request

# Add project root to path and load .env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEEZER_API = "https://api.deezer.com"
API_DELAY = 0.12


def fetch_preview_url(deezer_id: int) -> str | None:
    try:
        req = urllib.request.Request(
            f"{DEEZER_API}/track/{deezer_id}",
            headers={"Accept": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=15)  # noqa: S310
        data = json.loads(resp.read().decode())
        return data.get("preview")
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch extract MERT embeddings")
    parser.add_argument("--apply", action="store_true", help="Store embeddings in DB")
    parser.add_argument("--limit", type=int, default=0, help="Max songs (0=all)")
    parser.add_argument("--batch-size", type=int, default=500, help="DB fetch batch size")
    parser.add_argument("--checkpoint", type=str, default="mert_checkpoint.json", help="Checkpoint file")
    args = parser.parse_args()

    # Import MERT worker (loads model lazily)
    from app.workers.mert import extract_from_preview_url

    from app.db import get_supabase
    sb = get_supabase()

    # Load checkpoint (resume support)
    checkpoint_path = Path(__file__).parent / args.checkpoint
    processed_ids: set[str] = set()
    if checkpoint_path.exists():
        processed_ids = set(json.loads(checkpoint_path.read_text()))
        logger.info("Resuming: %d songs already processed", len(processed_ids))

    stats = {"extracted": 0, "skipped": 0, "failed": 0, "no_preview": 0}
    processed = 0
    max_songs = args.limit or float("inf")
    batch_num = 0
    start_time = time.time()

    while processed < max_songs:
        fetch_limit = min(args.batch_size, int(max_songs - processed)) if args.limit else args.batch_size
        result = (
            sb.table("songs")
            .select("id, deezer_id, artist, title")
            .is_("mert_embedding", "null")
            .not_.is_("deezer_id", "null")
            .order("created_at", desc=False)
            .limit(fetch_limit)
            .execute()
        )
        songs = result.data or []

        if not songs:
            logger.info("No more songs without MERT embeddings.")
            break

        batch_num += 1
        logger.info("=== Batch %d: %d songs (total: %d) ===", batch_num, len(songs), processed)

        for song in songs:
            sid = str(song["id"])

            if sid in processed_ids:
                stats["skipped"] += 1
                processed += 1
                continue

            deezer_id = song["deezer_id"]

            # Get preview URL
            time.sleep(API_DELAY)
            preview_url = fetch_preview_url(deezer_id)
            if not preview_url:
                stats["no_preview"] += 1
                processed_ids.add(sid)
                processed += 1
                continue

            # Extract MERT embedding
            embedding = extract_from_preview_url(preview_url)
            if embedding is None:
                stats["failed"] += 1
                processed_ids.add(sid)
                processed += 1
                continue

            stats["extracted"] += 1

            if args.apply:
                try:
                    sb.table("songs").update(
                        {"mert_embedding": str(embedding)}
                    ).eq("id", sid).execute()
                except Exception as exc:
                    # Try RPC fallback if RLS blocks direct update
                    try:
                        sb.rpc("update_song_mert", {
                            "song_id": sid,
                            "new_embedding": str(embedding),
                        }).execute()
                    except Exception:
                        logger.error("Failed to store MERT for %s: %s", sid, exc)
                        stats["failed"] += 1
                        stats["extracted"] -= 1

            processed_ids.add(sid)
            processed += 1

            if processed % 10 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                eta_min = (max_songs - processed) / rate / 60 if rate > 0 and max_songs != float("inf") else 0
                logger.info(
                    "[%d] %s - %s | extracted=%d failed=%d | %.1f songs/s%s",
                    processed, song["artist"], song["title"],
                    stats["extracted"], stats["failed"], rate,
                    f" | ETA: {eta_min:.0f}min" if eta_min > 0 else "",
                )

            # Save checkpoint every 50 songs
            if processed % 50 == 0:
                checkpoint_path.write_text(json.dumps(list(processed_ids)))

    # Final checkpoint
    checkpoint_path.write_text(json.dumps(list(processed_ids)))

    elapsed = time.time() - start_time
    logger.info(
        "Done! processed=%d extracted=%d failed=%d no_preview=%d skipped=%d (%.1f min)",
        processed, stats["extracted"], stats["failed"], stats["no_preview"],
        stats["skipped"], elapsed / 60,
    )


if __name__ == "__main__":
    main()
