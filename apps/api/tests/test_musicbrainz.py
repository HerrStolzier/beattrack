"""Tests for app.services.musicbrainz."""
from unittest.mock import MagicMock, patch

import pytest
import httpx as _httpx


# ---------------------------------------------------------------------------
# lookup_recording
# ---------------------------------------------------------------------------

def _make_mb_response(data: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = data
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = _httpx.HTTPStatusError(
            f"{status_code} Error", request=MagicMock(), response=MagicMock()
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_lookup_recording_success():
    """Returns title/artist/album dict when MusicBrainz responds successfully."""
    data = {
        "id": "abc-mbid",
        "title": "Test Song",
        "artist-credit": [
            {
                "artist": {"id": "artist-1", "name": "Test Artist"},
                "joinphrase": "",
            }
        ],
        "releases": [{"id": "release-1", "title": "Test Album"}],
    }
    mock_resp = _make_mb_response(data)

    with patch("app.services.musicbrainz.httpx.get", return_value=mock_resp):
        from app.services.musicbrainz import lookup_recording
        result = lookup_recording("abc-mbid")

    assert result is not None
    assert result["title"] == "Test Song"
    assert result["artist"] == "Test Artist"
    assert result["album"] == "Test Album"


def test_lookup_recording_multiple_artists():
    """Correctly joins multiple artist credits."""
    data = {
        "id": "abc-mbid",
        "title": "Collab Track",
        "artist-credit": [
            {
                "artist": {"id": "a1", "name": "Artist One"},
                "joinphrase": " & ",
            },
            {
                "artist": {"id": "a2", "name": "Artist Two"},
                "joinphrase": "",
            },
        ],
        "releases": [],
    }
    mock_resp = _make_mb_response(data)

    with patch("app.services.musicbrainz.httpx.get", return_value=mock_resp):
        from app.services.musicbrainz import lookup_recording
        result = lookup_recording("abc-mbid")

    assert result is not None
    assert result["artist"] == "Artist One & Artist Two"
    assert result["album"] == ""


def test_lookup_recording_not_found():
    """Returns None when MusicBrainz returns 404."""
    mock_resp = _make_mb_response({}, status_code=404)

    with patch("app.services.musicbrainz.httpx.get", return_value=mock_resp):
        from app.services.musicbrainz import lookup_recording
        result = lookup_recording("nonexistent-mbid")

    assert result is None


def test_lookup_recording_api_error():
    """Returns None on connection error, does not raise."""
    with patch(
        "app.services.musicbrainz.httpx.get",
        side_effect=ConnectionError("Network unreachable"),
    ):
        from app.services.musicbrainz import lookup_recording
        result = lookup_recording("some-mbid")

    assert result is None


def test_lookup_recording_http_error():
    """Returns None on HTTP 500 error."""
    mock_resp = _make_mb_response({}, status_code=500)

    with patch("app.services.musicbrainz.httpx.get", return_value=mock_resp):
        from app.services.musicbrainz import lookup_recording
        result = lookup_recording("some-mbid")

    assert result is None
