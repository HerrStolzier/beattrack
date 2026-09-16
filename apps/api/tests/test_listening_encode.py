"""Preflight must reject altered or undeclared audio before model loading."""
import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "listening_encode", Path(__file__).parents[1] / "scripts/listening/encode.py")
encoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encoder)


def test_preflight_rejects_invalid_inputs_before_model_loading(tmp_path):
    audio = tmp_path / "fixture.wav"
    audio.write_bytes(b"not decoded in this validation test")
    row = {"id": "a", "path": "fixture.wav", "start_seconds": 0,
           "duration_seconds": 3, "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
           "source_evidence": {"declaration": "synthetic fixture", "analysis": True,
                               "storage": True, "listening": True}}
    mutations = [({"audio_sha256": "0" * 64}, "checksum"),
                 ({"duration_seconds": float("nan")}, "finite"),
                 ({"duration_seconds": 31}, "between"),
                 ({"start_seconds": -1}, "nonnegative"),
                 ({"source_evidence": {}}, "permission")]
    for change, message in mutations:
        altered = copy.deepcopy(row)
        altered.update(change)
        with pytest.raises(ValueError, match=message):
            encoder.encode({"recordings": [altered]}, tmp_path, "mert",
                           tmp_path / "nonexistent-model", "unloaded")
