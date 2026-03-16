"""Crawl Deezer for commercial Electronic tracks and extract audio features.

Downloads 30-second preview clips from the Deezer CDN, extracts MusiCNN +
handcrafted features via the existing Essentia pipeline, then outputs JSONL
for later import via import_features.py.  Preview files are deleted
immediately after extraction — only feature vectors are kept.

Usage:
    # Full crawl (50+ seed artists, ~15K tracks):
    python apps/api/scripts/seed_deezer.py --workers 4

    # Quick test with 3 seed artists:
    python apps/api/scripts/seed_deezer.py --limit-artists 3 --workers 4

    # Resume after interrupt:
    python apps/api/scripts/seed_deezer.py --resume --workers 4

    # Custom output:
    python apps/api/scripts/seed_deezer.py --output my_features.jsonl

Checkpoint file: seed_deezer_checkpoint.json (in this script's directory)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
EXTRACT_SCRIPT = SCRIPT_DIR.parent / "app" / "workers" / "extract.py"
CHECKPOINT_FILE = SCRIPT_DIR / "seed_deezer_checkpoint.json"
DEFAULT_OUTPUT = SCRIPT_DIR / "deezer_features.jsonl"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deezer API
# ---------------------------------------------------------------------------

DEEZER_API = "https://api.deezer.com"
API_DELAY = 0.4  # seconds between API calls (conservative rate limit)


def deezer_get(endpoint: str, retries: int = 3) -> dict | list | None:
    """GET a Deezer API endpoint with retry logic."""
    url = f"{DEEZER_API}{endpoint}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                logger.warning("Deezer API error on %s: %s", endpoint, data["error"])
                return None
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            if attempt < retries - 1:
                wait = 2 ** attempt
                logger.warning("Retry %d for %s: %s (wait %ds)", attempt + 1, endpoint, exc, wait)
                time.sleep(wait)
            else:
                logger.error("Failed after %d retries: %s — %s", retries, endpoint, exc)
                return None
    return None


def deezer_get_all(endpoint: str, limit: int = 0) -> list[dict]:
    """Paginate through a Deezer list endpoint. Returns all items."""
    items: list[dict] = []
    url = endpoint
    while url:
        time.sleep(API_DELAY)
        data = deezer_get(url.replace(DEEZER_API, "") if url.startswith("http") else url)
        if not data or not isinstance(data, dict):
            break
        items.extend(data.get("data", []))
        if limit and len(items) >= limit:
            items = items[:limit]
            break
        url = data.get("next", "")
    return items


# ---------------------------------------------------------------------------
# Seed artists — curated list of top Electronic/Dance/House artists
# ---------------------------------------------------------------------------

SEED_ARTIST_NAMES: list[str] = [
    # EDM / Progressive House
    "Avicii", "Calvin Harris", "David Guetta", "Tiësto", "Afrojack",
    "Steve Aoki", "Martin Garrix", "Marshmello", "Skrillex", "Zedd",
    "Kygo", "Swedish House Mafia", "Alan Walker", "Disclosure", "Deadmau5",
    # Trance
    "Armin van Buuren", "Above & Beyond", "Paul van Dyk", "ATB", "Dash Berlin",
    # Techno
    "Richie Hawtin", "Carl Cox", "Jeff Mills", "Adam Beyer", "Amelie Lens",
    "Charlotte de Witte", "Nina Kraviz",
    # House / Deep House
    "Bob Sinclar", "Robin Schulz", "Duke Dumont", "Oliver Heldens",
    "Fisher", "MK", "Faithless",
    # Drum & Bass
    "Pendulum", "Sub Focus", "Chase & Status", "Netsky", "Goldie",
    # UK / Melodic / Breaks
    "Bicep", "Fred again..", "The Chemical Brothers", "Underworld",
    "The Prodigy", "Moby", "Daft Punk", "Kraftwerk", "Rüfüs Du Sol",
    # Ambient / Downtempo
    "Bonobo", "Massive Attack", "Aphex Twin", "Boards of Canada", "Air",
]


def resolve_artist_id(name: str) -> dict | None:
    """Look up artist by name via Deezer search. Returns {id, name} or None."""
    from urllib.parse import quote
    time.sleep(API_DELAY)
    data = deezer_get(f"/search/artist?q={quote(name)}&limit=5")
    if not data or not isinstance(data, dict):
        return None
    for artist in data.get("data", []):
        # Match name case-insensitively (Deezer may return slight variations)
        if artist.get("name", "").lower() == name.lower():
            return {"id": artist["id"], "name": artist["name"]}
    # Fallback: use first result if it looks close enough
    results = data.get("data", [])
    if results:
        return {"id": results[0]["id"], "name": results[0]["name"]}
    logger.warning("Could not resolve artist: %s", name)
    return None


def resolve_seed_artists(names: list[str]) -> list[dict]:
    """Resolve all seed artist names to {id, name} dicts via Deezer search."""
    artists = []
    for name in names:
        result = resolve_artist_id(name)
        if result:
            logger.info("Resolved: %s → id=%d (%s)", name, result["id"], result["name"])
            artists.append(result)
        else:
            logger.warning("Skipping unresolved artist: %s", name)
    logger.info("Resolved %d/%d seed artists", len(artists), len(names))
    return artists

# ---------------------------------------------------------------------------
# Genre mapping for Deezer genre IDs
# ---------------------------------------------------------------------------

DEEZER_GENRE_MAP: dict[int, str] = {
    106: "Electronic",
    113: "Dance",
    129: "House",
    153: "Techno",
    85: "Electro",
    169: "Soul & Funk",  # borderline, include
    197: "Chill",
}

# Genre IDs considered "Electronic-adjacent" for filtering related artists
ELECTRONIC_GENRE_IDS: set[int] = {106, 113, 129, 153, 85, 169, 197}


def map_deezer_genre(genre_id: int | None) -> str:
    """Map Deezer genre_id to internal Beattrack genre."""
    if genre_id and genre_id in DEEZER_GENRE_MAP:
        return DEEZER_GENRE_MAP[genre_id]
    return "Electronic"


def is_electronic_artist(artist_id: int) -> bool:
    """Check if an artist is Electronic by looking at their top track's album genre.

    Makes 1-2 API calls: top track → album details. Results are cached implicitly
    by the caller (seen_artist_ids set prevents re-checking).
    """
    time.sleep(API_DELAY)
    data = deezer_get(f"/artist/{artist_id}/top?limit=1")
    if not data or not isinstance(data, dict):
        return False
    tracks = data.get("data", [])
    if not tracks:
        return False
    album_id = tracks[0].get("album", {}).get("id")
    if not album_id:
        return False
    time.sleep(API_DELAY)
    album = deezer_get(f"/album/{album_id}")
    if not album or not isinstance(album, dict):
        return False
    genre_id = album.get("genre_id", 0)
    genres = album.get("genres", {}).get("data", [])
    genre_ids = {genre_id} | {g.get("id", 0) for g in genres}
    return bool(genre_ids & ELECTRONIC_GENRE_IDS)


# ---------------------------------------------------------------------------
# Track discovery
# ---------------------------------------------------------------------------


def crawl_tracks(
    seed_artists: list[dict],
    related_depth: int = 1,
    top_limit: int = 50,
    related_limit: int = 20,
) -> list[dict]:
    """Crawl Deezer for tracks starting from seed artists.

    For each seed artist:
    1. Fetch top tracks (up to top_limit)
    2. Fetch related artists (up to related_limit)
    3. Fetch top tracks for each related artist

    Returns deduplicated list of track dicts.
    """
    seen_track_ids: set[int] = set()
    seen_artist_ids: set[int] = set()
    seed_ids: set[int] = {a["id"] for a in seed_artists}  # never skip seeds
    skipped_related: set[int] = set()  # non-electronic related artists
    tracks: list[dict] = []

    def process_artist(artist_id: int, artist_name: str, depth: int = 0) -> None:
        if artist_id in seen_artist_ids:
            return
        seen_artist_ids.add(artist_id)

        logger.info("Crawling artist: %s (id=%d, depth=%d)", artist_name, artist_id, depth)

        # Fetch top tracks
        top_tracks = deezer_get_all(f"/artist/{artist_id}/top?limit={top_limit}", limit=top_limit)
        new_count = 0
        for t in top_tracks:
            tid = t.get("id")
            if not tid or tid in seen_track_ids:
                continue
            preview = t.get("preview")
            if not preview:
                continue
            seen_track_ids.add(tid)
            new_count += 1
            tracks.append({
                "deezer_id": tid,
                "title": t.get("title", ""),
                "artist": artist_name,
                "artist_id": artist_id,
                "album": t.get("album", {}).get("title", ""),
                "duration": t.get("duration", 0),
                "preview_url": preview,
                "release_year": None,  # filled from album if available
                "genre_id": None,
            })
        logger.info("  Found %d new tracks (total: %d)", new_count, len(tracks))

        # Fetch related artists and recurse (with genre filter)
        if depth < related_depth:
            time.sleep(API_DELAY)
            related = deezer_get_all(
                f"/artist/{artist_id}/related?limit={related_limit}",
                limit=related_limit,
            )
            for r in related:
                rid = r.get("id")
                rname = r.get("name", f"Artist {rid}")
                if rid and rid not in seen_artist_ids and rid not in skipped_related:
                    # Genre-check related artists to prevent drift
                    if is_electronic_artist(rid):
                        process_artist(rid, rname, depth + 1)
                    else:
                        # Mark as skipped (not seen — seeds must still be processed)
                        skipped_related.add(rid)
                        logger.debug("Skipping non-electronic related: %s (id=%d)", rname, rid)

    for artist in seed_artists:
        process_artist(artist["id"], artist["name"], depth=0)

    logger.info(
        "Crawl complete: %d unique tracks from %d artists",
        len(tracks),
        len(seen_artist_ids),
    )
    return tracks


def enrich_tracks(tracks: list[dict]) -> list[dict]:
    """Fetch album details for release_year and genre where missing."""
    album_cache: dict[int, dict] = {}
    enriched = 0

    for t in tracks:
        # We can get release year from the track's album
        # Skip if already has release_year
        if t.get("release_year"):
            continue

        # Try to get album info (batch-friendly: cache by album)
        album_id = None
        # The track data from /artist/top doesn't always include full album info
        # We'll skip enrichment for now and use what we have
        # This keeps API calls low

    logger.info("Enriched %d tracks with album metadata", enriched)
    return tracks


# ---------------------------------------------------------------------------
# Preview download + extraction
# ---------------------------------------------------------------------------


def download_preview(url: str, dest: str) -> bool:
    """Download a 30s preview MP3 from Deezer CDN."""
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to download preview: %s — %s", url, exc)
        return False


def run_extract(audio_path: str) -> dict:
    """Call extract.py as a subprocess and parse its JSON output."""
    import subprocess

    result = subprocess.run(
        [sys.executable, str(EXTRACT_SCRIPT), audio_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr_tail = result.stderr.strip().splitlines()
        last_lines = "\n".join(stderr_tail[-5:]) if stderr_tail else "(no stderr)"
        raise RuntimeError(
            f"extract.py exited {result.returncode} for '{audio_path}':\n{last_lines}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"extract.py produced non-JSON stdout for '{audio_path}': {exc}"
        ) from exc


def _fetch_fresh_preview_url(deezer_id: str) -> str | None:
    """Fetch a fresh (non-expired) preview URL from Deezer track endpoint."""
    try:
        url = f"{DEEZER_API}/track/{deezer_id}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("preview") or None
    except Exception:  # noqa: BLE001
        return None


def _worker_extract(args: tuple[str, str, str]) -> tuple[str, dict | None, str | None]:
    """Download preview, extract features, delete preview.

    args: (track_key, preview_url, temp_dir)
    Returns: (track_key, features_or_None, error_or_None)
    """
    track_key, preview_url, temp_dir = args
    preview_path = os.path.join(temp_dir, f"{track_key}.mp3")

    try:
        # Fetch fresh preview URL (cached URLs expire due to HMAC signing)
        fresh_url = _fetch_fresh_preview_url(track_key)
        if fresh_url:
            preview_url = fresh_url

        # Download
        if not download_preview(preview_url, preview_path):
            return track_key, None, "Download failed"

        # Extract
        features = run_extract(preview_path)
        return track_key, features, None

    except Exception as exc:  # noqa: BLE001
        return track_key, None, str(exc)
    finally:
        # Always clean up the preview file
        try:
            os.unlink(preview_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Row building
# ---------------------------------------------------------------------------


def build_row(track: dict, features: dict) -> dict:
    """Build a songs table row from Deezer metadata and extracted features."""
    return {
        "_tid": str(track["deezer_id"]),
        "title": track.get("title", "Unknown"),
        "artist": track.get("artist", "Unknown"),
        "album": track.get("album") or None,
        "duration_sec": features.get("duration") or track.get("duration"),
        "bpm": features.get("bpm"),
        "musical_key": features.get("key", "Unknown"),
        "learned_embedding": str(features["learned"]),
        "handcrafted_raw": str(features["handcrafted"]),
        "source": "deezer",
        "embedding_type": "real",
        "metadata_status": "complete",
        "genre": map_deezer_genre(track.get("genre_id")),
        "release_year": track.get("release_year"),
    }


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, encoding="utf-8") as f:
                data = json.load(f)
            logger.info(
                "Resumed checkpoint: %d processed, %d failed",
                len(data.get("processed", [])),
                len(data.get("failed", [])),
            )
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read checkpoint: %s — starting fresh", exc)
    return {"processed": [], "failed": [], "last_batch": None}


def save_checkpoint(checkpoint: dict) -> None:
    tmp = CHECKPOINT_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f)
    tmp.replace(CHECKPOINT_FILE)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl Deezer for Electronic tracks and extract audio features."
    )
    parser.add_argument(
        "--limit-artists",
        type=int,
        default=None,
        help="Only use the first N seed artists (for testing)",
    )
    parser.add_argument(
        "--related-depth",
        type=int,
        default=1,
        help="How deep to follow related artists (default: 1)",
    )
    parser.add_argument(
        "--top-limit",
        type=int,
        default=50,
        help="Max top tracks per artist (default: 50)",
    )
    parser.add_argument(
        "--related-limit",
        type=int,
        default=20,
        help="Max related artists per seed (default: 20)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel extraction workers (default: 4)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Rows per JSONL flush and checkpoint save (default: 100)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSONL file (default: deezer_features.jsonl)",
    )
    parser.add_argument(
        "--crawl-only",
        action="store_true",
        help="Only crawl tracks (no extraction), save track list as JSON",
    )
    parser.add_argument(
        "--tracks-json",
        default=None,
        help="Use cached track list from JSON file (skip crawl phase)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not EXTRACT_SCRIPT.exists():
        logger.error("Extract script not found at '%s'", EXTRACT_SCRIPT)
        sys.exit(1)

    # --- Resolve seed artist IDs via Deezer search ---
    names = SEED_ARTIST_NAMES
    if args.limit_artists:
        names = names[: args.limit_artists]
    logger.info("Resolving %d seed artists via Deezer search...", len(names))
    seeds = resolve_seed_artists(names)
    if not seeds:
        logger.error("Could not resolve any seed artists. Exiting.")
        sys.exit(1)
    logger.info("Using %d seed artists", len(seeds))

    # --- Load or crawl tracks ---
    tracks_cache = SCRIPT_DIR / "deezer_tracks.json"
    if args.tracks_json:
        tracks_cache = Path(args.tracks_json)

    if args.tracks_json or (args.resume and tracks_cache.exists()):
        with open(tracks_cache, encoding="utf-8") as f:
            tracks = json.load(f)
        logger.info("Loaded %d cached tracks from '%s'", len(tracks), tracks_cache)
    else:
        logger.info("Starting Deezer crawl (related_depth=%d)...", args.related_depth)
        tracks = crawl_tracks(
            seeds,
            related_depth=args.related_depth,
            top_limit=args.top_limit,
            related_limit=args.related_limit,
        )
        if not tracks:
            logger.error("No tracks found. Exiting.")
            sys.exit(1)
        # Always cache the track list for resume
        with open(tracks_cache, "w", encoding="utf-8") as f:
            json.dump(tracks, f, ensure_ascii=False)
        logger.info("Cached %d tracks to '%s'", len(tracks), tracks_cache)

    # --- Crawl-only mode ---
    if args.crawl_only:
        logger.info("Crawl-only mode: %d tracks saved. Exiting.", len(tracks))
        return

    # --- Checkpoint ---
    checkpoint = load_checkpoint() if args.resume else {"processed": [], "failed": [], "last_batch": None}
    already_processed: set[str] = set(checkpoint.get("processed", []))
    already_failed: set[str] = set(checkpoint.get("failed", []))

    # Filter out already-processed tracks
    work_items = [t for t in tracks if str(t["deezer_id"]) not in already_processed]
    if args.resume:
        logger.info(
            "Skipping %d already-processed; %d remaining",
            len(tracks) - len(work_items),
            len(work_items),
        )

    total_tracks = len(work_items)
    if total_tracks == 0:
        logger.info("All tracks already processed. Nothing to do.")
        return

    # --- Output file ---
    output_jsonl = Path(args.output) if args.output else DEFAULT_OUTPUT
    logger.info("Features will be saved to '%s'", output_jsonl)
    logger.info(
        "Starting extraction of %d tracks with %d worker(s)...",
        total_tracks,
        args.workers,
    )

    # --- Create temp dir for preview downloads ---
    temp_dir = tempfile.mkdtemp(prefix="beattrack_deezer_")
    logger.info("Temp directory for previews: %s", temp_dir)

    # --- Processing loop ---
    success_count = 0
    fail_count = 0
    pending_rows: list[dict] = []
    batch_number = checkpoint.get("last_batch") or 0
    track_lookup = {str(t["deezer_id"]): t for t in work_items}

    jsonl_file = open(output_jsonl, "a", encoding="utf-8")

    try:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            future_to_key = {}
            for t in work_items:
                key = str(t["deezer_id"])
                future = executor.submit(
                    _worker_extract,
                    (key, t["preview_url"], temp_dir),
                )
                future_to_key[future] = key

            completed = 0
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                completed += 1

                try:
                    result_key, features, error = future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Worker exception for %s: %s", key, exc)
                    already_failed.add(key)
                    fail_count += 1
                    continue

                if features is None:
                    logger.warning("Extraction failed for %s: %s", key, error)
                    already_failed.add(key)
                    fail_count += 1
                else:
                    track_meta = track_lookup[key]
                    row = build_row(track_meta, features)
                    pending_rows.append(row)
                    already_processed.add(key)
                    success_count += 1

                # Log progress
                if completed % 50 == 0 or completed == total_tracks:
                    logger.info(
                        "Progress: %d/%d (success=%d, fail=%d)",
                        completed,
                        total_tracks,
                        success_count,
                        fail_count,
                    )

                # Flush batch
                if len(pending_rows) >= args.batch_size:
                    batch_number += 1
                    for r in pending_rows:
                        jsonl_file.write(json.dumps(r, ensure_ascii=False) + "\n")
                    jsonl_file.flush()
                    logger.info("  Wrote batch %d (%d rows)", batch_number, len(pending_rows))
                    pending_rows.clear()

                    checkpoint["processed"] = sorted(already_processed)
                    checkpoint["failed"] = sorted(already_failed)
                    checkpoint["last_batch"] = batch_number
                    save_checkpoint(checkpoint)

        # Flush remaining
        if pending_rows:
            batch_number += 1
            for r in pending_rows:
                jsonl_file.write(json.dumps(r, ensure_ascii=False) + "\n")
            jsonl_file.flush()
            logger.info("  Wrote final batch %d (%d rows)", batch_number, len(pending_rows))
            pending_rows.clear()
    finally:
        jsonl_file.close()
        # Clean up temp dir
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass

    # Final checkpoint
    checkpoint["processed"] = sorted(already_processed)
    checkpoint["failed"] = sorted(already_failed)
    checkpoint["last_batch"] = batch_number
    save_checkpoint(checkpoint)

    logger.info(
        "\nDone! %d tracks succeeded, %d failed. Output: '%s'",
        success_count,
        fail_count,
        output_jsonl,
    )


if __name__ == "__main__":
    main()
