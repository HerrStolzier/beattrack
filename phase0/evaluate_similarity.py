"""Phase 0.2 — FMA-small Benchmark: Same-Genre Precision@10.

Computes MusiCNN embeddings + handcrafted features for FMA-small tracks,
then evaluates similarity quality via Same-Genre P@10.
"""

import ast
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from extract import extract_learned_embedding, extract_handcrafted

DATA_DIR = Path(__file__).parent / "data"
EMBEDDINGS_DIR = Path(__file__).parent / "embeddings"


def get_audio_path(audio_dir: Path, track_id: int) -> Path:
    """FMA convention: track 2 → 000/000002.mp3."""
    tid_str = f"{track_id:06d}"
    return audio_dir / tid_str[:3] / f"{tid_str}.mp3"


def load_fma_metadata(metadata_dir: Path) -> pd.DataFrame:
    """Load tracks.csv and filter to fma_small with valid genre_top."""
    tracks_csv = metadata_dir / "fma_metadata" / "tracks.csv"
    if not tracks_csv.exists():
        raise FileNotFoundError(f"tracks.csv not found at {tracks_csv}")

    tracks = pd.read_csv(tracks_csv, index_col=0, header=[0, 1])
    # Filter to small subset
    small = tracks[tracks[("set", "subset")] == "small"].copy()
    # Drop tracks without a genre
    small = small[small[("track", "genre_top")].notna()]
    print(f"FMA-small: {len(small)} tracks, {small[('track', 'genre_top')].nunique()} genres")
    return small


