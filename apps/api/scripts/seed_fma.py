"""Batch-extract features from FMA audio files and insert into Supabase.

Usage:
    export SUPABASE_URL=https://xxx.supabase.co
    export SUPABASE_SERVICE_ROLE_KEY=eyJ...

    python apps/api/scripts/seed_fma.py \\
        --fma-dir phase0/data/fma_medium \\
        --metadata-csv phase0/data/raw_tracks.csv \\
        --batch-size 100 \\
        --workers 4

    # Resume after a crash:
    python apps/api/scripts/seed_fma.py ... --resume

    # Quick test with 10 tracks:
    python apps/api/scripts/seed_fma.py ... --limit 10

Checkpoint file: seed_checkpoint.json (in this script's directory)
    {"processed": [2, 5, 10, ...], "failed": [7, 15, ...], "last_batch": 1500}

Extract subprocess: apps/api/app/workers/extract.py
    Receives one positional arg (audio path), writes JSON to stdout.
    Exit 0 = success; any other exit = failure.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from supabase import create_client

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
EXTRACT_SCRIPT = SCRIPT_DIR.parent / "app" / "workers" / "extract.py"
CHECKPOINT_FILE = SCRIPT_DIR / "seed_checkpoint.json"

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
# Metadata helpers
# ---------------------------------------------------------------------------


def parse_duration(duration_str: str) -> float | None:
    """Convert 'MM:SS' or 'HH:MM:SS' to seconds (float). Returns None on failure."""
    if not duration_str:
        return None
    parts = duration_str.strip().split(":")
    try:
        if len(parts) == 2:
            return float(int(parts[0]) * 60 + int(parts[1]))
        if len(parts) == 3:
            return float(int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))
    except ValueError:
        return None
    return None


def load_metadata(csv_path: str) -> dict[int, dict]:
    """Load track metadata from raw_tracks.csv → dict keyed by integer track_id."""
    tracks: dict[int, dict] = {}
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_id = row.get("track_id", "").strip()
            if not raw_id:
                continue
            try:
                tid = int(raw_id)
            except ValueError:
                continue
            tracks[tid] = {
                "track_title": row.get("track_title", "").strip(),
                "artist_name": row.get("artist_name", "").strip(),
                "album_title": row.get("album_title", "").strip(),
                "track_duration": row.get("track_duration", "").strip(),
            }
    return tracks


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------


def load_checkpoint() -> dict:
    """Load checkpoint from disk. Returns empty structure if not found."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, encoding="utf-8") as f:
                data = json.load(f)
            logger.info(
                "Resumed checkpoint: %d processed, %d failed, last_batch=%s",
                len(data.get("processed", [])),
                len(data.get("failed", [])),
                data.get("last_batch"),
            )
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read checkpoint file: %s — starting fresh", exc)
    return {"processed": [], "failed": [], "last_batch": None}


def save_checkpoint(checkpoint: dict) -> None:
    """Persist checkpoint to disk atomically."""
    tmp = CHECKPOINT_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f)
    tmp.replace(CHECKPOINT_FILE)


# ---------------------------------------------------------------------------
# Extraction worker (runs in a subprocess)
# ---------------------------------------------------------------------------


def run_extract(audio_path: str) -> dict:
    """Call extract.py as a subprocess and parse its JSON output.

    Returns the parsed feature dict on success.
    Raises RuntimeError on any failure.
    """
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


def _worker_extract(args: tuple[int, str]) -> tuple[int, dict | None, str | None]:
    """Top-level function for ProcessPoolExecutor (must be picklable).

    Returns (track_id, features_dict_or_None, error_message_or_None).
    """
    tid, audio_path = args
    try:
        features = run_extract(audio_path)
        return tid, features, None
    except Exception as exc:  # noqa: BLE001
        return tid, None, str(exc)


# ---------------------------------------------------------------------------
# DB insert
# ---------------------------------------------------------------------------


def build_row(tid: int, meta: dict, features: dict) -> dict:
    """Build a songs table row dict from metadata and extracted features."""
    title = meta.get("track_title") or f"FMA Track {tid}"
    artist = meta.get("artist_name") or "Unknown"
    album = meta.get("album_title") or None
    has_title = bool(meta.get("track_title"))

    # Prefer duration from extraction result; fall back to CSV
    duration = features.get("duration") or None
    if not duration:
        duration = parse_duration(meta.get("track_duration", ""))

    return {
        "_tid": tid,  # internal — stripped before DB insert
        "title": title,
        "artist": artist,
        "album": album,
        "duration_sec": duration,
        "bpm": features.get("bpm"),
        "musical_key": features.get("key", "Unknown"),
        "learned_embedding": str(features["learned"]),
        "handcrafted_raw": str(features["handcrafted"]),
        "handcrafted_norm": str(features["handcrafted"]),  # normalized later by compute_stats.py
        "source": "fma",
        "embedding_type": "real",
        "metadata_status": "complete" if has_title else "partial",
    }


