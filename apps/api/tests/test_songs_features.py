"""Tests for songs features endpoint and _compute_radar."""
import pytest
from app.routes.songs import _compute_radar, RadarFeatures


class TestComputeRadar:
    """Tests for the _compute_radar helper."""

    def test_returns_zeros_for_short_vector(self):
        result = _compute_radar([0.0] * 10)
        assert result == RadarFeatures(timbre=0, harmony=0, rhythm=0, brightness=0, intensity=0)

    def test_returns_valid_features_for_44_dim(self):
        # Build a 44-dim vector with known values
        hc = [0.0] * 44
        hc[1:13] = [0.5] * 12  # MFCC means
        hc[26:38] = [0.3] * 12  # HPCP
        hc[38] = 0.6  # spectral centroid
        hc[39] = 0.7  # spectral rolloff
        hc[40] = 130.0  # BPM
        hc[41] = 0.4  # ZCR
        hc[42] = 0.8  # loudness
        hc[43] = 0.6  # danceability

        result = _compute_radar(hc)

        assert 0 <= result.timbre <= 1
        assert 0 <= result.harmony <= 1
        assert 0 <= result.rhythm <= 1
        assert 0 <= result.brightness <= 1
        assert 0 <= result.intensity <= 1

    def test_rhythm_scales_with_bpm(self):
        hc_slow = [0.0] * 44
        hc_slow[40] = 70.0  # slow BPM
        hc_slow[43] = 0.5  # danceability

        hc_fast = [0.0] * 44
        hc_fast[40] = 180.0  # fast BPM
        hc_fast[43] = 0.5  # danceability

        slow = _compute_radar(hc_slow)
        fast = _compute_radar(hc_fast)

        assert fast.rhythm > slow.rhythm

    def test_intensity_scales_with_loudness(self):
        hc_quiet = [0.0] * 44
        hc_quiet[42] = 0.1  # quiet

        hc_loud = [0.0] * 44
        hc_loud[42] = 0.9  # loud

        quiet = _compute_radar(hc_quiet)
        loud = _compute_radar(hc_loud)

        assert loud.intensity > quiet.intensity

    def test_values_clamped_to_0_1(self):
        # Extreme values should still be clamped
        hc = [100.0] * 44
        result = _compute_radar(hc)

        assert result.timbre <= 1
        assert result.harmony <= 1
        assert result.rhythm <= 1
        assert result.brightness <= 1
        assert result.intensity <= 1


class TestSongCountEndpoint:
    """Tests for GET /songs/count/total."""

    def test_song_count(self, client, supabase_mock):
        from app.db import get_supabase
        from app.main import app

        sb, builder = supabase_mock
        # Mock the count query
        result_mock = type("R", (), {"count": 32871})()
        builder.execute.return_value = result_mock
        app.dependency_overrides[get_supabase] = lambda: sb

        response = client.get("/songs/count/total")
        assert response.status_code == 200
        assert response.json() == {"count": 32871}


class TestFeaturesEndpoint:
    """Tests for GET /songs/{id}/features."""

    def test_features_success(self, client, supabase_mock):
        from app.db import get_supabase
        from app.main import app

        sb, builder = supabase_mock
        hc = [0.0] * 44
        hc[1:13] = [0.5] * 12
        hc[26:38] = [0.3] * 12
        hc[40] = 120.0
        hc[42] = 0.7
        hc[43] = 0.5

        builder.execute.return_value = type("R", (), {"data": {"handcrafted_norm": hc}})()
        app.dependency_overrides[get_supabase] = lambda: sb

        response = client.get("/songs/test-id/features")
        assert response.status_code == 200
        data = response.json()
        assert "timbre" in data
        assert "harmony" in data
        assert "rhythm" in data
        assert "brightness" in data
        assert "intensity" in data

    def test_features_no_data(self, client, supabase_mock):
        from app.db import get_supabase
        from app.main import app

        sb, builder = supabase_mock
        builder.execute.return_value = type("R", (), {"data": {"handcrafted_norm": None}})()
        app.dependency_overrides[get_supabase] = lambda: sb

        response = client.get("/songs/test-id/features")
        assert response.status_code == 422
