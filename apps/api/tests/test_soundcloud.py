"""Tests for SoundCloud URL parsing, title parsing, and identify endpoint."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_supabase
from app.services.soundcloud import parse_soundcloud_url, parse_title
from tests.conftest import _make_supabase_mock


# ---------------------------------------------------------------------------
# parse_soundcloud_url
# ---------------------------------------------------------------------------

def test_parse_soundcloud_url_valid():
    assert parse_soundcloud_url("https://soundcloud.com/artist/track-name") is True


def test_parse_soundcloud_url_valid_www():
    assert parse_soundcloud_url("https://www.soundcloud.com/artist/track-name") is True


def test_parse_soundcloud_url_invalid_domain():
    assert parse_soundcloud_url("https://example.com/artist/track") is False


def test_parse_soundcloud_url_invalid_no_track():
    assert parse_soundcloud_url("https://soundcloud.com/artist") is False


def test_parse_soundcloud_url_empty():
    assert parse_soundcloud_url("") is False


# ---------------------------------------------------------------------------
# parse_title
# ---------------------------------------------------------------------------

def test_parse_title_dash_format():
    artist, title = parse_title("Artist - Track Name", "AuthorChannel")
    assert artist == "Artist"
    assert title == "Track Name"


def test_parse_title_plain_with_author():
    artist, title = parse_title("My Track", "CoolArtist")
    assert artist == "CoolArtist"
    assert title == "My Track"


def test_parse_title_noise_removal_official():
    artist, title = parse_title("Artist - Track [Official Audio]", "")
    assert artist == "Artist"
    assert title == "Track"


def test_parse_title_noise_removal_remix():
    artist, title = parse_title("Great Track (Remix)", "DJ Name")
    assert artist == "DJ Name"
    assert title == "Great Track"


def test_parse_title_no_author_fallback():
    artist, title = parse_title("Just A Track", "")
    assert artist == "Unknown"
    assert title == "Just A Track"


# ---------------------------------------------------------------------------
# identify_soundcloud endpoint
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_identify_soundcloud_invalid_url(client):
    resp = client.post("/identify/soundcloud", json={"url": "https://example.com"})
    assert resp.status_code == 400
    assert "Invalid SoundCloud URL" in resp.json()["detail"]


def test_identify_soundcloud_match(client):
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    for method in ("select", "eq", "ilike", "in_", "range", "insert", "single", "limit"):
        getattr(builder, method).return_value = builder

    matched_song = {
        "id": "abc123",
        "title": "Track Name",
        "artist": "Artist",
        "album": "Album",
        "bpm": 128.0,
        "musical_key": "Am",
        "duration_sec": 210.0,
    }
    execute_result = MagicMock()
    execute_result.data = [matched_song]
    builder.execute.return_value = execute_result

    app.dependency_overrides[get_supabase] = lambda: sb

    with patch("app.routes.identify.sc_fetch_oembed", new_callable=AsyncMock) as mock_oembed:
        mock_oembed.return_value = {"title": "Artist - Track Name", "author_name": "Artist"}
        resp = client.post("/identify/soundcloud", json={"url": "https://soundcloud.com/artist/track-name"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] is True
    assert data["song"] is not None
    assert data["parsed_artist"] == "Artist"
    assert data["parsed_title"] == "Track Name"


def test_identify_soundcloud_no_match(client):
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    for method in ("select", "eq", "ilike", "in_", "range", "insert", "single", "limit"):
        getattr(builder, method).return_value = builder

    execute_result = MagicMock()
    execute_result.data = []
    builder.execute.return_value = execute_result

    app.dependency_overrides[get_supabase] = lambda: sb

    with patch("app.routes.identify.sc_fetch_oembed", new_callable=AsyncMock) as mock_oembed:
        mock_oembed.return_value = {"title": "Unknown - Rare Track", "author_name": "Unknown"}
        resp = client.post("/identify/soundcloud", json={"url": "https://soundcloud.com/unknown/rare-track"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] is False
    assert data["song"] is None
    assert "nicht in der Datenbank gefunden" in data["message"]


def test_identify_soundcloud_oembed_failure(client):
    sb, _ = _make_supabase_mock()
    app.dependency_overrides[get_supabase] = lambda: sb

    with patch("app.routes.identify.sc_fetch_oembed", new_callable=AsyncMock) as mock_oembed:
        mock_oembed.return_value = None
        resp = client.post("/identify/soundcloud", json={"url": "https://soundcloud.com/artist/track"})

    assert resp.status_code == 502
    assert "Could not fetch SoundCloud metadata" in resp.json()["detail"]