def insert_batch(supabase, rows: list[dict]) -> None:
    """Insert a list of row dicts into the songs table.

    Strips internal '_tid' field before inserting.
    """
    clean_rows = [{k: v for k, v in r.items() if k != "_tid"} for r in rows]
    supabase.table("songs").insert(clean_rows).execute()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract FMA audio features and seed into Supabase songs table."
    )
    parser.add_argument(
        "--fma-dir",
        required=True,
        help="Path to FMA audio directory (e.g. phase0/data/fma_medium)",
    )
    parser.add_argument(
        "--metadata-csv",
        required=True,
        help="Path to raw_tracks.csv",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of rows to insert per DB batch (default: 100)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from seed_checkpoint.json, skipping already-processed tracks",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # --- Env vars ---
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars")
        sys.exit(1)

    # --- Validate paths ---
    fma_dir = Path(args.fma_dir).resolve()
    if not fma_dir.is_dir():
        logger.error("--fma-dir '%s' is not a directory", fma_dir)
        sys.exit(1)

    metadata_csv = Path(args.metadata_csv).resolve()
    if not metadata_csv.is_file():
        logger.error("--metadata-csv '%s' not found", metadata_csv)
        sys.exit(1)

    if not EXTRACT_SCRIPT.exists():
        logger.error("Extract script not found at '%s'", EXTRACT_SCRIPT)
        sys.exit(1)

    # --- Load metadata ---
    logger.info("Loading metadata from '%s'...", metadata_csv)
    metadata = load_metadata(str(metadata_csv))
    logger.info("  %d tracks with metadata", len(metadata))

    # --- Discover audio files ---
    logger.info("Scanning '%s' for .mp3 files...", fma_dir)
    mp3_files: list[tuple[int, Path]] = []
    for mp3_path in sorted(fma_dir.rglob("*.mp3")):
        stem = mp3_path.stem  # e.g. "000002"
        try:
            tid = int(stem)
        except ValueError:
            logger.warning("Skipping file with non-numeric stem: '%s'", mp3_path)
            continue
        mp3_files.append((tid, mp3_path))

    logger.info("  %d .mp3 files found", len(mp3_files))

    # --- Checkpoint ---
    checkpoint = load_checkpoint() if args.resume else {"processed": [], "failed": [], "last_batch": None}
    already_processed: set[int] = set(checkpoint.get("processed", []))
    already_failed: set[int] = set(checkpoint.get("failed", []))

    if args.resume:
        before = len(mp3_files)
        mp3_files = [(tid, p) for tid, p in mp3_files if tid not in already_processed]
        logger.info(
            "  Skipping %d already-processed tracks; %d remaining",
            before - len(mp3_files),
            len(mp3_files),
        )

    # --- Apply --limit ---
    if args.limit is not None:
        mp3_files = mp3_files[: args.limit]
        logger.info("  Limited to %d tracks (--limit)", len(mp3_files))

    total_tracks = len(mp3_files)
    if total_tracks == 0:
        logger.info("Nothing to process. Exiting.")
        return

    # --- Supabase client ---
    supabase = create_client(url, key)

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

    work_items = [(tid, str(mp3_path)) for tid, mp3_path in mp3_files]

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
                logger.warning("Worker raised unexpected exception for track %d: %s", tid, exc)
                already_failed.add(tid)
                fail_count += 1
                continue

            if features is None:
                logger.warning("Extraction failed for track %d: %s", tid, error)
                already_failed.add(tid)
                fail_count += 1
            else:
                meta = metadata.get(tid, {})
                row = build_row(tid, meta, features)
                pending_rows.append(row)
                already_processed.add(tid)
                success_count += 1

            # Log progress every 100 tracks
            if completed % 100 == 0 or completed == total_tracks:
                logger.info(
                    "Progress: %d/%d tracks processed (success=%d, fail=%d)",
                    completed,
                    total_tracks,
                    success_count,
                    fail_count,
                )

            # Flush batch when full
            if len(pending_rows) >= args.batch_size:
                batch_number += 1
                logger.info(
                    "Inserting batch %d (%d rows)...", batch_number, len(pending_rows)
                )
                try:
                    insert_batch(supabase, pending_rows)
                except Exception as exc:  # noqa: BLE001
                    failed_tids = [r["_tid"] for r in pending_rows]
                    logger.error(
                        "DB insert failed for batch %d: %s — %d rows lost",
                        batch_number,
                        exc,
                        len(pending_rows),
                    )
                    already_failed.update(failed_tids)
                    # Remove from processed since they didn't make it to DB
                    already_processed -= set(failed_tids)
                else:
                    logger.info("  Batch %d inserted OK", batch_number)

                pending_rows.clear()
                checkpoint["processed"] = sorted(already_processed)
                checkpoint["failed"] = sorted(already_failed)
                checkpoint["last_batch"] = batch_number
                save_checkpoint(checkpoint)

    # Flush any remaining rows
    if pending_rows:
        batch_number += 1
        logger.info(
            "Inserting final batch %d (%d rows)...", batch_number, len(pending_rows)
        )
        try:
            insert_batch(supabase, pending_rows)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "DB insert failed for final batch %d: %s — %d rows lost",
                batch_number,
                exc,
                len(pending_rows),
            )
        else:
            logger.info("  Final batch %d inserted OK", batch_number)

        pending_rows.clear()

    # Final checkpoint save
    checkpoint["processed"] = sorted(already_processed)
    checkpoint["failed"] = sorted(already_failed)
    checkpoint["last_batch"] = batch_number
    save_checkpoint(checkpoint)

    logger.info(
        "\nDone! %d tracks succeeded, %d failed. Checkpoint saved to '%s'.",
        success_count,
        fail_count,
        CHECKPOINT_FILE,
    )


if __name__ == "__main__":
    main()
