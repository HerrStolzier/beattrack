"""Tests for Spotify URL parsing, title parsing, and identify endpoint."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_supabase
from app.services.spotify import parse_spotify_url, parse_title
from tests.conftest import _make_supabase_mock


# ---------------------------------------------------------------------------
# parse_spotify_url
# ---------------------------------------------------------------------------

def test_parse_spotify_url_valid():
    assert parse_spotify_url("https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh") == "4iV5W9uYEdYUVa79Axb7Rh"


def test_parse_spotify_url_valid_with_intl_prefix():
    assert parse_spotify_url("https://open.spotify.com/intl-de/track/4iV5W9uYEdYUVa79Axb7Rh") == "4iV5W9uYEdYUVa79Axb7Rh"


def test_parse_spotify_url_valid_with_query_params():
    assert parse_spotify_url("https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh?si=abc123") == "4iV5W9uYEdYUVa79Axb7Rh"


def test_parse_spotify_url_invalid_domain():
    assert parse_spotify_url("https://spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh") is None


def test_parse_spotify_url_invalid_not_track():
    assert parse_spotify_url("https://open.spotify.com/album/4iV5W9uYEdYUVa79Axb7Rh") is None


def test_parse_spotify_url_empty():
    assert parse_spotify_url("") is None


# ---------------------------------------------------------------------------
# parse_title
# ---------------------------------------------------------------------------

def test_parse_title_dash_format():
    artist, title = parse_title("Artist - Track Name", "")
    assert artist == "Artist"
    assert title == "Track Name"


def test_parse_title_plain_no_author():
    artist, title = parse_title("My Song", "")
    assert artist == "Unknown"
    assert title == "My Song"


def test_parse_title_noise_removal_remaster():
    artist, title = parse_title("Artist - Song (Remaster)", "")
    assert artist == "Artist"
    assert title == "Song"


def test_parse_title_noise_removal_explicit():
    artist, title = parse_title("Cool Song (Explicit)", "Some Artist")
    assert artist == "Some Artist"
    assert title == "Cool Song"


def test_parse_title_with_author_name():
    artist, title = parse_title("Track Title", "Known Artist")
    assert artist == "Known Artist"
    assert title == "Track Title"


# ---------------------------------------------------------------------------
# identify_spotify endpoint
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_identify_spotify_invalid_url(client):
    resp = client.post("/identify/spotify", json={"url": "https://example.com"})
    assert resp.status_code == 400
    assert "Invalid Spotify URL" in resp.json()["detail"]


def test_identify_spotify_match(client):
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    for method in ("select", "eq", "ilike", "in_", "range", "insert", "single", "limit"):
        getattr(builder, method).return_value = builder

    matched_song = {
        "id": "xyz789",
        "title": "Track Name",
        "artist": "Artist",
        "album": "Album",
        "bpm": 120.0,
        "musical_key": "Cm",
        "duration_sec": 195.0,
    }
    execute_result = MagicMock()
    execute_result.data = [matched_song]
    builder.execute.return_value = execute_result

    app.dependency_overrides[get_supabase] = lambda: sb

    with patch("app.routes.identify.sp_fetch_oembed", new_callable=AsyncMock) as mock_oembed:
        mock_oembed.return_value = {"title": "Artist - Track Name", "author_name": ""}
        resp = client.post("/identify/spotify", json={"url": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] is True
    assert data["song"] is not None
    assert data["parsed_artist"] == "Artist"
    assert data["parsed_title"] == "Track Name"


def test_identify_spotify_no_match(client):
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    for method in ("select", "eq", "ilike", "in_", "range", "insert", "single", "limit"):
        getattr(builder, method).return_value = builder

    execute_result = MagicMock()
    execute_result.data = []
    builder.execute.return_value = execute_result

    app.dependency_overrides[get_supabase] = lambda: sb

    with patch("app.routes.identify.sp_fetch_oembed", new_callable=AsyncMock) as mock_oembed:
        mock_oembed.return_value = {"title": "Rare Song", "author_name": ""}
        resp = client.post("/identify/spotify", json={"url": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] is False
    assert data["song"] is None
    assert "Kein Match" in data["message"]


def test_identify_spotify_oembed_failure(client):
    sb, _ = _make_supabase_mock()
    app.dependency_overrides[get_supabase] = lambda: sb

    with patch("app.routes.identify.sp_fetch_oembed", new_callable=AsyncMock) as mock_oembed:
        mock_oembed.return_value = None
        resp = client.post("/identify/spotify", json={"url": "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"})

    assert resp.status_code == 502
    assert "Could not fetch Spotify metadata" in resp.json()["detail"]
