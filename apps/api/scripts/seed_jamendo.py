"""Batch-extract features from MTG-Jamendo audio files and output JSONL.

Uses the same Essentia MusiCNN pipeline as seed_fma.py but reads metadata
from MTG-Jamendo TSV files instead of FMA CSV.

Usage:
    python apps/api/scripts/seed_jamendo.py \
        --audio-dir data/mtg-jamendo-audio \
        --metadata-tsv data/mtg-jamendo-dataset/data/raw.meta.tsv \
        --genre-tsv data/mtg-jamendo-dataset/data/autotagging_genre.tsv \
        --workers 4

    # Extract-only (default) — saves to JSONL for later import:
    python apps/api/scripts/seed_jamendo.py ... --output jamendo_features.jsonl

    # Resume after a crash:
    python apps/api/scripts/seed_jamendo.py ... --resume

    # Quick test with 10 tracks:
    python apps/api/scripts/seed_jamendo.py ... --limit 10

Checkpoint file: seed_jamendo_checkpoint.json (in this script's directory)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
EXTRACT_SCRIPT = SCRIPT_DIR.parent / "app" / "workers" / "extract.py"
CHECKPOINT_FILE = SCRIPT_DIR / "seed_jamendo_checkpoint.json"

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
# Genre mapping: Jamendo tags → internal Beattrack genres
# ---------------------------------------------------------------------------

# Priority order matters: more specific tags first.
# First matching tag wins for a given track.
GENRE_MAP: dict[str, str] = {
    "techno": "Techno",
    "house": "House",
    "deephouse": "House",
    "trance": "Trance",
    "drumnbass": "Drum & Bass",
    "dubstep": "Dubstep",
    "idm": "IDM",
    "minimal": "Minimal Electronic",
    "breakbeat": "Breakbeat",
    "downtempo": "Downtempo",
    "chillout": "Chill-out",
    "ambient": "Ambient",
    "darkambient": "Ambient",
    "dance": "Dance",
    "club": "Dance",
    "eurodance": "Dance",
    "edm": "Electronic",
    "electronica": "Electronic",
    "electropop": "Electronic",
    "synthpop": "Electronic",
    "darkwave": "Electronic",
    "industrial": "Electronic",
    "electronic": "Electronic",
}

# Tags that qualify a track as "electronic-related"
ELECTRONIC_TAGS = set(GENRE_MAP.keys())


# ---------------------------------------------------------------------------
# Metadata loading
# ---------------------------------------------------------------------------


def load_genre_tags(tsv_path: str) -> dict[str, dict]:
    """Load autotagging_genre.tsv → dict keyed by track_id.

    Returns:
        {track_id: {"path": "14/214.mp3", "duration": 124.6, "tags": ["electronic", "ambient"]}}
    """
    tracks: dict[str, dict] = {}
    with open(tsv_path, encoding="utf-8") as f:
        header = f.readline()  # skip header
        if not header.startswith("TRACK_ID"):
            logger.warning("Unexpected header in genre TSV: %s", header.strip())

        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 6:
                continue

            track_id = parts[0]
            audio_path = parts[3]
            try:
                duration = float(parts[4])
            except ValueError:
                duration = 0.0

            # Parse genre tags: "genre---electronic\tgenre---ambient" → ["electronic", "ambient"]
            raw_tags = parts[5:]
            tags = []
            for tag in raw_tags:
                tag = tag.strip()
                if tag.startswith("genre---"):
                    tags.append(tag[len("genre---"):])

            tracks[track_id] = {
                "path": audio_path,
                "duration": duration,
                "tags": tags,
            }

    return tracks


def load_metadata(tsv_path: str) -> dict[str, dict]:
    """Load raw.meta.tsv → dict keyed by track_id.

    Returns:
        {track_id: {"title": "...", "artist": "...", "album": "...", "release_year": 2004}}
    """
    tracks: dict[str, dict] = {}
    with open(tsv_path, encoding="utf-8") as f:
        header = f.readline()
        if not header.startswith("TRACK_ID"):
            logger.warning("Unexpected header in metadata TSV: %s", header.strip())

        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 7:
                continue

            track_id = parts[0]
            title = parts[3]
            artist = parts[4]
            album = parts[5]

            # Parse release year from date like "2004-12-28"
            release_year = None
            date_str = parts[6] if len(parts) > 6 else ""
            if date_str and "-" in date_str:
                try:
                    release_year = int(date_str.split("-")[0])
                except ValueError:
                    pass

            tracks[track_id] = {
                "title": title,
                "artist": artist,
                "album": album,
                "release_year": release_year,
            }

    return tracks


def map_genre(tags: list[str]) -> str | None:
    """Map Jamendo genre tags to internal Beattrack genre.

    Returns the most specific matching genre, or None if no match.
    """
    for tag in tags:
        if tag in GENRE_MAP:
            return GENRE_MAP[tag]
    return None


def filter_electronic(
    genre_data: dict[str, dict],
    min_year: int | None = None,
    meta: dict[str, dict] | None = None,
) -> dict[str, dict]:
    """Filter tracks that have at least one electronic-related tag.

    Returns filtered genre_data dict with added 'genre' field.
    """
    filtered: dict[str, dict] = {}
    skipped_genre = 0
    skipped_year = 0

    for track_id, info in genre_data.items():
        tags = info.get("tags", [])

        # Must have at least one electronic-related tag
        if not any(t in ELECTRONIC_TAGS for t in tags):
            skipped_genre += 1
            continue

        # Year filter
        if min_year and meta and track_id in meta:
            year = meta[track_id].get("release_year")
            if year and year < min_year:
                skipped_year += 1
                continue

        info["genre"] = map_genre(tags)
        filtered[track_id] = info

    logger.info("  Skipped %d tracks (no electronic tag)", skipped_genre)
    if min_year:
        logger.info("  Skipped %d tracks (year < %d)", skipped_year, min_year)

    return filtered


# ---------------------------------------------------------------------------
# Checkpoint helpers
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
# Extraction (reuses extract.py subprocess)
# ---------------------------------------------------------------------------


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


def _worker_extract(args: tuple[str, str]) -> tuple[str, dict | None, str | None]:
    """Top-level function for ProcessPoolExecutor.

    Returns (track_id, features_dict_or_None, error_message_or_None).
    """
    track_id, audio_path = args
    try:
        features = run_extract(audio_path)
        return track_id, features, None
    except Exception as exc:  # noqa: BLE001
        return track_id, None, str(exc)


# ---------------------------------------------------------------------------
# Row building
# ---------------------------------------------------------------------------


def build_row(track_id: str, meta: dict, genre_info: dict, features: dict) -> dict:
    """Build a songs table row dict from metadata and extracted features."""
    title = meta.get("title") or f"Jamendo {track_id}"
    artist = meta.get("artist") or "Unknown"
    album = meta.get("album") or None
    has_title = bool(meta.get("title"))

    # Prefer duration from extraction; fall back to TSV duration
    duration = features.get("duration") or genre_info.get("duration") or None

    return {
        "_track_id": track_id,  # internal — stripped before import
        "title": title,
        "artist": artist,
        "album": album,
        "duration_sec": duration,
        "bpm": features.get("bpm"),
        "musical_key": features.get("key", "Unknown"),
        "learned_embedding": str(features["learned"]),
        "handcrafted_raw": str(features["handcrafted"]),
        "source": "jamendo",
        "embedding_type": "real",
        "metadata_status": "complete" if has_title else "partial",
        "genre": genre_info.get("genre", "Electronic"),
        "release_year": meta.get("release_year"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract MTG-Jamendo audio features and save to JSONL."
    )
    parser.add_argument(
        "--audio-dir",
        required=True,
        help="Path to extracted MTG-Jamendo audio directory",
    )
    parser.add_argument(
        "--metadata-tsv",
        required=True,
        help="Path to raw.meta.tsv",
    )
    parser.add_argument(
        "--genre-tsv",
        required=True,
        help="Path to autotagging_genre.tsv",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=0,
        help="Only include tracks from this year onwards (default: 0 = no filter)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Rows to write per JSONL flush (default: 100)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from seed_jamendo_checkpoint.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only N tracks (useful for testing)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel extraction workers (default: 1)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSONL file path (default: jamendo_features.jsonl in script dir)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # --- Validate paths ---
    audio_dir = Path(args.audio_dir).resolve()
    if not audio_dir.is_dir():
        logger.error("--audio-dir '%s' is not a directory", audio_dir)
        sys.exit(1)

    metadata_tsv = Path(args.metadata_tsv).resolve()
    if not metadata_tsv.is_file():
        logger.error("--metadata-tsv '%s' not found", metadata_tsv)
        sys.exit(1)

    genre_tsv = Path(args.genre_tsv).resolve()
    if not genre_tsv.is_file():
        logger.error("--genre-tsv '%s' not found", genre_tsv)
        sys.exit(1)

    if not EXTRACT_SCRIPT.exists():
        logger.error("Extract script not found at '%s'", EXTRACT_SCRIPT)
        sys.exit(1)

    # --- Load metadata ---
    logger.info("Loading metadata from '%s'...", metadata_tsv)
    meta = load_metadata(str(metadata_tsv))
    logger.info("  %d tracks in metadata", len(meta))

    logger.info("Loading genre tags from '%s'...", genre_tsv)
    genre_data = load_genre_tags(str(genre_tsv))
    logger.info("  %d tracks in genre file", len(genre_data))

    # --- Filter for electronic tracks ---
    min_year = args.min_year if args.min_year > 0 else None
    logger.info("Filtering for electronic-related tracks...")
    electronic = filter_electronic(genre_data, min_year=min_year, meta=meta)
    logger.info("  %d electronic tracks after filtering", len(electronic))

    # --- Discover audio files ---
    logger.info("Matching audio files in '%s'...", audio_dir)
    work_items: list[tuple[str, str]] = []
    missing_audio = 0

    for track_id, info in sorted(electronic.items()):
        tsv_path = info["path"]  # e.g. "14/214.mp3"
        # Try both naming conventions:
        # 1. Original: 14/214.mp3
        # 2. Low-quality variant: 14/214.low.mp3
        audio_path = audio_dir / tsv_path
        if not audio_path.is_file():
            low_path = audio_dir / tsv_path.replace(".mp3", ".low.mp3")
            if low_path.is_file():
                audio_path = low_path
            else:
                missing_audio += 1
                continue
        work_items.append((track_id, str(audio_path)))

    logger.info(
        "  %d tracks with audio found, %d missing",
        len(work_items),
        missing_audio,
    )

    # --- Checkpoint ---
    checkpoint = load_checkpoint() if args.resume else {"processed": [], "failed": [], "last_batch": None}
    already_processed: set[str] = set(checkpoint.get("processed", []))
    already_failed: set[str] = set(checkpoint.get("failed", []))

    if args.resume:
        before = len(work_items)
        work_items = [(tid, p) for tid, p in work_items if tid not in already_processed]
        logger.info(
            "  Skipping %d already-processed; %d remaining",
            before - len(work_items),
            len(work_items),
        )

    # --- Apply --limit ---
    if args.limit is not None:
        work_items = work_items[: args.limit]
        logger.info("  Limited to %d tracks (--limit)", len(work_items))

    total_tracks = len(work_items)
    if total_tracks == 0:
        logger.info("Nothing to process. Exiting.")
        return

    # --- Output file ---
    output_jsonl = Path(args.output) if args.output else SCRIPT_DIR / "jamendo_features.jsonl"
    logger.info("Features will be saved to '%s'", output_jsonl)

    # --- Processing loop ---
    success_count = 0
    fail_count = 0
    pending_rows: list[dict] = []
    batch_number = checkpoint.get("last_batch") or 0

    logger.info(
        "Starting extraction of %d tracks with %d worker(s)...",
        total_tracks,
        args.workers,
    )

    jsonl_file = open(output_jsonl, "a", encoding="utf-8")

    try:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            future_to_tid = {
                executor.submit(_worker_extract, item): item[0] for item in work_items
            }

            completed = 0
            for future in as_completed(future_to_tid):
                tid = future_to_tid[future]
                completed += 1

                try:
                    result_tid, features, error = future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Worker exception for %s: %s", tid, exc)
                    already_failed.add(tid)
                    fail_count += 1
                    continue

                if features is None:
                    logger.warning("Extraction failed for %s: %s", tid, error)
                    already_failed.add(tid)
                    fail_count += 1
                else:
                    track_meta = meta.get(tid, {})
                    genre_info = electronic.get(tid, {})
                    row = build_row(tid, track_meta, genre_info, features)
                    pending_rows.append(row)
                    already_processed.add(tid)
                    success_count += 1

                # Log progress every 100 tracks
                if completed % 100 == 0 or completed == total_tracks:
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

        # Flush remaining rows
        if pending_rows:
            batch_number += 1
            for r in pending_rows:
                jsonl_file.write(json.dumps(r, ensure_ascii=False) + "\n")
            jsonl_file.flush()
            logger.info("  Wrote final batch %d (%d rows)", batch_number, len(pending_rows))
            pending_rows.clear()
    finally:
        jsonl_file.close()

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
