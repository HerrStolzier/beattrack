"""Tests for Apple Music URL parsing, including the ReDoS hardening."""
from fastapi.testclient import TestClient

from app.main import app
from app.services.apple_music import MAX_URL_LENGTH, parse_apple_music_url


# ---------------------------------------------------------------------------
# parse_apple_music_url — happy paths
# ---------------------------------------------------------------------------

def test_parse_song_url():
    url = "https://music.apple.com/us/song/blue-monday/1440913011"
    assert parse_apple_music_url(url) == "1440913011"


def test_parse_album_url_with_track_param():
    url = "https://music.apple.com/de/album/power-corruption-lies/1440912932?i=1440913011"
    assert parse_apple_music_url(url) == "1440913011"


def test_parse_album_url_with_extra_query_params():
    url = "https://music.apple.com/de/album/x/1440912932?l=de&i=1440913011&uo=4"
    assert parse_apple_music_url(url) == "1440913011"


def test_parse_url_is_stripped():
    url = "  https://music.apple.com/us/song/blue-monday/1440913011  "
    assert parse_apple_music_url(url) == "1440913011"


# ---------------------------------------------------------------------------
# parse_apple_music_url — rejections
# ---------------------------------------------------------------------------

def test_parse_album_url_without_track_param():
    """An album URL without ?i= carries no track ID."""
    url = "https://music.apple.com/de/album/power-corruption-lies/1440912932"
    assert parse_apple_music_url(url) is None


def test_parse_rejects_non_numeric_track_param():
    url = "https://music.apple.com/de/album/x/1440912932?i=not-a-number"
    assert parse_apple_music_url(url) is None


def test_parse_rejects_wrong_host():
    url = "https://music.apple.com.evil.example/us/song/x/123"
    assert parse_apple_music_url(url) is None


def test_parse_rejects_url_not_at_start():
    """match, not search — a URL buried in other text is not a valid input.

    This is the ReDoS vector: search() let an attacker prefix arbitrary
    repetitions before the real pattern.
    """
    url = "junk https://music.apple.com/us/song/blue-monday/1440913011"
    assert parse_apple_music_url(url) is None


# ---------------------------------------------------------------------------
# ReDoS regression — CodeQL py/polynomial-redos
# ---------------------------------------------------------------------------

def test_parse_rejects_overlong_url():
    url = "https://music.apple.com/de/album/x/1?" + "a" * MAX_URL_LENGTH
    assert len(url) > MAX_URL_LENGTH
    assert parse_apple_music_url(url) is None


def test_parse_handles_pathological_repetition():
    """The pattern CodeQL reported: many repetitions of the URL prefix.

    Deterministic assertion rather than a timing one: the input is
    rejected outright, so there is nothing left to backtrack over.
    """
    payload = "http://music.apple.com/a/album/-/9?" * 60
    assert parse_apple_music_url(payload) is None


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

def test_identify_rejects_overlong_url_with_422():
    client = TestClient(app)
    resp = client.post("/identify/apple_music", json={"url": "https://music.apple.com/" + "a" * 3000})
    assert resp.status_code == 422
