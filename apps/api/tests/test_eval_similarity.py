"""Tests for the read-only similarity evaluation helper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "eval_similarity.py"
spec = importlib.util.spec_from_file_location("eval_similarity", SCRIPT_PATH)
assert spec and spec.loader
eval_similarity = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = eval_similarity
spec.loader.exec_module(eval_similarity)


def test_golden_query_fixture_has_discovery_notes():
    queries = eval_similarity.load_queries()

    assert len(queries) >= 30
    for query in queries:
        assert query.artist
        assert query.title
        assert query.label
        assert query.expected_traits
        assert query.avoid_traits
        assert query.known_bad
        assert query.too_obvious
        assert query.duplicate_risks
        assert query.discovery_intent


def test_score_mode_both_keeps_raw_rows_and_adds_discovery_rows():
    song = {"artist": "Burial", "title": "Archangel"}
    rows = [
        {"id": "same", "artist": "Burial", "title": "Shell of Light", "similarity": 0.91},
        {"id": "fresh", "artist": "Other", "title": "Late Night Signal", "similarity": 0.90},
    ]

    raw_rows, discovery_rows = eval_similarity._rows_for_score_mode(song, rows, "both")

    assert raw_rows == ("raw", rows)
    assert discovery_rows[0] == "discovery"
    assert discovery_rows[1][0]["id"] == "fresh"
    same_artist = next(row for row in discovery_rows[1] if row["id"] == "same")
    assert same_artist["sonic_similarity"] == pytest.approx(0.91)
    assert same_artist["discovery_penalty"] > 0


def test_score_mode_raw_does_not_mutate_rows():
    rows = [{"id": "1", "artist": "A", "title": "B", "similarity": 0.8}]

    [(label, score_rows)] = eval_similarity._rows_for_score_mode({}, rows, "raw")

    assert label == "raw"
    assert score_rows is rows
    assert "sonic_similarity" not in rows[0]


def test_format_rank_changes_summarizes_top_list_movement():
    raw_rows = [
        {"id": "same", "artist": "Burial", "title": "Shell of Light", "similarity": 0.91},
        {"id": "fresh", "artist": "Other", "title": "Late Night Signal", "similarity": 0.90},
    ]
    discovery_rows = [
        {"id": "fresh", "artist": "Other", "title": "Late Night Signal", "similarity": 0.90},
        {
            "id": "same",
            "artist": "Burial",
            "title": "Shell of Light",
            "similarity": 0.85,
            "discovery_penalty": 0.06,
        },
    ]

    changes = eval_similarity._format_rank_changes(raw_rows, discovery_rows, limit=2)

    assert set(changes) == {
        "Burial - Shell of Light: down 1 (penalty=0.060)",
        "Other - Late Night Signal: up 1 (penalty=0.000)",
    }


def test_bpm_drift_notes_flag_large_tempo_differences():
    song = {"bpm": 124}
    rows = [
        {"artist": "Close", "title": "Tempo", "bpm": 128},
        {"artist": "Far", "title": "Tempo", "bpm": 150},
        {"artist": "Missing", "title": "Tempo", "bpm": None},
    ]

    notes = eval_similarity._format_bpm_drift_notes(song, rows, limit=3)

    assert notes == ["#2 Far - Tempo: bpm_delta=26.0"]


def test_bpm_delta_ignores_missing_or_invalid_values():
    assert eval_similarity._bpm_delta(None, 120) is None
    assert eval_similarity._bpm_delta(120, "unknown") is None
    assert eval_similarity._bpm_delta(120, 128) == pytest.approx(8)


def test_snapshot_rows_keep_compact_result_fields():
    rows = [
        {
            "id": "track-1",
            "artist": "Artist",
            "title": "Track",
            "similarity": "0.91",
            "sonic_similarity": 0.95,
            "discovery_penalty": 0.04,
            "discovery_penalty_reasons": ["same_artist", "too_close"],
            "bpm": 124,
            "genre": "Techno",
            "learned_embedding": [1, 2, 3],
        }
    ]

    snapshot = eval_similarity._snapshot_rows(rows, limit=1)

    assert snapshot == [
        {
            "rank": 1,
            "id": "track-1",
            "artist": "Artist",
            "title": "Track",
            "similarity": 0.91,
            "bpm": 124,
            "genre": "Techno",
            "sonic_similarity": 0.95,
            "discovery_penalty": 0.04,
            "discovery_penalty_reasons": ["same_artist", "too_close"],
        }
    ]


def test_write_snapshot_creates_parent_directory(tmp_path):
    path = tmp_path / "snapshots" / "eval.json"

    eval_similarity._write_snapshot(path, {"summary": {"total": 1}})

    assert path.exists()
    assert '"total": 1' in path.read_text()


def test_apply_query_limit_truncates_fixture_queries():
    queries = eval_similarity.load_queries()

    limited = eval_similarity._apply_query_limit(queries, 3)

    assert len(limited) == 3
    assert limited == queries[:3]


def test_apply_query_limit_rejects_zero():
    with pytest.raises(ValueError, match="at least 1"):
        eval_similarity._apply_query_limit(eval_similarity.load_queries(), 0)


def test_query_snapshot_metadata_includes_review_notes():
    query = eval_similarity.load_queries()[0]

    metadata = eval_similarity._query_snapshot_metadata(query)

    assert metadata["artist"] == query.artist
    assert metadata["expected_traits"] == query.expected_traits
    assert metadata["avoid_traits"] == query.avoid_traits
    assert metadata["known_bad"] == query.known_bad
    assert metadata["too_obvious"] == query.too_obvious
    assert metadata["duplicate_risks"] == query.duplicate_risks
    assert metadata["discovery_intent"] == query.discovery_intent


def test_snapshot_review_summary_counts_review_signals():
    snapshot = {
        "queries": [
            {
                "strategies": {
                    "balanced": {
                        "rank_changes": ["A: down 1", "B: up 1"],
                        "bpm_drift_warnings": ["#1 A: bpm_delta=20.0"],
                        "scores": {
                            "discovery": [
                                {"discovery_penalty_reasons": ["same_artist", "too_close"]},
                                {"discovery_penalty_reasons": ["same_artist"]},
                            ],
                            "raw": [{"discovery_penalty_reasons": []}],
                        },
                    }
                }
            }
        ]
    }

    summary = eval_similarity._snapshot_review_summary(snapshot)

    assert summary == {
        "penalty_reason_counts": {"same_artist": 2, "too_close": 1},
        "rank_change_count": 2,
        "bpm_drift_warning_count": 1,
    }
