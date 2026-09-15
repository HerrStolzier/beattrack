"""Regression cases that would invalidate a comparison of ranking methods."""

import json
from types import SimpleNamespace

import pytest

from app.db import get_supabase
from app.main import app
from app.routes.similar import _fuse_candidates, _deduplicate_versions
from app.services.vectors import parse_vector


@pytest.mark.parametrize("raw", [None, "broken", "null", "{}", "[true]", "[NaN]", [],
                                     [float("inf")], [[1]], ["1"], [True], [10**1000]])
def test_invalid_vector_is_unavailable(raw):
    assert parse_vector(raw) is None


def test_dimensions_are_checked():
    assert parse_vector("[1,2]", 44) is None
    assert parse_vector("[1,2]", 2) == [1.0, 2.0]


def test_learned_only_scores_remain_exactly_unchanged():
    results = [{"id": str(i), "similarity": value} for i, value in enumerate([0.91, 0.89, 0.87])]
    scored = _fuse_candidates(results, None, [])
    assert [r["similarity"] for r in scored] == [r["similarity"] for r in results]


def test_same_recording_with_different_artist_credit_is_not_repeated():
    rows = [{"id": "a", "title": "Maru", "artist": "Oliver", "deezer_id": 123},
            {"id": "b", "title": "Maru", "artist": "Gorge", "deezer_id": 123}]
    assert _deduplicate_versions(rows) == rows[:1]


def test_missing_mert_does_not_reduce_other_candidates_score():
    results = [{"id": "a", "similarity": 1.0}, {"id": "b", "similarity": 1.0}]
    vectors = [
        {"id": "a", "handcrafted_norm": [1.0] * 44, "mert_embedding": [1.0] * 768},
        {"id": "b", "handcrafted_norm": [1.0] * 44},
    ]
    scored = _fuse_candidates(results, [1.0] * 44, vectors, query_mert=[1.0] * 768)
    assert [row["similarity"] for row in scored] == pytest.approx([1.0, 1.0])
    by_id = {row["id"]: row for row in scored}
    assert by_id["b"]["_signals"] == ["musicnn", "handcrafted"]


def test_mert_can_contribute_without_handcrafted():
    scored = _fuse_candidates(
        [{"id": "a", "similarity": 0.8}], None,
        [{"id": "a", "mert_embedding": [1.0] * 768}], query_mert=[1.0] * 768,
    )
    assert scored[0]["similarity"] == pytest.approx((0.65 * 0.8 + 0.15) / 0.8)
    assert scored[0]["_signals"] == ["musicnn", "mert"]


def test_corrupt_candidate_does_not_disable_fusion_for_valid_candidate():
    scored = _fuse_candidates(
        [{"id": "a", "similarity": 0.8}, {"id": "b", "similarity": 0.8}],
        [1.0] * 44,
        [{"id": "a", "handcrafted_norm": "broken"},
         {"id": "b", "handcrafted_norm": json.dumps([1.0] * 44)}],
    )
    assert scored[0]["id"] == "b"
    assert scored[0]["similarity"] == pytest.approx(0.84)
    assert scored[1]["similarity"] == pytest.approx(0.8)


def test_single_search_uses_postgrest_text_vectors(client, supabase_mock, caplog):
    sb, builder = supabase_mock
    builder.execute.side_effect = [
        SimpleNamespace(data={"id": "seed", "learned_embedding": "[1,0]",
                              "handcrafted_norm": json.dumps([1.0] * 44)}),
        SimpleNamespace(data=[
            {"id": "a", "handcrafted_norm": json.dumps([-1.0] * 44)},
            {"id": "b", "handcrafted_norm": json.dumps([1.0] * 44)},
        ]),
    ]
    sb.rpc.return_value.execute.return_value = SimpleNamespace(data=[
        {"id": "a", "title": "A", "artist": "A", "similarity": 0.9},
        {"id": "b", "title": "B", "artist": "B", "similarity": 0.8},
    ])
    app.dependency_overrides[get_supabase] = lambda: sb
    response = client.post("/similar", json={"song_id": "seed", "limit": 2})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == ["b", "a"]
    assert [row["similarity"] for row in response.json()] == pytest.approx([0.84, 0.52])
    assert "Late fusion failed" not in caplog.text
    assert "_signals" not in response.json()[0]
