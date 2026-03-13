"""Tests for app/services/features.py."""
import pytest

from app.services.features import FeatureExtractionError, extract_features_safe, normalize_handcrafted


# ---------------------------------------------------------------------------
# normalize_handcrafted
# ---------------------------------------------------------------------------

def test_normalize_handcrafted():
    """Z-score with known values: (raw - mean) / std = [1.0, 1.0, 1.0]."""
    raw = [2.0, 4.0, 6.0]
    stats = {"mean": [1.0, 2.0, 3.0], "std": [1.0, 2.0, 3.0]}
    result = normalize_handcrafted(raw, stats)
    assert len(result) == 3
    for val in result:
        assert abs(val - 1.0) < 1e-9


def test_normalize_handcrafted_zero_std():
    """std=0 should be replaced by 1.0 to avoid division by zero."""
    raw = [5.0, 10.0]
    stats = {"mean": [5.0, 5.0], "std": [0.0, 0.0]}
    # With std clamped to 1.0: (5-5)/1=0.0, (10-5)/1=5.0
    result = normalize_handcrafted(raw, stats)
    assert len(result) == 2
    assert abs(result[0] - 0.0) < 1e-9
    assert abs(result[1] - 5.0) < 1e-9


# ---------------------------------------------------------------------------
# extract_features_safe
# ---------------------------------------------------------------------------

def test_extract_features_safe_invalid_path():
    """Non-existent audio path should raise FeatureExtractionError."""
    with pytest.raises(FeatureExtractionError):
        extract_features_safe("/tmp/does_not_exist_beattrack_test.wav")


@pytest.mark.slow
def test_extract_features_safe_integration(audio_wav_path):
    """Integration test: real extraction from sine_440hz.wav.

    Skipped if essentia is not installed in the venv.
    """
    try:
        import essentia  # noqa: F401
    except ImportError:
        pytest.skip("essentia not installed — skipping integration test")

    result = extract_features_safe(audio_wav_path, timeout=120)

    assert "learned" in result
    assert "handcrafted" in result
    assert "bpm" in result
    assert "key" in result

    assert len(result["learned"]) == 200
    assert len(result["handcrafted"]) == 44
    assert result["bpm"] > 0
    assert isinstance(result["key"], str)
