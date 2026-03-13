"""Feature extraction worker — MusiCNN embedding + handcrafted features.

This module is intended to run as an isolated subprocess. All diagnostic
output goes to stderr. stdout carries only a single JSON object on success.

Exit codes:
    0   — success, JSON written to stdout
    1   — bad arguments
    2   — model file not found
    3   — extraction error
"""
import json
import logging
import os
import sys
from pathlib import Path

import essentia.standard as es
import numpy as np

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model path resolution
# ---------------------------------------------------------------------------
_DEFAULT_MODEL_PATH = (
    Path(__file__).parent.parent.parent / "models" / "msd-musicnn-1.pb"
)


def _resolve_model_path() -> Path:
    """Return the MusiCNN model path, preferring the default location.

    Falls back to the ``MUSICNN_MODEL_PATH`` environment variable when the
    default path does not exist on disk.
    """
    if _DEFAULT_MODEL_PATH.exists():
        return _DEFAULT_MODEL_PATH

    env_path = os.environ.get("MUSICNN_MODEL_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
        logger.warning(
            "MUSICNN_MODEL_PATH='%s' does not exist on disk", env_path
        )

    # Return the default path anyway and let the caller surface the error
    return _DEFAULT_MODEL_PATH


MODEL_PATH = _resolve_model_path()


# ---------------------------------------------------------------------------
# Feature extraction helpers
# ---------------------------------------------------------------------------

def reduce_hpcp(hpcp_36: np.ndarray) -> np.ndarray:
    """Reduce 36-bin HPCP to 12-bin chroma by summing 3 sub-bins per semitone."""
    return hpcp_36.reshape(12, 3).sum(axis=1)


def extract_learned_embedding(audio_path: str) -> np.ndarray:
    """Return MusiCNN learned embedding (200-dim), mean-pooled over frames."""
    audio = es.MonoLoader(filename=audio_path, sampleRate=16000)()
    model = es.TensorflowPredictMusiCNN(
        graphFilename=str(MODEL_PATH),
        output="model/dense/BiasAdd",
    )
    embeddings = model(audio)  # shape: (n_frames, 200)
    return np.mean(embeddings, axis=0)


def extract_handcrafted(audio_path: str) -> dict:
    """Return 44-dim handcrafted feature vector plus scalar metadata."""
    features, _ = es.MusicExtractor(
        lowlevelStats=["mean", "stdev"],
        rhythmStats=["mean", "stdev"],
        tonalStats=["mean", "stdev"],
    )(audio_path)

    mfcc_stdev = np.sqrt(np.diag(features["lowlevel.mfcc.cov"]))

    handcrafted = np.concatenate([
        features["lowlevel.mfcc.mean"],                  # 13
        mfcc_stdev,                                      # 13
        reduce_hpcp(features["tonal.hpcp.mean"]),        # 12  (36 -> 12)
        [features["lowlevel.spectral_centroid.mean"]],   # 1
        [features["lowlevel.spectral_rolloff.mean"]],    # 1
        [features["rhythm.bpm"]],                        # 1
        [features["lowlevel.zerocrossingrate.mean"]],    # 1
        [features["lowlevel.average_loudness"]],         # 1
        [features["rhythm.danceability"]],               # 1
    ])  # Total: 44

    descriptor_names = features.descriptorNames()
    key = (
        str(features["tonal.key_edma.key"])
        if "tonal.key_edma.key" in descriptor_names
        else "Unknown"
    )

    duration = float(
        features["metadata.audio_properties.length"]
        if "metadata.audio_properties.length" in descriptor_names
        else 0
    )

    return {
        "handcrafted": handcrafted,
        "bpm": float(features["rhythm.bpm"]),
        "key": key,
        "duration": duration,
    }


def extract_all(audio_path: str) -> dict:
    """Run full feature extraction pipeline and return combined result dict."""
    logger.info("Starting extraction for '%s'", audio_path)

    learned = extract_learned_embedding(audio_path)
    logger.info("Learned embedding extracted (shape: %s)", learned.shape)

    hc = extract_handcrafted(audio_path)
    logger.info(
        "Handcrafted features extracted — bpm=%.1f key=%s duration=%.1f s",
        hc["bpm"],
        hc["key"],
        hc["duration"],
    )

    return {
        "learned": learned.tolist(),
        "handcrafted": hc["handcrafted"].tolist(),
        "bpm": hc["bpm"],
        "key": hc["key"],
        "duration": hc["duration"],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python -m app.workers.extract <audio_path>",
            file=sys.stderr,
        )
        sys.exit(1)

    audio_path = sys.argv[1]

    if not MODEL_PATH.exists():
        logger.error(
            "Model file not found at '%s'. "
            "Set MUSICNN_MODEL_PATH to override.",
            MODEL_PATH,
        )
        sys.exit(2)

    try:
        result = extract_all(audio_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Extraction failed for '%s': %s", audio_path, exc, exc_info=True)
        sys.exit(3)

    print(json.dumps(result))
    sys.exit(0)
