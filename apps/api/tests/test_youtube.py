"""Tests for YouTube URL parsing, title parsing, and identify endpoint."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_supabase
from app.services.youtube import parse_youtube_url, parse_title
from tests.conftest import _make_supabase_mock


# ---------------------------------------------------------------------------
# parse_youtube_url
# ---------------------------------------------------------------------------

def test_parse_youtube_url_standard():
    assert parse_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_parse_youtube_url_short():
    assert parse_youtube_url("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_parse_youtube_url_shorts():
    assert parse_youtube_url("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_parse_youtube_url_invalid():
    assert parse_youtube_url("https://example.com") is None


def test_parse_youtube_url_empty():
    assert parse_youtube_url("") is None


# ---------------------------------------------------------------------------
# parse_title
# ---------------------------------------------------------------------------

def test_parse_title_dash():
    artist, title = parse_title("Artist - Song Title", "ChannelName")
    assert artist == "Artist"
    assert title == "Song Title"


def test_parse_title_by():
    artist, title = parse_title("Song Title by Artist", "ChannelName")
    assert artist == "Artist"
    assert title == "Song Title"


def test_parse_title_pipe():
    artist, title = parse_title("Artist | Song Title", "ChannelName")
    assert artist == "Artist"
    assert title == "Song Title"


def test_parse_title_strip_video():
    artist, title = parse_title("Artist - Song (Official Video)", "ChannelName")
    assert artist == "Artist"
    assert title == "Song"


def test_parse_title_strip_lyrics():
    artist, title = parse_title("Artist - Song (Lyrics)", "ChannelName")
    assert artist == "Artist"
    assert title == "Song"


def test_parse_title_strip_audio():
    artist, title = parse_title("Artist - Song (Audio)", "ChannelName")
    assert artist == "Artist"
    assert title == "Song"


def test_parse_title_fallback():
    artist, title = parse_title("Some Random Title", "ChannelName")
    assert artist == "ChannelName"
    assert title == "Some Random Title"


# ---------------------------------------------------------------------------
# identify_youtube endpoint
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_identify_youtube_invalid_url(client):
    resp = client.post("/identify/youtube", json={"url": "https://example.com"})
    assert resp.status_code == 400
    assert "Invalid YouTube URL" in resp.json()["detail"]


def test_identify_youtube_match(client):
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    # Chain all methods back to builder
    for method in ("select", "eq", "ilike", "in_", "range", "insert", "single", "limit"):
        getattr(builder, method).return_value = builder

    matched_song = {
        "id": "abc123",
        "title": "Song Title",
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

    with patch("app.routes.identify.fetch_oembed") as mock_oembed:
        mock_oembed.return_value = {"title": "Artist - Song Title", "author_name": "ArtistChannel"}
        resp = client.post("/identify/youtube", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] is True
    assert data["song"] is not None
    assert data["parsed_artist"] == "Artist"
    assert data["parsed_title"] == "Song Title"
    assert "Found match" in data["message"]


def test_identify_youtube_no_match(client):
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    for method in ("select", "eq", "ilike", "in_", "range", "insert", "single", "limit"):
        getattr(builder, method).return_value = builder

    execute_result = MagicMock()
    execute_result.data = []
    builder.execute.return_value = execute_result

    app.dependency_overrides[get_supabase] = lambda: sb

    with patch("app.routes.identify.fetch_oembed") as mock_oembed:
        mock_oembed.return_value = {"title": "Unknown Artist - Rare Track", "author_name": "SomeChannel"}
        resp = client.post("/identify/youtube", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] is False
    assert data["song"] is None
    assert "Upload the audio file" in data["message"]


def test_identify_youtube_oembed_failure(client):
    sb, _ = _make_supabase_mock()
    app.dependency_overrides[get_supabase] = lambda: sb

    with patch("app.routes.identify.fetch_oembed") as mock_oembed:
        mock_oembed.return_value = None
        resp = client.post("/identify/youtube", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})

    assert resp.status_code == 502
    assert "Could not fetch YouTube metadata" in resp.json()["detail"]
