"""Import extracted features from JSONL into Supabase via REST RPC.

Calls the bulk_import_songs() SECURITY DEFINER function via Supabase
REST API using the anon key — no service_role_key needed.

Usage:
    python apps/api/scripts/import_features.py \
        --url https://qpkemujemfnymtgmtkfg.supabase.co \
        --key eyJ... \
        --batch-size 25

    # Resume from a specific batch:
    python apps/api/scripts/import_features.py \
        --url ... --key ... --start-batch 50
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DEFAULT_JSONL = SCRIPT_DIR / "seed_features.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def call_rpc(url: str, key: str, rows: list[dict]) -> int:
    """Call bulk_import_songs RPC and return number of inserted rows."""
    rpc_url = f"{url}/rest/v1/rpc/bulk_import_songs"
    payload = json.dumps({"rows": rows}).encode("utf-8")

    req = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method="POST",
    )

    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read().decode("utf-8"))
    return result if isinstance(result, int) else len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import features JSONL into Supabase via RPC."
    )
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL), help="Input JSONL file")
    parser.add_argument("--url", required=True, help="Supabase project URL")
    parser.add_argument("--key", required=True, help="Supabase anon key")
    parser.add_argument(
        "--batch-size", type=int, default=25,
        help="Rows per RPC call (default: 25, keep low for large vectors)",
    )
    parser.add_argument(
        "--start-batch", type=int, default=1,
        help="Resume from batch N (default: 1)",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl).resolve()
    if not jsonl_path.is_file():
        logger.error("JSONL file not found: %s", jsonl_path)
        sys.exit(1)

    # Read all rows
    rows = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                # Rename _tid to deezer_id for bulk_import_songs RPC
                tid = row.pop("_tid", None)
                if tid is not None:
                    row["deezer_id"] = str(tid)
                rows.append(row)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping invalid JSON on line %d: %s", line_num, exc)

    total = len(rows)
    logger.info("Loaded %d rows from '%s'", total, jsonl_path)

    if not rows:
        return

    # Split into batches
    batches = [
        rows[i : i + args.batch_size]
        for i in range(0, total, args.batch_size)
    ]
    num_batches = len(batches)
    logger.info(
        "%d batches of up to %d rows (starting from batch %d)",
        num_batches, args.batch_size, args.start_batch,
    )

    inserted_total = 0
    failed_batches = []

    for i, batch in enumerate(batches, 1):
        if i < args.start_batch:
            continue

        try:
            count = call_rpc(args.url, args.key, batch)
            inserted_total += count

            if i % 20 == 0 or i == num_batches:
                logger.info(
                    "Batch %d/%d done — %d/%d rows inserted so far",
                    i, num_batches, inserted_total, total,
                )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            logger.error("Batch %d failed (HTTP %d): %s", i, exc.code, body)
            failed_batches.append(i)
        except Exception as exc:
            logger.error("Batch %d failed: %s", i, exc)
            failed_batches.append(i)

        # Small delay to avoid rate limiting
        time.sleep(0.1)

    logger.info(
        "\nDone! %d/%d rows inserted. %d batches failed.",
        inserted_total, total, len(failed_batches),
    )
    if failed_batches:
        logger.info("Failed batches: %s", failed_batches)
        logger.info("Resume with: --start-batch %d", min(failed_batches))


if __name__ == "__main__":
    main()
