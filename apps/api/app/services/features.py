"""Feature extraction service — runs Essentia in isolated subprocess."""
import json
import logging
import subprocess

import numpy as np

logger = logging.getLogger(__name__)


class FeatureExtractionError(Exception):
    """Raised when feature extraction fails."""


def extract_features_safe(audio_path: str, timeout: int = 180) -> dict:
    """Essentia + MusiCNN in isoliertem Subprocess mit RAM-Cap.

    Returns dict with keys: learned (list[float]), handcrafted (list[float]), bpm (float), key (str), duration (float)
    """
    import sys
    from pathlib import Path
    extract_script = str(Path(__file__).parent.parent / "workers" / "extract.py")
    try:
        result = subprocess.run(
            [sys.executable, extract_script, audio_path],
            capture_output=True, timeout=timeout, text=True,
            process_group=0,
        )
    except subprocess.TimeoutExpired:
        logger.error("Feature extraction timed out after %ds for %s", timeout, audio_path)
        raise FeatureExtractionError("Audio analysis timed out. Please try a shorter file.")

    if result.returncode != 0:
        logger.error("Essentia failed (exit %d) for %s: %s", result.returncode, audio_path, result.stderr[:500])
        raise FeatureExtractionError("Audio analysis failed. Please try a different file.")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.error("Invalid JSON from extract worker: %s", result.stdout[:200])
        raise FeatureExtractionError("Audio analysis produced invalid results.")


def normalize_handcrafted(raw: list[float], stats: dict) -> list[float]:
    """Z-Score normalization using pre-computed stats from config table.

    stats format: {"mean": [44 floats], "std": [44 floats]}
    """
    raw_arr = np.array(raw)
    mean = np.array(stats["mean"])
    std = np.array(stats["std"])
    # Prevent division by zero
    std = np.where(std == 0, 1.0, std)
    normalized = (raw_arr - mean) / std
    return normalized.tolist()
