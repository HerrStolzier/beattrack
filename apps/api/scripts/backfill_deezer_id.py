"""Backfill deezer_id from JSONL into existing songs.

Matches songs by (title, artist) and updates their deezer_id.

Usage:
    python apps/api/scripts/backfill_deezer_id.py \
        --url https://xxx.supabase.co \
        --key eyJ... \
        --jsonl scripts/deezer_features.jsonl
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


def supabase_patch(url: str, key: str, song_id: str, deezer_id: int) -> bool:
    """Update a single song's deezer_id via Supabase REST API."""
    patch_url = f"{url}/rest/v1/songs?id=eq.{song_id}"
    payload = json.dumps({"deezer_id": deezer_id}).encode("utf-8")

    req = urllib.request.Request(
        patch_url,
        data=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="PATCH",
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        return True
    except urllib.error.HTTPError as exc:
        logger.warning("PATCH failed for %s: HTTP %d", song_id, exc.code)
        return False


def supabase_query(url: str, key: str, title: str, artist: str) -> str | None:
    """Find a song ID by exact title + artist match."""
    import urllib.parse

    # Use exact match to avoid false positives
    query_url = (
        f"{url}/rest/v1/songs"
        f"?title=eq.{urllib.parse.quote(title, safe='')}"
        f"&artist=eq.{urllib.parse.quote(artist, safe='')}"
        f"&source=eq.deezer"
        f"&deezer_id=is.null"
        f"&select=id"
        f"&limit=1"
    )

    req = urllib.request.Request(
        query_url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode("utf-8"))
        if data:
            return data[0]["id"]
    except Exception as exc:
        logger.debug("Query failed for '%s - %s': %s", artist, title, exc)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill deezer_id into existing songs.")
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL), help="JSONL with _tid field")
    parser.add_argument("--url", required=True, help="Supabase project URL")
    parser.add_argument("--key", required=True, help="Supabase anon key")
    parser.add_argument("--dry-run", action="store_true", help="Don't write, just show matches")
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl).resolve()
    if not jsonl_path.is_file():
        logger.error("JSONL not found: %s", jsonl_path)
        sys.exit(1)

    # Build mapping from JSONL: (title, artist) -> deezer_id
    tid_map: dict[tuple[str, str], int] = {}
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                tid = row.get("_tid")
                title = row.get("title", "").strip()
                artist = row.get("artist", "").strip()
                if tid and title and artist:
                    tid_map[(title, artist)] = int(tid)
            except (json.JSONDecodeError, ValueError):
                continue

    logger.info("Loaded %d title/artist -> deezer_id mappings", len(tid_map))

    matched = 0
    updated = 0
    errors = 0

    for i, ((title, artist), deezer_id) in enumerate(tid_map.items(), 1):
        song_id = supabase_query(args.url, args.key, title, artist)
        if not song_id:
            continue

        matched += 1
        if args.dry_run:
            logger.info("[DRY] %s - %s -> deezer_id=%d", artist, title, deezer_id)
        else:
            if supabase_patch(args.url, args.key, song_id, deezer_id):
                updated += 1
            else:
                errors += 1

        if i % 500 == 0:
            logger.info("Progress: %d/%d checked, %d matched, %d updated", i, len(tid_map), matched, updated)
            time.sleep(0.2)  # Rate limiting

        # Small delay between requests
        if not args.dry_run and matched % 10 == 0:
            time.sleep(0.05)

    logger.info(
        "Done! %d/%d matched, %d updated, %d errors",
        matched, len(tid_map), updated, errors,
    )


if __name__ == "__main__":
    main()
