"""Phase 0.1 — Extract MusiCNN embedding + handcrafted features from audio."""

import json
import sys
from pathlib import Path

import essentia.standard as es
import numpy as np


MODEL_PATH = Path(__file__).parent / "models" / "msd-musicnn-1.pb"


def reduce_hpcp(hpcp_36: np.ndarray) -> np.ndarray:
    """36-bin HPCP -> 12-bin chroma (sum 3 sub-bins per semitone)."""
    return hpcp_36.reshape(12, 3).sum(axis=1)


def extract_learned_embedding(audio_path: str) -> np.ndarray:
    """MusiCNN learned embedding (200-dim), mean-pooled over frames."""
    audio = es.MonoLoader(filename=audio_path, sampleRate=16000)()
    model = es.TensorflowPredictMusiCNN(
        graphFilename=str(MODEL_PATH),
        output="model/dense/BiasAdd",
    )
    embeddings = model(audio)  # (n_frames, 200)
    return np.mean(embeddings, axis=0)


def extract_handcrafted(audio_path: str) -> dict:
    """44-dim handcrafted feature vector + scalar metadata."""
    features, _ = es.MusicExtractor(
        lowlevelStats=["mean", "stdev"],
        rhythmStats=["mean", "stdev"],
        tonalStats=["mean", "stdev"],
    )(audio_path)

    # MFCC stdev: sqrt of covariance diagonal (MusicExtractor outputs cov, not stdev)
    mfcc_stdev = np.sqrt(np.diag(features["lowlevel.mfcc.cov"]))

    handcrafted = np.concatenate([
        features["lowlevel.mfcc.mean"],                 # 13
        mfcc_stdev,                                     # 13
        reduce_hpcp(features["tonal.hpcp.mean"]),       # 12 (36 -> 12)
        [features["lowlevel.spectral_centroid.mean"]],  # 1
        [features["lowlevel.spectral_rolloff.mean"]],   # 1
        [features["rhythm.bpm"]],                       # 1
        [features["lowlevel.zerocrossingrate.mean"]],   # 1
        [features["lowlevel.average_loudness"]],        # 1
        [features["rhythm.danceability"]],              # 1
    ])  # Total: 44

    return {
        "handcrafted": handcrafted,
        "bpm": float(features["rhythm.bpm"]),
        "key": str(features["tonal.key_edma.key"]) if "tonal.key_edma.key" in features.descriptorNames() else "Unknown",
    }


def extract_all(audio_path: str) -> dict:
    """Full extraction: learned embedding + handcrafted features."""
    learned = extract_learned_embedding(audio_path)
    hc = extract_handcrafted(audio_path)

    return {
        "learned": learned.tolist(),
        "handcrafted": hc["handcrafted"].tolist(),
        "bpm": hc["bpm"],
        "key": hc["key"],
        "learned_shape": learned.shape,
        "handcrafted_shape": hc["handcrafted"].shape,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract.py <audio_path>")
        sys.exit(1)

    result = extract_all(sys.argv[1])
    print(f"Learned embedding shape: {result['learned_shape']}")
    print(f"Handcrafted features shape: {result['handcrafted_shape']}")
    print(f"BPM: {result['bpm']:.1f}")
    print(f"Key: {result['key']}")
    print(f"Learned (first 5): {result['learned'][:5]}")
    print(f"Handcrafted (first 5): {result['handcrafted'][:5]}")
    print(f"\nNo NaN in learned: {not np.any(np.isnan(result['learned']))}")
    print(f"No NaN in handcrafted: {not np.any(np.isnan(result['handcrafted']))}")
    print(json.dumps({"status": "ok", "learned_dim": len(result["learned"]), "handcrafted_dim": len(result["handcrafted"])}))
