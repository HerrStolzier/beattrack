"""Backfill deezer_id from JSONL into existing songs via RPC.

Uses the `backfill_deezer_ids(jsonb)` RPC function on Supabase
to batch-update songs by (title, artist) match.

Usage:
    python apps/api/scripts/backfill_deezer_id.py \
        --url https://xxx.supabase.co \
        --key eyJ... \
        --jsonl scripts/deezer_features.jsonl \
        --batch-size 500
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
DEFAULT_JSONL = SCRIPT_DIR / "deezer_features.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def call_rpc(url: str, key: str, batch: list[dict]) -> int:
    """Call backfill_deezer_ids RPC with a batch of {title, artist, deezer_id}."""
    rpc_url = f"{url}/rest/v1/rpc/backfill_deezer_ids"
    payload = json.dumps({"rows": batch}).encode("utf-8")

    req = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode("utf-8"))
        return int(result) if isinstance(result, (int, float)) else 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error("RPC failed (HTTP %d): %s", exc.code, body[:200])
        return -1
    except Exception as exc:
        logger.error("RPC error: %s", exc)
        return -1


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill deezer_id via RPC.")
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL), help="JSONL with _tid field")
    parser.add_argument("--url", required=True, help="Supabase project URL")
    parser.add_argument("--key", required=True, help="Supabase anon key")
    parser.add_argument("--batch-size", type=int, default=500, help="Rows per RPC call")
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl).resolve()
    if not jsonl_path.is_file():
        logger.error("JSONL not found: %s", jsonl_path)
        sys.exit(1)

    # Build unique mappings from JSONL
    seen: set[int] = set()
    rows: list[dict] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                tid = data.get("_tid")
                title = data.get("title", "").strip()
                artist = data.get("artist", "").strip()
                if tid and title and artist:
                    tid_int = int(tid)
                    if tid_int not in seen:
                        seen.add(tid_int)
                        rows.append({"title": title, "artist": artist, "deezer_id": tid_int})
            except (json.JSONDecodeError, ValueError):
                continue

    logger.info("Loaded %d unique deezer_id mappings", len(rows))

    total_updated = 0
    total_errors = 0
    batch_size = args.batch_size

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(rows) + batch_size - 1) // batch_size

        result = call_rpc(args.url, args.key, batch)
        if result < 0:
            total_errors += 1
            logger.warning("Batch %d/%d failed, continuing...", batch_num, total_batches)
        else:
            total_updated += result
            logger.info(
                "Batch %d/%d: %d updated (total: %d)",
                batch_num, total_batches, result, total_updated,
            )

        # Small delay between batches
        time.sleep(0.3)

    logger.info("Done! %d songs updated, %d batch errors", total_updated, total_errors)


if __name__ == "__main__":
    main()
