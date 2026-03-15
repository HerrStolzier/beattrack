"""Tag existing FMA songs with genre + release_year, then remove non-matching songs.

Usage:
    export SUPABASE_URL=https://xxx.supabase.co
    export SUPABASE_SERVICE_ROLE_KEY=eyJ...

    # Dry run (default) — shows what would be deleted:
    python apps/api/scripts/cleanup_genres.py \\
        --metadata-csv phase0/data/raw_tracks.csv \\
        --genres-csv phase0/data/fma_metadata/genres.csv

    # Actually delete:
    python apps/api/scripts/cleanup_genres.py \\
        --metadata-csv phase0/data/raw_tracks.csv \\
        --genres-csv phase0/data/fma_metadata/genres.csv \\
        --execute
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from supabase import create_client

# Re-use helpers from seed_fma
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from seed_fma import load_genre_hierarchy, load_metadata  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tag songs with genre and remove non-matching.")
    parser.add_argument("--metadata-csv", required=True, help="Path to raw_tracks.csv")
    parser.add_argument("--genres-csv", required=True, help="Path to FMA genres.csv")
    parser.add_argument(
        "--keep-genres",
        nargs="+",
        default=["Electronic"],
        help="Top-level genres to keep (default: Electronic)",
    )
    parser.add_argument(
        "--exclude-genres",
        nargs="+",
        default=["Trip-Hop", "Skweee", "Chiptune", "Chip Music", "Breakcore - Hard", "Ambient Electronic"],
        help="Sub-genres to exclude even if top-level matches.",
    )
    parser.add_argument("--min-year", type=int, default=2000, help="Min release year (default: 2000)")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete songs. Without this flag, only shows what would happen.",
    )
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars")
        sys.exit(1)

    supabase = create_client(url, key)

    # Load genre hierarchy
    genre_hierarchy = load_genre_hierarchy(args.genres_csv)
    logger.info("Loaded %d genre mappings", len(genre_hierarchy))

    # Load ALL metadata (no filtering) to get genre info for existing tracks
    all_metadata = load_metadata(args.metadata_csv, genre_hierarchy=genre_hierarchy)
    logger.info("Loaded metadata for %d tracks", len(all_metadata))

    # Build sub-genre lookup for exclude filter
    excluded_subs = set(args.exclude_genres) if args.exclude_genres else set()
    sub_genre_map: dict[int, str | None] = {}  # tid → first sub-genre title
    if excluded_subs:
        import ast as _ast
        import csv as _csv

        with open(args.metadata_csv, encoding="utf-8", newline="") as f:
            reader = _csv.DictReader(f)
            for row in reader:
                raw_id = row.get("track_id", "").strip()
                if not raw_id:
                    continue
                try:
                    tid = int(raw_id)
                except ValueError:
                    continue
                genres_str = row.get("track_genres", "")
                if genres_str:
                    try:
                        genres = _ast.literal_eval(genres_str)
                        for g in genres:
                            gt = g.get("genre_title", "")
                            if gt in genre_hierarchy:
                                sub_genre_map[tid] = gt
                                break
                    except (ValueError, SyntaxError):
                        pass

    # Fetch all song titles from DB to match with FMA track_ids
    # FMA songs have title pattern "FMA Track {tid}" for untitled, or the actual title
    logger.info("Fetching existing songs from DB...")
    result = supabase.table("songs").select("id, title, source").eq("source", "fma").execute()
    db_songs = result.data
    logger.info("Found %d FMA songs in DB", len(db_songs))

    # Build title→track_id mapping from metadata for matching
    # The seed script uses title from CSV, so we can match on title
    title_artist_to_tid: dict[str, int] = {}
    for tid, meta in all_metadata.items():
        title = meta.get("track_title") or f"FMA Track {tid}"
        artist = meta.get("artist_name") or "Unknown"
        key_str = f"{title}|||{artist}"
        title_artist_to_tid[key_str] = tid

    # Classify each DB song
    keep_genres = set(args.keep_genres)
    to_keep: list[dict] = []
    to_delete: list[dict] = []
    unmatched: list[dict] = []

    for song in db_songs:
        # Try to find the FMA track_id for this song
        matched_tid = None
        matched_meta = None

        # Try matching via title pattern "FMA Track {tid}"
        if song["title"].startswith("FMA Track "):
            try:
                matched_tid = int(song["title"].split("FMA Track ")[1])
                matched_meta = all_metadata.get(matched_tid)
            except (ValueError, IndexError):
                pass

        # Try matching all metadata entries by title
        if not matched_meta:
            for tid, meta in all_metadata.items():
                title = meta.get("track_title") or f"FMA Track {tid}"
                if title == song["title"]:
                    matched_tid = tid
                    matched_meta = meta
                    break

        if not matched_meta:
            unmatched.append(song)
            continue

        genre = matched_meta.get("genre")
        year = matched_meta.get("release_year")
        sub = sub_genre_map.get(matched_tid)

        genre_ok = genre in keep_genres
        not_excluded = sub not in excluded_subs
        year_ok = not args.min_year or not year or year >= args.min_year

        if genre_ok and not_excluded and year_ok:
            to_keep.append({"song": song, "genre": genre, "year": year, "tid": matched_tid, "sub": sub})
        else:
            to_delete.append({"song": song, "genre": genre, "year": year, "tid": matched_tid, "sub": sub})

    logger.info("")
    logger.info("=== Results ===")
    logger.info("Keep:      %d songs (genre in %s, year >= %d)", len(to_keep), keep_genres, args.min_year)
    logger.info("Delete:    %d songs (wrong genre or year)", len(to_delete))
    logger.info("Unmatched: %d songs (no FMA metadata found — will be deleted)", len(unmatched))

    # Show genre breakdown of deletions
    delete_genres: dict[str, int] = {}
    for item in to_delete:
        g = item["genre"] or "Unknown"
        delete_genres[g] = delete_genres.get(g, 0) + 1
    logger.info("\nDeletion breakdown by genre:")
    for g, c in sorted(delete_genres.items(), key=lambda x: -x[1]):
        logger.info("  %s: %d", g, c)

    if not args.execute:
        logger.info("\n*** DRY RUN — no changes made. Use --execute to delete. ***")
        return

    # Tag kept songs with genre + release_year
    logger.info("\nTagging %d kept songs with genre + release_year...", len(to_keep))
    for i, item in enumerate(to_keep):
        supabase.table("songs").update({
            "genre": item["genre"],
            "release_year": item["year"],
        }).eq("id", item["song"]["id"]).execute()
        if (i + 1) % 100 == 0:
            logger.info("  Tagged %d/%d", i + 1, len(to_keep))

    # Delete non-matching songs
    delete_ids = [item["song"]["id"] for item in to_delete] + [s["id"] for s in unmatched]
    if delete_ids:
        logger.info("Deleting %d songs...", len(delete_ids))
        # Delete in batches of 100
        for i in range(0, len(delete_ids), 100):
            batch = delete_ids[i : i + 100]
            supabase.table("songs").delete().in_("id", batch).execute()
            logger.info("  Deleted batch %d/%d", i // 100 + 1, (len(delete_ids) + 99) // 100)

    logger.info("Done! %d songs kept, %d deleted.", len(to_keep), len(delete_ids))


if __name__ == "__main__":
    main()
