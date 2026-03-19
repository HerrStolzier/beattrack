"""Backfill genre for existing songs using Deezer Album API.

Fetches album genre for songs that have deezer_id but genre='Electronic' (hardcoded default).
Rate-limited to respect Deezer's 50 req/5s limit.

Usage:
    python scripts/backfill_genre.py                  # Dry run (show what would change)
    python scripts/backfill_genre.py --apply           # Apply changes
    python scripts/backfill_genre.py --apply --limit 100  # Process first 100 songs
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

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.genre import DEEZER_GENRE_MAP, resolve_genre_from_album

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEEZER_API = "https://api.deezer.com"
API_DELAY = 0.12  # ~8 req/s, well under Deezer's 50/5s limit


def deezer_get(endpoint: str, retries: int = 3) -> dict | None:
    url = f"{DEEZER_API}{endpoint}" if not endpoint.startswith("http") else endpoint
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            resp = urllib.request.urlopen(req, timeout=15)  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                logger.warning("Deezer error: %s", data["error"])
                return None
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                return None
    return None


def get_album_id_for_track(deezer_id: int) -> int | None:
    """Fetch track from Deezer to get album_id."""
    data = deezer_get(f"/track/{deezer_id}")
    if data and isinstance(data, dict):
        return data.get("album", {}).get("id")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill genre from Deezer Album API")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    parser.add_argument("--limit", type=int, default=0, help="Max songs to process (0=all)")
    parser.add_argument("--batch-size", type=int, default=500, help="DB fetch batch size")
    args = parser.parse_args()

    from app.db import get_supabase
    sb = get_supabase()

    # Fetch songs with hardcoded genre
    query = (
        sb.table("songs")
        .select("id, deezer_id, artist, title, genre")
        .eq("genre", "Electronic")
        .not_.is_("deezer_id", "null")
        .order("created_at", desc=False)
    )
    if args.limit:
        query = query.limit(args.limit)
    else:
        query = query.limit(args.batch_size)

    result = query.execute()
    songs = result.data or []

    if not songs:
        logger.info("No songs to backfill.")
        return

    logger.info("Processing %d songs (apply=%s)", len(songs), args.apply)

    # Cache: album_id → genre (avoid re-fetching same album)
    album_cache: dict[int, str] = {}
    stats = {"unchanged": 0, "updated": 0, "failed": 0}
    total = len(songs)

    for i, song in enumerate(songs):
        deezer_id = song["deezer_id"]

        # 1. Get album_id from track
        time.sleep(API_DELAY)
        album_id = get_album_id_for_track(deezer_id)

        if not album_id:
            stats["failed"] += 1
            continue

        # 2. Resolve genre (with cache)
        if album_id in album_cache:
            genre = album_cache[album_id]
        else:
            time.sleep(API_DELAY)
            genre = resolve_genre_from_album(album_id, deezer_get=deezer_get)
            album_cache[album_id] = genre

        if genre == "Electronic":
            stats["unchanged"] += 1
        else:
            stats["updated"] += 1
            if args.apply:
                try:
                    sb.table("songs").update({"genre": genre}).eq("id", song["id"]).execute()
                except Exception as exc:
                    logger.error("Failed to update %s: %s", song["id"], exc)
                    stats["failed"] += 1
                    stats["updated"] -= 1

            logger.info(
                "[%d/%d] %s — %s: %s → %s",
                i + 1, total, song["artist"], song["title"], song["genre"], genre,
            )

        if (i + 1) % 100 == 0:
            logger.info("Progress: %d/%d | updated=%d unchanged=%d failed=%d",
                        i + 1, total, stats["updated"], stats["unchanged"], stats["failed"])

    logger.info("Done! updated=%d unchanged=%d failed=%d cached_albums=%d",
                stats["updated"], stats["unchanged"], stats["failed"], len(album_cache))


if __name__ == "__main__":
    main()