def unzip_if_needed(zip_path: Path, extract_to: Path) -> None:
    """Extract a zip file if not already extracted."""
    if extract_to.exists() and any(extract_to.iterdir()):
        print(f"Already extracted: {extract_to}")
        return
    print(f"Extracting {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_to)
    print(f"Extracted to {extract_to}")


def compute_embeddings(
    tracks: pd.DataFrame, audio_dir: Path, output_path: Path, max_tracks: int = 0
) -> dict:
    """Compute embeddings for all tracks. Saves incrementally to avoid losing progress."""
    # Load existing progress
    if output_path.exists():
        existing = np.load(output_path, allow_pickle=True).item()
        print(f"Resuming: {len(existing.get('learned', {}))} tracks already computed")
    else:
        existing = {"learned": {}, "handcrafted": {}, "genres": {}, "failed": []}

    track_ids = list(tracks.index)
    if max_tracks > 0:
        track_ids = track_ids[:max_tracks]

    total = len(track_ids)
    done = 0
    skipped = 0
    failed = 0
    start_time = time.time()

    for i, tid in enumerate(track_ids):
        tid_str = str(tid)

        # Skip already computed
        if tid_str in existing["learned"]:
            skipped += 1
            continue

        audio_path = get_audio_path(audio_dir, tid)
        if not audio_path.exists():
            existing["failed"].append(tid)
            failed += 1
            continue

        try:
            learned = extract_learned_embedding(str(audio_path))
            hc_result = extract_handcrafted(str(audio_path))

            existing["learned"][tid_str] = learned.tolist()
            existing["handcrafted"][tid_str] = hc_result["handcrafted"].tolist()
            existing["genres"][tid_str] = str(tracks.loc[tid, ("track", "genre_top")])
            done += 1

        except Exception as e:
            existing["failed"].append(tid)
            failed += 1
            print(f"  FAIL track {tid}: {e}")

        # Progress + incremental save every 50 tracks
        computed = done + skipped
        if computed % 50 == 0 or i == total - 1:
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 and done > 0 else 0
            eta = (total - computed) / rate / 60 if rate > 0 else 0
            print(
                f"  [{computed}/{total}] done={done} skipped={skipped} "
                f"failed={failed} rate={rate:.1f}/s ETA={eta:.0f}min"
            )
            np.save(output_path, existing)

    # Final save
    np.save(output_path, existing)
    print(f"\nEmbeddings saved: {len(existing['learned'])} tracks → {output_path}")
    return existing


def cosine_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """Compute pairwise cosine similarity matrix."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)  # avoid division by zero
    normalized = embeddings / norms
    return normalized @ normalized.T


def precision_at_k(sim_matrix: np.ndarray, genres: list[str], k: int = 10) -> float:
    """Same-Genre Precision@K: for each track, what fraction of top-K neighbors share its genre?"""
    n = sim_matrix.shape[0]
    precisions = []

    for i in range(n):
        # Get top-K neighbors (excluding self)
        sims = sim_matrix[i].copy()
        sims[i] = -1  # exclude self
        top_k_idx = np.argsort(sims)[-k:]

        # Count same-genre hits
        same_genre = sum(1 for j in top_k_idx if genres[j] == genres[i])
        precisions.append(same_genre / k)

    return float(np.mean(precisions))


def evaluate(embeddings_path: Path) -> dict:
    """Run P@10 evaluation on saved embeddings."""
    data = np.load(embeddings_path, allow_pickle=True).item()

    # Filter out malformed embeddings (NaN scalars instead of vectors)
    track_ids = [
        tid for tid in sorted(data["learned"].keys())
        if isinstance(data["learned"][tid], list) and len(data["learned"][tid]) == 200
    ]
    n = len(track_ids)
    skipped = len(data["learned"]) - n
    print(f"\nEvaluating {n} tracks (skipped {skipped} malformed)...")

    learned = np.array([data["learned"][tid] for tid in track_ids])
    handcrafted = np.array([data["handcrafted"][tid] for tid in track_ids])
    genres = [data["genres"][tid] for tid in track_ids]

    # Normalize handcrafted features (different scales)
    hc_mean = handcrafted.mean(axis=0)
    hc_std = handcrafted.std(axis=0)
    hc_std = np.maximum(hc_std, 1e-10)
    handcrafted_norm = (handcrafted - hc_mean) / hc_std

    # 1. MusiCNN only
    print("Computing MusiCNN similarity...")
    sim_learned = cosine_similarity_matrix(learned)
    p10_learned = precision_at_k(sim_learned, genres, k=10)
    print(f"  MusiCNN P@10: {p10_learned:.4f}")

    # 2. Handcrafted only
    print("Computing Handcrafted similarity...")
    sim_hc = cosine_similarity_matrix(handcrafted_norm)
    p10_hc = precision_at_k(sim_hc, genres, k=10)
    print(f"  Handcrafted P@10: {p10_hc:.4f}")

    # 3. Late fusion (80/20 as per plan)
    print("Computing Late Fusion (80/20) similarity...")
    sim_fusion = 0.8 * sim_learned + 0.2 * sim_hc
    p10_fusion = precision_at_k(sim_fusion, genres, k=10)
    print(f"  Late Fusion P@10: {p10_fusion:.4f}")

    # Per-genre breakdown
    unique_genres = sorted(set(genres))
    print(f"\nPer-genre P@10 (Late Fusion):")
    genre_results = {}
    for genre in unique_genres:
        genre_mask = [g == genre for g in genres]
        genre_indices = [i for i, m in enumerate(genre_mask) if m]
        if len(genre_indices) < 2:
            continue
        sub_sim = sim_fusion[np.ix_(genre_indices, range(sim_fusion.shape[1]))]
        # P@10 for tracks in this genre
        genre_precisions = []
        for row_idx, global_idx in enumerate(genre_indices):
            sims = sim_fusion[global_idx].copy()
            sims[global_idx] = -1
            top_k_idx = np.argsort(sims)[-10:]
            same = sum(1 for j in top_k_idx if genres[j] == genre)
            genre_precisions.append(same / 10)
        genre_p10 = float(np.mean(genre_precisions))
        genre_results[genre] = {"p10": genre_p10, "count": len(genre_indices)}
        print(f"  {genre:20s}: P@10={genre_p10:.4f} (n={len(genre_indices)})")

    results = {
        "n_tracks": n,
        "musicnn_p10": p10_learned,
        "handcrafted_p10": p10_hc,
        "fusion_p10": p10_fusion,
        "fusion_weights": {"learned": 0.8, "handcrafted": 0.2},
        "per_genre": genre_results,
        "random_baseline": 1.0 / len(unique_genres),
    }

    print(f"\n--- Summary ---")
    print(f"Random baseline: {results['random_baseline']:.4f}")
    print(f"MusiCNN P@10:    {p10_learned:.4f}")
    print(f"Handcrafted P@10:{p10_hc:.4f}")
    print(f"Fusion P@10:     {p10_fusion:.4f}")
    print(f"Target:          >0.5000")
    print(f"Go/No-Go:        {'GO ✓' if p10_fusion > 0.5 else 'REVIEW needed'}")

    return results


if __name__ == "__main__":
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    embeddings_path = EMBEDDINGS_DIR / "fma_small_embeddings.npy"

    if len(sys.argv) > 1 and sys.argv[1] == "eval-only":
        # Just run evaluation on existing embeddings
        results = evaluate(embeddings_path)
        print(json.dumps(results, indent=2, default=str))
        sys.exit(0)

    max_tracks = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0

    # Unzip downloads
    metadata_zip = DATA_DIR / "fma_metadata.zip"
    audio_zip = DATA_DIR / "fma_small.zip"

    if not metadata_zip.exists():
        print(f"ERROR: {metadata_zip} not found. Download first.")
        sys.exit(1)
    if not audio_zip.exists():
        print(f"ERROR: {audio_zip} not found. Download first.")
        sys.exit(1)

    unzip_if_needed(metadata_zip, DATA_DIR)
    unzip_if_needed(audio_zip, DATA_DIR)

    # Load metadata
    tracks = load_fma_metadata(DATA_DIR)

    # Find audio directory (fma_small/ inside data/)
    audio_dir = DATA_DIR / "fma_small"
    if not audio_dir.exists():
        print(f"ERROR: {audio_dir} not found after extraction.")
        sys.exit(1)

    # Compute embeddings
    embeddings = compute_embeddings(tracks, audio_dir, embeddings_path, max_tracks=max_tracks)

    # Evaluate
    results = evaluate(embeddings_path)

    # Save results
    results_path = EMBEDDINGS_DIR / "benchmark_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {results_path}")
