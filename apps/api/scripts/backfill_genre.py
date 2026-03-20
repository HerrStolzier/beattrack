"""Backfill genre for existing songs using Deezer Album API.

Fetches album genre for songs that have deezer_id but genre='Electronic' (hardcoded default).
Loops through batches until all songs are processed or --limit is reached.

Usage:
    python scripts/backfill_genre.py                      # Dry run
    python scripts/backfill_genre.py --apply               # Apply all
    python scripts/backfill_genre.py --apply --limit 1000  # Apply first 1000
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

from app.services.genre import resolve_genre_from_album

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEEZER_API = "https://api.deezer.com"
API_DELAY = 0.12


def deezer_get(endpoint: str, retries: int = 3) -> dict | None:
    url = f"{DEEZER_API}{endpoint}" if not endpoint.startswith("http") else endpoint
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            resp = urllib.request.urlopen(req, timeout=15)  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                return None
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                return None
    return None


def get_album_id_for_track(deezer_id: int) -> int | None:
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

    album_cache: dict[int, str] = {}
    stats = {"unchanged": 0, "updated": 0, "failed": 0}
    processed = 0
    max_songs = args.limit or float("inf")
    batch_num = 0

    while processed < max_songs:
        # Fetch next batch of songs still tagged 'Electronic'
        fetch_limit = min(args.batch_size, int(max_songs - processed)) if args.limit else args.batch_size
        for retry in range(3):
            try:
                result = (
                    sb.table("songs")
                    .select("id, deezer_id, artist, title, genre")
                    .eq("genre", "Electronic")
                    .not_.is_("deezer_id", "null")
                    .order("created_at", desc=False)
                    .limit(fetch_limit)
                    .execute()
                )
                songs = result.data or []
                break
            except Exception as exc:
                wait = 30 * (retry + 1)
                logger.warning("DB fetch failed (attempt %d/3), retry in %ds: %s", retry + 1, wait, exc)
                time.sleep(wait)
        else:
            logger.error("DB fetch failed 3 times, stopping.")
            break

        if not songs:
            logger.info("No more songs to backfill.")
            break

        batch_num += 1
        logger.info("=== Batch %d: %d songs (total processed: %d) ===", batch_num, len(songs), processed)

        for song in songs:
            deezer_id = song["deezer_id"]

            time.sleep(API_DELAY)
            album_id = get_album_id_for_track(deezer_id)

            if not album_id:
                stats["failed"] += 1
                processed += 1
                continue

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
                    for retry in range(3):
                        try:
                            sb.rpc("update_song_genre", {
                                "song_id": song["id"],
                                "new_genre": genre,
                            }).execute()
                            break
                        except Exception as exc:
                            if retry < 2:
                                time.sleep(5 * (retry + 1))
                            else:
                                logger.error("Failed to update %s after 3 tries: %s", song["id"], exc)
                                stats["failed"] += 1
                                stats["updated"] -= 1

                logger.info(
                    "[%d] %s — %s: %s → %s",
                    processed + 1, song["artist"], song["title"], song["genre"], genre,
                )

            processed += 1
            if (processed) % 100 == 0:
                logger.info(
                    "Progress: %d | updated=%d unchanged=%d failed=%d cached=%d",
                    processed, stats["updated"], stats["unchanged"], stats["failed"], len(album_cache),
                )

    logger.info(
        "Done! processed=%d updated=%d unchanged=%d failed=%d cached_albums=%d",
        processed, stats["updated"], stats["unchanged"], stats["failed"], len(album_cache),
    )


if __name__ == "__main__":
    main()
