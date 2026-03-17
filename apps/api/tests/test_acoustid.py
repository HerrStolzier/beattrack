"""Tests for app.services.acoustid."""
import time
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# fingerprint_file
# ---------------------------------------------------------------------------

def test_fingerprint_file_no_fpcalc():
    """Returns None and logs a warning when fpcalc is not installed."""
    with patch("app.services.acoustid.shutil.which", return_value=None):
        from app.services.acoustid import fingerprint_file
        result = fingerprint_file("/tmp/test.mp3")
    assert result is None


def test_fingerprint_file_success():
    """Returns (fingerprint, duration) tuple when fpcalc succeeds."""
    fake_stdout = "123\nAQADtMjyyZEk"
    fake_proc = CompletedProcess(
        args=["fpcalc", "-plain", "/tmp/test.mp3"],
        returncode=0,
        stdout=fake_stdout,
        stderr="",
    )
    with patch("app.services.acoustid.shutil.which", return_value="/usr/bin/fpcalc"), \
         patch("app.services.acoustid.subprocess.run", return_value=fake_proc):
        from app.services.acoustid import fingerprint_file
        result = fingerprint_file("/tmp/test.mp3")

    assert result is not None
    fingerprint, duration = result
    assert fingerprint == "AQADtMjyyZEk"
    assert duration == 123


def test_fingerprint_file_nonzero_returncode():
    """Returns None when fpcalc exits with non-zero return code."""
    fake_proc = CompletedProcess(
        args=["fpcalc", "-plain", "/tmp/test.mp3"],
        returncode=1,
        stdout="",
        stderr="error",
    )
    with patch("app.services.acoustid.shutil.which", return_value="/usr/bin/fpcalc"), \
         patch("app.services.acoustid.subprocess.run", return_value=fake_proc):
        from app.services.acoustid import fingerprint_file
        result = fingerprint_file("/tmp/test.mp3")

    assert result is None


# ---------------------------------------------------------------------------
# lookup
# ---------------------------------------------------------------------------

def _make_acoustid_response(recordings: list) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "status": "ok",
        "results": [
            {"id": "result-1", "score": 0.9, "recordings": recordings}
        ],
    }
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_lookup_success():
    """Returns MBID when AcoustID finds a match."""
    mock_resp = _make_acoustid_response([{"id": "abc-123-mbid"}])

    with patch("app.services.acoustid.httpx.post", return_value=mock_resp):
        from app.services.acoustid import lookup
        result = lookup("FINGERPRINT", 180, "test-api-key")

    assert result == "abc-123-mbid"


def test_lookup_no_results():
    """Returns None when AcoustID returns empty results."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "ok", "results": []}
    mock_resp.raise_for_status.return_value = None

    with patch("app.services.acoustid.httpx.post", return_value=mock_resp):
        from app.services.acoustid import lookup
        result = lookup("FINGERPRINT", 180, "test-api-key")

    assert result is None


def test_lookup_no_recordings():
    """Returns None when result has no recordings list."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "status": "ok",
        "results": [{"id": "result-1", "score": 0.5, "recordings": []}],
    }
    mock_resp.raise_for_status.return_value = None

    with patch("app.services.acoustid.httpx.post", return_value=mock_resp):
        from app.services.acoustid import lookup
        result = lookup("FINGERPRINT", 180, "test-api-key")

    assert result is None


def test_lookup_api_error():
    """Returns None on HTTP error, does not raise."""
    import httpx as _httpx

    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "500 Server Error", request=MagicMock(), response=MagicMock()
    )

    with patch("app.services.acoustid.httpx.post", return_value=mock_resp):
        from app.services.acoustid import lookup
        result = lookup("FINGERPRINT", 180, "test-api-key")

    assert result is None


def test_lookup_missing_api_key():
    """Returns None immediately when api_key is empty."""
    with patch("app.services.acoustid.httpx.post") as mock_post:
        from app.services.acoustid import lookup
        result = lookup("FINGERPRINT", 180, "")

    assert result is None
    mock_post.assert_not_called()


def test_rate_limiting():
    """Three rapid calls should take at least 0.5s total due to rate limiting."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "ok", "results": []}
    mock_resp.raise_for_status.return_value = None

    import app.services.acoustid as acoustid_mod
    # Reset the last-call timer so we start fresh
    acoustid_mod._last_call = 0.0

    start = time.monotonic()
    with patch("app.services.acoustid.httpx.post", return_value=mock_resp):
        from app.services.acoustid import lookup
        lookup("FP", 10, "key")
        lookup("FP", 10, "key")
        lookup("FP", 10, "key")
    elapsed = time.monotonic() - start

    # 3 calls with 0.5s minimum gap → at least 0.5s * 2 gaps = 1.0s
    assert elapsed >= 0.9, f"Expected at least 0.9s, got {elapsed:.3f}s"
