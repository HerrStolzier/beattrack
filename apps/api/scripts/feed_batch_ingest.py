"""Feed crawled Deezer tracks to the Railway batch ingest endpoint.

Reads deezer_tracks.json and sends tracks in batches to the API.
Supports resume via checkpoint file.

Usage:
    python apps/api/scripts/feed_batch_ingest.py \
        --api-url https://beattrack-production.up.railway.app \
        --secret YOUR_ADMIN_SECRET \
        --batch-size 10

    # Resume after interrupt:
    python apps/api/scripts/feed_batch_ingest.py \
        --api-url ... --secret ... --resume
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DEFAULT_TRACKS = SCRIPT_DIR / "deezer_tracks.json"
CHECKPOINT_FILE = SCRIPT_DIR / "feed_checkpoint.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_checkpoint() -> set[int]:
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text())
        return set(data.get("processed_ids", []))
    return set()


def save_checkpoint(processed_ids: set[int]) -> None:
    CHECKPOINT_FILE.write_text(json.dumps({
        "processed_ids": sorted(processed_ids),
        "count": len(processed_ids),
    }))


def send_batch(api_url: str, secret: str, tracks: list[dict], timeout: int = 300) -> dict:
    """Send a batch of tracks to the ingest endpoint."""
    url = f"{api_url}/admin/ingest/batch"
    payload = json.dumps({"tracks": tracks}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8"))


def get_status(api_url: str, secret: str) -> dict:
    req = urllib.request.Request(
        f"{api_url}/admin/ingest/status",
        headers={"Authorization": f"Bearer {secret}"},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Feed tracks to batch ingest API")
    parser.add_argument("--api-url", required=True, help="Railway API URL")
    parser.add_argument("--secret", required=True, help="ADMIN_SECRET token")
    parser.add_argument("--tracks-json", default=str(DEFAULT_TRACKS))
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Max tracks to process (0=all)")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between batches")
    args = parser.parse_args()

    # Load tracks
    tracks_file = Path(args.tracks_json)
    if not tracks_file.exists():
        logger.error("Tracks file not found: %s", tracks_file)
        sys.exit(1)

    with open(tracks_file, encoding="utf-8") as f:
        all_tracks = json.load(f)
    logger.info("Loaded %d tracks from %s", len(all_tracks), tracks_file)

    # Filter already processed
    processed_ids = load_checkpoint() if args.resume else set()
    if args.resume and processed_ids:
        logger.info("Resuming: %d already processed", len(processed_ids))

    work = [t for t in all_tracks if t["deezer_id"] not in processed_ids]
    if args.limit:
        work = work[:args.limit]

    logger.info("%d tracks to process", len(work))
    if not work:
        return

    # Check API is up
    try:
        status = get_status(args.api_url, args.secret)
        logger.info("API online — status: %s", status.get("status", "ok"))
    except Exception as exc:
        logger.error("API not reachable: %s", exc)
        sys.exit(1)

    # Process in batches
    total_succeeded = 0
    total_failed = 0
    batch_num = 0

    for i in range(0, len(work), args.batch_size):
        batch = work[i : i + args.batch_size]
        batch_num += 1

        # Convert to API format
        api_tracks = []
        for t in batch:
            api_tracks.append({
                "deezer_id": t["deezer_id"],
                "title": t["title"],
                "artist": t["artist"],
                "artist_id": t.get("artist_id"),
                "album": t.get("album"),
                "duration": t.get("duration", 0),
                "preview_url": t.get("preview_url"),
            })

        try:
            result = send_batch(args.api_url, args.secret, api_tracks)
            total_succeeded += result.get("succeeded", 0)
            total_failed += result.get("failed", 0)

            # Mark as processed
            for t in batch:
                processed_ids.add(t["deezer_id"])

            # Checkpoint every 10 batches
            if batch_num % 10 == 0:
                save_checkpoint(processed_ids)

            progress = min(i + len(batch), len(work))
            logger.info(
                "Batch %d: %d/%d succeeded | Progress: %d/%d (%.1f%%) | Total: %d succeeded, %d failed",
                batch_num,
                result.get("succeeded", 0),
                len(batch),
                progress,
                len(work),
                progress / len(work) * 100,
                total_succeeded,
                total_failed,
            )

            if result.get("errors"):
                for err in result["errors"][:3]:
                    logger.warning("  Error: %s", err)

        except urllib.error.HTTPError as exc:
            logger.error("HTTP %d on batch %d: %s", exc.code, batch_num, exc.read().decode()[:200])
            save_checkpoint(processed_ids)
            if exc.code in (503, 502, 429):
                logger.info("Waiting 60s before retry...")
                time.sleep(60)
                continue
            break
        except Exception as exc:
            logger.error("Batch %d failed: %s", batch_num, exc)
            save_checkpoint(processed_ids)
            time.sleep(10)
            continue

        time.sleep(args.delay)

    # Final checkpoint
    save_checkpoint(processed_ids)
    logger.info("Done! Total: %d succeeded, %d failed out of %d", total_succeeded, total_failed, len(work))

    logger.info("Feed complete.")


if __name__ == "__main__":
    main()
