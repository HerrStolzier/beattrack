"""Analyze embedding space with PCA and cluster metrics.

Fetches random sample of learned embeddings from Supabase,
runs PCA, computes cluster statistics, and generates visualization.

Usage:
    python scripts/analyze_embeddings.py
    python scripts/analyze_embeddings.py --samples 5000
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path and load .env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze embedding space")
    parser.add_argument("--samples", type=int, default=3000, help="Number of songs to sample")
    parser.add_argument("--output", type=str, default="embedding_analysis.png", help="Output plot path")
    args = parser.parse_args()

    import numpy as np

    from app.db import get_supabase
    sb = get_supabase()

    # Fetch random sample via RPC (TABLESAMPLE for efficiency)
    logger.info("Fetching %d random embeddings via RPC...", args.samples)
    result = sb.rpc("sample_embeddings", {"sample_size": args.samples}).execute()
    all_rows = result.data or []
    all_rows = [r for r in all_rows if r.get("learned_embedding")]
    logger.info("Got %d samples with embeddings", len(all_rows))

    if len(all_rows) < 100:
        logger.error("Not enough samples for analysis")
        return

    # Build numpy arrays — embeddings may come as string "[0.1,0.2,...]" from RPC
    def parse_embedding(e):
        if isinstance(e, str):
            return json.loads(e)
        return e

    embeddings = np.array([parse_embedding(r["learned_embedding"]) for r in all_rows], dtype=np.float64)
    genres = [r.get("genre", "Unknown") or "Unknown" for r in all_rows]
    bpms = [r.get("bpm") or 0 for r in all_rows]

    logger.info("Embedding shape: %s", embeddings.shape)

    # --- Stats ---
    # Pairwise cosine similarities (sample 1000 pairs)
    n = len(embeddings)
    rng = np.random.default_rng(42)
    n_pairs = min(5000, n * (n - 1) // 2)
    idx_a = rng.integers(0, n, size=n_pairs)
    idx_b = rng.integers(0, n, size=n_pairs)
    # Avoid self-pairs
    mask = idx_a != idx_b
    idx_a, idx_b = idx_a[mask], idx_b[mask]

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normed = embeddings / norms
    cosine_sims = np.sum(normed[idx_a] * normed[idx_b], axis=1)

    print("\n" + "=" * 60)
    print("EMBEDDING SPACE ANALYSIS")
    print("=" * 60)
    print(f"Samples:            {n}")
    print(f"Dimensions:         {embeddings.shape[1]}")
    print(f"Unique genres:      {len(set(genres))}")
    print(f"\nPairwise Cosine Similarity ({len(cosine_sims)} random pairs):")
    print(f"  Mean:             {np.mean(cosine_sims):.4f}")
    print(f"  Std:              {np.std(cosine_sims):.4f}")
    print(f"  Min:              {np.min(cosine_sims):.4f}")
    print(f"  Max:              {np.max(cosine_sims):.4f}")
    print(f"  Median:           {np.median(cosine_sims):.4f}")
    print(f"  P5:               {np.percentile(cosine_sims, 5):.4f}")
    print(f"  P25:              {np.percentile(cosine_sims, 25):.4f}")
    print(f"  P75:              {np.percentile(cosine_sims, 75):.4f}")
    print(f"  P95:              {np.percentile(cosine_sims, 95):.4f}")

    # --- PCA ---
    from sklearn.decomposition import PCA

    pca = PCA(n_components=min(50, embeddings.shape[1]))
    pca.fit(embeddings)

    cum_var = np.cumsum(pca.explained_variance_ratio_)
    n_90 = np.searchsorted(cum_var, 0.90) + 1
    n_95 = np.searchsorted(cum_var, 0.95) + 1

    print(f"\nPCA Explained Variance:")
    print(f"  PC1:              {pca.explained_variance_ratio_[0]:.4f} ({pca.explained_variance_ratio_[0]*100:.1f}%)")
    print(f"  PC1+PC2:          {cum_var[1]:.4f} ({cum_var[1]*100:.1f}%)")
    print(f"  PCs for 90%:      {n_90}")
    print(f"  PCs for 95%:      {n_95}")

    # --- Effective dimensionality ---
    eigenvalues = pca.explained_variance_ratio_
    entropy = -np.sum(eigenvalues * np.log(eigenvalues + 1e-10))
    effective_dim = np.exp(entropy)
    print(f"  Effective dim:    {effective_dim:.1f} (of {embeddings.shape[1]})")

    # --- Genre clustering quality ---
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import LabelEncoder

    pca_2d = PCA(n_components=2)
    coords_2d = pca_2d.fit_transform(embeddings)

    le = LabelEncoder()
    genre_labels = le.fit_transform(genres)
    # Only compute silhouette if we have 2+ genres
    if len(set(genres)) >= 2:
        sil = silhouette_score(coords_2d, genre_labels, sample_size=min(2000, n))
        print(f"\nGenre Clustering (Silhouette Score): {sil:.4f}")
        print(f"  (-1=bad, 0=overlapping, 1=perfect separation)")
        if sil < 0.1:
            print(f"  → Genres are NOT well-separated in embedding space")
        elif sil < 0.3:
            print(f"  → Weak genre structure exists")
        else:
            print(f"  → Clear genre clusters exist")

    # --- Histogram of cosine similarities ---
    print(f"\nCosine Similarity Distribution:")
    bins = [0.8, 0.85, 0.9, 0.92, 0.94, 0.96, 0.98, 1.0]
    counts, _ = np.histogram(cosine_sims, bins=bins)
    for i, count in enumerate(counts):
        pct = count / len(cosine_sims) * 100
        bar = "█" * int(pct / 2)
        print(f"  {bins[i]:.2f}-{bins[i+1]:.2f}: {pct:5.1f}% {bar}")

    print("=" * 60)

    # --- Plot ---
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        # 1. PCA 2D scatter colored by genre
        unique_genres = list(set(genres))
        colors = plt.cm.tab20(np.linspace(0, 1, len(unique_genres)))
        genre_color_map = {g: colors[i] for i, g in enumerate(unique_genres)}
        point_colors = [genre_color_map[g] for g in genres]

        axes[0].scatter(coords_2d[:, 0], coords_2d[:, 1], c=point_colors, alpha=0.3, s=4)
        axes[0].set_title(f"PCA 2D (var explained: {pca_2d.explained_variance_ratio_.sum()*100:.1f}%)")
        axes[0].set_xlabel("PC1")
        axes[0].set_ylabel("PC2")

        # 2. Cosine similarity histogram
        axes[1].hist(cosine_sims, bins=50, color="#f59e0b", alpha=0.8, edgecolor="black", linewidth=0.5)
        axes[1].axvline(np.mean(cosine_sims), color="red", linestyle="--", label=f"Mean: {np.mean(cosine_sims):.3f}")
        axes[1].set_title("Pairwise Cosine Similarity")
        axes[1].set_xlabel("Cosine Similarity")
        axes[1].legend()

        # 3. Explained variance curve
        axes[2].plot(range(1, len(cum_var) + 1), cum_var, "o-", markersize=3, color="#22d3ee")
        axes[2].axhline(0.90, color="red", linestyle="--", alpha=0.5, label="90%")
        axes[2].axhline(0.95, color="orange", linestyle="--", alpha=0.5, label="95%")
        axes[2].set_title(f"PCA Cumulative Variance (90% @ {n_90} PCs)")
        axes[2].set_xlabel("Principal Components")
        axes[2].set_ylabel("Cumulative Variance")
        axes[2].legend()

        plt.tight_layout()
        out_path = Path(__file__).parent / args.output
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        logger.info("Plot saved to %s", out_path)
    except ImportError:
        logger.warning("matplotlib not installed, skipping plot")


if __name__ == "__main__":
    main()
