"""Compare MERT embeddings vs MusiCNN on a sample of songs.

Downloads MERT-v1-95M, extracts embeddings for N songs, computes
pairwise similarities, and compares with existing MusiCNN embeddings.

Usage:
    python scripts/eval_mert.py                    # 50 songs, compare
    python scripts/eval_mert.py --samples 100      # more songs
    python scripts/eval_mert.py --model m-a-p/MERT-v1-330M  # larger model

Requirements (install in venv):
    uv pip install transformers torch torchaudio scipy --python .venv/bin/python
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
import urllib.request

import numpy as np

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEEZER_API = "https://api.deezer.com"


def fetch_preview_url(deezer_id: int) -> str | None:
    """Get fresh preview URL from Deezer."""
    try:
        req = urllib.request.Request(
            f"{DEEZER_API}/track/{deezer_id}",
            headers={"Accept": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=15)  # noqa: S310
        data = json.loads(resp.read().decode())
        return data.get("preview")
    except Exception:
        return None


def download_preview(url: str, dest: str) -> bool:
    try:
        urllib.request.urlretrieve(url, dest)  # noqa: S310
        return True
    except Exception:
        return False


def load_audio(path: str, target_sr: int = 24000) -> np.ndarray:
    """Load audio file and resample to target sample rate."""
    import torchaudio

    waveform, sr = torchaudio.load(path)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(sr, target_sr)
        waveform = resampler(waveform)
    return waveform.squeeze().numpy()


def extract_mert_embedding(
    audio: np.ndarray,
    model,
    processor,
    device: str = "cpu",
) -> np.ndarray:
    """Extract mean-pooled embedding from MERT model."""
    import torch

    inputs = processor(audio, sampling_rate=24000, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)

    # Use last hidden state, mean-pool over time
    last_hidden = outputs.hidden_states[-1]  # [batch, timesteps, hidden_dim]
    embedding = last_hidden.mean(dim=1).squeeze().cpu().numpy()
    return embedding


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare MERT vs MusiCNN embeddings")
    parser.add_argument("--samples", type=int, default=50, help="Number of songs")
    parser.add_argument("--model", type=str, default="m-a-p/MERT-v1-95M", help="HuggingFace model ID")
    parser.add_argument("--device", type=str, default="auto", help="Device: auto, cpu, mps, cuda")
    args = parser.parse_args()

    import torch

    if args.device == "auto":
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
    else:
        device = args.device
    logger.info("Using device: %s", device)

    # Load MERT model
    from transformers import AutoModel, Wav2Vec2FeatureExtractor

    logger.info("Loading %s...", args.model)
    processor = Wav2Vec2FeatureExtractor.from_pretrained(args.model)
    model = AutoModel.from_pretrained(args.model, trust_remote_code=True)
    model = model.to(device)
    model.set_strict_mode = False  # type: ignore[attr-defined]
    logger.info("Model loaded (device=%s)", device)

    # Fetch sample songs from DB
    from app.db import get_supabase

    sb = get_supabase()
    result = sb.rpc("sample_embeddings", {"sample_size": args.samples}).execute()
    songs = result.data or []
    logger.info("Got %d songs from DB", len(songs))

    song_ids = [str(s["id"]) for s in songs]
    meta_result = (
        sb.table("songs")
        .select("id, deezer_id, title, artist, genre, learned_embedding")
        .in_("id", song_ids)
        .execute()
    )
    song_map = {str(r["id"]): r for r in (meta_result.data or []) if r.get("deezer_id")}
    logger.info("Songs with deezer_id: %d", len(song_map))

    # Extract embeddings
    mert_embeddings: dict[str, np.ndarray] = {}
    musicnn_embeddings: dict[str, np.ndarray] = {}
    temp_dir = tempfile.mkdtemp(prefix="mert_eval_")

    for i, (sid, song) in enumerate(list(song_map.items())[:args.samples]):
        deezer_id = song["deezer_id"]
        logger.info("[%d/%d] %s - %s", i + 1, min(args.samples, len(song_map)),
                    song["artist"], song["title"])

        preview_url = fetch_preview_url(deezer_id)
        if not preview_url:
            continue
        preview_path = os.path.join(temp_dir, f"{deezer_id}.mp3")
        if not download_preview(preview_url, preview_path):
            continue

        try:
            audio = load_audio(preview_path, target_sr=24000)
            emb = extract_mert_embedding(audio, model, processor, device)
            mert_embeddings[sid] = emb

            musicnn_raw = song.get("learned_embedding")
            if musicnn_raw:
                if isinstance(musicnn_raw, str):
                    musicnn_raw = json.loads(musicnn_raw)
                musicnn_embeddings[sid] = np.array(musicnn_raw, dtype=np.float64)
        except Exception as exc:
            logger.warning("Failed for %s: %s", sid, exc)
        finally:
            try:
                os.unlink(preview_path)
            except OSError:
                pass
        time.sleep(0.15)

    try:
        os.rmdir(temp_dir)
    except OSError:
        pass

    logger.info("MERT: %d embeddings, MusiCNN: %d", len(mert_embeddings), len(musicnn_embeddings))

    if len(mert_embeddings) < 10:
        logger.error("Not enough embeddings for comparison")
        return

    # Compare pairwise similarities
    common_ids = list(set(mert_embeddings.keys()) & set(musicnn_embeddings.keys()))
    n = len(common_ids)

    rng = np.random.default_rng(42)
    n_pairs = min(2000, n * (n - 1) // 2)
    idx_a = rng.integers(0, n, size=n_pairs)
    idx_b = rng.integers(0, n, size=n_pairs)
    mask = idx_a != idx_b
    idx_a, idx_b = idx_a[mask], idx_b[mask]

    mert_sims, musicnn_sims = [], []
    for a, b in zip(idx_a, idx_b):
        id_a, id_b = common_ids[a], common_ids[b]
        mert_sims.append(cosine_sim(mert_embeddings[id_a], mert_embeddings[id_b]))
        musicnn_sims.append(cosine_sim(musicnn_embeddings[id_a], musicnn_embeddings[id_b]))

    mert_sims_arr = np.array(mert_sims)
    musicnn_sims_arr = np.array(musicnn_sims)

    from scipy.stats import spearmanr
    corr, p_value = spearmanr(mert_sims_arr, musicnn_sims_arr)

    # MERT effective dimensionality
    from sklearn.decomposition import PCA

    mert_matrix = np.array([mert_embeddings[sid] for sid in common_ids])
    pca = PCA(n_components=min(50, mert_matrix.shape[1]))
    pca.fit(mert_matrix)
    cum_var = np.cumsum(pca.explained_variance_ratio_)
    n_90 = int(np.searchsorted(cum_var, 0.90)) + 1
    eigenvalues = pca.explained_variance_ratio_
    entropy = -np.sum(eigenvalues * np.log(eigenvalues + 1e-10))
    effective_dim = float(np.exp(entropy))

    print("\n" + "=" * 60)
    print("MERT vs MusiCNN EMBEDDING COMPARISON")
    print("=" * 60)
    print(f"Model:              {args.model}")
    print(f"Songs compared:     {n}")
    print(f"Pairs:              {len(mert_sims_arr)}")
    print(f"MERT dim:           {next(iter(mert_embeddings.values())).shape[0]}")
    print(f"MusiCNN dim:        {next(iter(musicnn_embeddings.values())).shape[0]}")

    for label, sims in [("MERT", mert_sims_arr), ("MusiCNN", musicnn_sims_arr)]:
        print(f"\n{label} Cosine Similarity:")
        print(f"  Mean:     {np.mean(sims):.4f}")
        print(f"  Std:      {np.std(sims):.4f}")
        print(f"  Range:    {np.min(sims):.4f} — {np.max(sims):.4f}")
        print(f"  P5-P95:   {np.percentile(sims, 5):.4f} — {np.percentile(sims, 95):.4f}")

    print(f"\nRank Correlation (Spearman): rho = {corr:.4f} (p = {p_value:.2e})")
    if corr > 0.7:
        print("  -> Strong agreement (replacement candidate)")
    elif corr > 0.4:
        print("  -> Moderate agreement (captures different aspects)")
    else:
        print("  -> Weak agreement (complementary signal)")

    print(f"\nMERT Space: effective_dim={effective_dim:.1f}, PCs_90%={n_90}")
    print(f"MusiCNN Space: effective_dim=11.3, PCs_90%=12")

    print("\nVERDICT:")
    if np.std(mert_sims_arr) > np.std(musicnn_sims_arr) * 1.2:
        print("  + Better spread (more discriminative)")
    if effective_dim > 15:
        print("  + Higher effective dimensionality")
    if corr < 0.5:
        print("  + Captures different structure (complementary)")
    if np.std(mert_sims_arr) <= np.std(musicnn_sims_arr) * 0.8:
        print("  - Worse spread than MusiCNN")
    print("=" * 60)


if __name__ == "__main__":
    main()
