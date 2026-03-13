"""Unit tests for Beattrack API routes.

The Supabase client is mocked via FastAPI dependency_overrides so no real DB
connection is needed.
"""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_supabase

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SONG_ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "title": "Test Song",
    "artist": "Test Artist",
    "album": "Test Album",
    "bpm": 128.0,
    "musical_key": "Am",
    "duration_sec": 210.5,
}

SONG_ROW_FULL = {
    **SONG_ROW,
    "learned_embedding": [0.1] * 200,
    "handcrafted_norm": [0.5] * 50,
}

SIMILAR_ROW = {
    "id": "22222222-2222-2222-2222-222222222222",
    "title": "Similar Song",
    "artist": "Another Artist",
    "album": None,
    "bpm": 130.0,
    "similarity": 0.95,
}


def _make_response(data):
    resp = MagicMock()
    resp.data = data
    return resp


def _make_supabase_mock() -> MagicMock:
    sb = MagicMock()
    # Make every chained builder method return the same mock so we can
    # set .execute on it at the end.
    builder = MagicMock()
    sb.table.return_value = builder
    for method in ("select", "eq", "ilike", "in_", "range", "insert", "single"):
        getattr(builder, method).return_value = builder
    return sb, builder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Return a TestClient with no dependency overrides (reset after test)."""
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /songs
# ---------------------------------------------------------------------------

def test_list_songs(client):
    sb, builder = _make_supabase_mock()
    builder.execute.return_value = _make_response([SONG_ROW])
    app.dependency_overrides[get_supabase] = lambda: sb

    resp = client.get("/songs")

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["id"] == SONG_ROW["id"]
    assert body[0]["title"] == "Test Song"
    assert "learned_embedding" not in body[0]


def test_list_songs_with_query(client):
    sb, builder = _make_supabase_mock()
    builder.execute.return_value = _make_response([SONG_ROW])
    app.dependency_overrides[get_supabase] = lambda: sb

    resp = client.get("/songs?q=test&limit=5&offset=0")

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# GET /songs/{id}
# ---------------------------------------------------------------------------

def test_get_song(client):
    sb, builder = _make_supabase_mock()
    builder.execute.return_value = _make_response(SONG_ROW)
    app.dependency_overrides[get_supabase] = lambda: sb

    resp = client.get(f"/songs/{SONG_ROW['id']}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == SONG_ROW["id"]
    assert body["bpm"] == 128.0


def test_get_song_not_found(client):
    sb, builder = _make_supabase_mock()
    builder.execute.return_value = _make_response(None)
    app.dependency_overrides[get_supabase] = lambda: sb

    resp = client.get("/songs/00000000-0000-0000-0000-000000000000")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Song not found"


# ---------------------------------------------------------------------------
# POST /similar
# ---------------------------------------------------------------------------

def test_post_similar(client):
    sb, builder = _make_supabase_mock()

    # Call 1: fetch query song; Call 2: fetch handcrafted_norm for results
    builder.execute.side_effect = [
        _make_response(SONG_ROW_FULL),
        _make_response([{"id": SIMILAR_ROW["id"], "handcrafted_norm": [0.4] * 50}]),
    ]
    # RPC call
    rpc_builder = MagicMock()
    rpc_builder.execute.return_value = _make_response([SIMILAR_ROW])
    sb.rpc.return_value = rpc_builder

    app.dependency_overrides[get_supabase] = lambda: sb

    resp = client.post(
        "/similar",
        json={"song_id": SONG_ROW["id"], "limit": 10},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["id"] == SIMILAR_ROW["id"]
    assert "similarity" in body[0]
    assert "learned_embedding" not in body[0]


def test_post_similar_song_not_found(client):
    sb, builder = _make_supabase_mock()
    builder.execute.return_value = _make_response(None)
    app.dependency_overrides[get_supabase] = lambda: sb

    resp = client.post(
        "/similar",
        json={"song_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /feedback
# ---------------------------------------------------------------------------

def test_post_feedback(client):
    sb, builder = _make_supabase_mock()
    builder.execute.return_value = _make_response([{}])
    app.dependency_overrides[get_supabase] = lambda: sb

    resp = client.post(
        "/feedback",
        json={
            "query_song_id": SONG_ROW["id"],
            "result_song_id": SIMILAR_ROW["id"],
            "rating": 1,
        },
    )

    assert resp.status_code == 201
