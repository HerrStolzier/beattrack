"""MERT embedding extraction worker.

Extracts 768-dim embeddings from MERT-v1-95M via mean-pooling.
Used both for batch extraction and on-demand ingest.

The model is loaded lazily on first call and cached in memory.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile

import numpy as np

logger = logging.getLogger(__name__)

# Lazy-loaded model singleton
_model = None
_processor = None
_device = None

MODEL_ID = "m-a-p/MERT-v1-95M"
SAMPLE_RATE = 24000
EMBEDDING_DIM = 768


def _get_model():
    """Load MERT model lazily (first call only, ~2s)."""
    global _model, _processor, _device

    if _model is not None:
        return _model, _processor, _device

    import torch
    from transformers import AutoModel, Wav2Vec2FeatureExtractor

    if torch.backends.mps.is_available():
        _device = "mps"
    elif torch.cuda.is_available():
        _device = "cuda"
    else:
        _device = "cpu"

    logger.info("Loading %s on %s...", MODEL_ID, _device)
    _processor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_ID)
    _model = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=True)
    _model = _model.to(_device)

    logger.info("MERT model loaded")

    return _model, _processor, _device


def load_audio_ffmpeg(path: str, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    """Load audio via ffmpeg, resample to target_sr, mono float32."""
    cmd = [
        "ffmpeg", "-i", path,
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ar", str(target_sr), "-ac", "1",
        "-v", "quiet", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {path}")
    return np.frombuffer(result.stdout, dtype=np.float32)


def extract_embedding(audio_path: str) -> list[float]:
    """Extract MERT embedding from an audio file.

    Returns 768-dim float list (mean-pooled last hidden state).
    """
    import torch

    model, processor, device = _get_model()
    audio = load_audio_ffmpeg(audio_path)

    inputs = processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)

    # Mean-pool last hidden state over timesteps -> fixed 768-dim vector
    last_hidden = outputs.hidden_states[-1]
    embedding = last_hidden.mean(dim=1).squeeze().cpu().numpy()

    return embedding.tolist()


def extract_from_preview_url(preview_url: str) -> list[float] | None:
    """Download preview and extract MERT embedding. Returns None on failure."""
    import urllib.request

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
        try:
            urllib.request.urlretrieve(preview_url, tmp.name)  # noqa: S310
            return extract_embedding(tmp.name)
        except Exception as exc:
            logger.warning("MERT extraction failed: %s", exc)
            return None
