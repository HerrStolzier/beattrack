"""Import FMA embeddings + metadata into Supabase.

Usage:
    export SUPABASE_URL=https://xxx.supabase.co
    export SUPABASE_SERVICE_ROLE_KEY=eyJ...
    cd beattrack && uv run --with supabase --with numpy python scripts/import_fma.py

Reads:
    - phase0/embeddings/fma_small_embeddings.npy  (7996 tracks, learned + handcrafted)
    - phase0/data/fma_metadata.zip → raw_tracks.csv (title, artist, album, duration)

Writes:
    - songs table (embeddings + metadata)
    - config table (handcrafted normalization stats)
"""

import csv
import io
import os
import sys
import zipfile

import numpy as np
from supabase import create_client

EMBEDDINGS_PATH = "phase0/embeddings/fma_small_embeddings.npy"
METADATA_ZIP = "phase0/data/fma_metadata.zip"
BATCH_SIZE = 100


def parse_duration(duration_str: str) -> float | None:
    """Convert 'MM:SS' or 'HH:MM:SS' to seconds."""
    if not duration_str:
        return None
    parts = duration_str.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return None
    return None


def load_metadata(zip_path: str) -> dict[str, dict]:
    """Load track metadata from FMA zip → raw_tracks.csv."""
    tracks = {}
    with zipfile.ZipFile(zip_path) as z:
        with z.open("fma_metadata/raw_tracks.csv") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
            for row in reader:
                tid = row["track_id"]
                tracks[tid] = {
                    "title": row.get("track_title") or f"Track {tid}",
                    "artist": row.get("artist_name") or "Unknown",
                    "album": row.get("album_title") or None,
                    "duration_sec": parse_duration(row.get("track_duration", "")),
                }
    return tracks


def compute_normalization_stats(
    handcrafted: dict[str, list],
) -> tuple[list[float], list[float]]:
    """Compute z-score normalization stats (mean, std) across all tracks."""
    matrix = np.array(list(handcrafted.values()), dtype=np.float64)
    means = matrix.mean(axis=0).tolist()
    stds = matrix.std(axis=0).tolist()
    # Avoid division by zero
    stds = [s if s > 1e-10 else 1.0 for s in stds]
    return means, stds


def normalize_handcrafted(
    raw: list, means: list[float], stds: list[float]
) -> list[float]:
    """Z-score normalize a single handcrafted vector."""
    return [(v - m) / s for v, m, s in zip(raw, means, stds)]


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Error: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars")
        sys.exit(1)

    print("Loading embeddings...")
    data = np.load(EMBEDDINGS_PATH, allow_pickle=True).item()
    learned = data["learned"]
    handcrafted = data["handcrafted"]
    genres = data["genres"]
    failed = set(str(f) for f in data.get("failed", []))

    print(f"  {len(learned)} tracks with embeddings")
    print(f"  {len(failed)} failed tracks to skip")

    print("Loading metadata...")
    metadata = load_metadata(METADATA_ZIP)
    print(f"  {len(metadata)} tracks with metadata")

    print("Computing normalization stats...")
    means, stds = compute_normalization_stats(handcrafted)

    supabase = create_client(url, key)

    # Store normalization stats in config
    print("Saving normalization stats to config...")
    supabase.table("config").upsert(
        {
            "key": "handcrafted_norm_stats",
            "value": {"means": means, "stds": stds, "dim": 44},
        }
    ).execute()

    # Build song rows
    track_ids = [tid for tid in learned if tid not in failed]
    print(f"Importing {len(track_ids)} songs...")

    rows = []
    skipped = 0
    for tid in track_ids:
        meta = metadata.get(tid, {})
        hc_raw = handcrafted[tid]
        hc_norm = normalize_handcrafted(hc_raw, means, stds)

        if not meta:
            skipped += 1
            meta = {
                "title": f"FMA Track {tid}",
                "artist": "Unknown",
                "album": None,
                "duration_sec": None,
            }

        rows.append(
            {
                "title": meta["title"],
                "artist": meta["artist"],
                "album": meta["album"],
                "duration_sec": meta["duration_sec"],
                "learned_embedding": str(learned[tid]),
                "handcrafted_raw": str(hc_raw),
                "handcrafted_norm": str(hc_norm),
                "source": "fma",
                "embedding_type": "real",
                "metadata_status": "complete" if meta.get("title") else "partial",
            }
        )

    # Batch insert
    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        supabase.table("songs").insert(batch).execute()
        inserted += len(batch)
        if inserted % 500 == 0 or inserted == len(rows):
            print(f"  {inserted}/{len(rows)} inserted")

    print(f"\nDone! {inserted} songs imported, {skipped} without metadata.")


if __name__ == "__main__":
    main()
