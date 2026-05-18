"""Tests for eval snapshot comparison helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "compare_eval_snapshots.py"
spec = importlib.util.spec_from_file_location("compare_eval_snapshots", SCRIPT_PATH)
assert spec and spec.loader
compare_eval_snapshots = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = compare_eval_snapshots
spec.loader.exec_module(compare_eval_snapshots)


def test_compare_snapshots_returns_summary_and_review_deltas():
    before = {
        "summary": {"found": 8, "missing": 2, "total": 10},
        "review_summary": {
            "rank_change_count": 5,
            "bpm_drift_warning_count": 3,
            "penalty_reason_counts": {"same_artist": 4, "too_close": 2},
        },
    }
    after = {
        "summary": {"found": 9, "missing": 1, "total": 10},
        "review_summary": {
            "rank_change_count": 7,
            "bpm_drift_warning_count": 1,
            "penalty_reason_counts": {"same_artist": 3, "same_title": 2, "too_close": 5},
        },
    }

    comparison = compare_eval_snapshots.compare_snapshots(before, after)

    assert comparison == {
        "summary_delta": {"found": 1, "missing": -1, "total": 0},
        "review_delta": {
            "rank_change_count": 2,
            "bpm_drift_warning_count": -2,
            "penalty_reason_counts": {
                "same_artist": -1,
                "same_title": 2,
                "too_close": 3,
            },
        },
    }


def test_print_comparison_outputs_signed_deltas(capsys):
    comparison = {
        "summary_delta": {"found": 1, "missing": -1, "total": 0},
        "review_delta": {
            "rank_change_count": 2,
            "bpm_drift_warning_count": -2,
            "penalty_reason_counts": {"same_artist": -1},
        },
    }

    compare_eval_snapshots.print_comparison(comparison)

    captured = capsys.readouterr()
    assert "found: +1" in captured.out
    assert "missing: -1" in captured.out
    assert "same_artist: -1" in captured.out


def test_comparison_to_json_returns_machine_readable_payload():
    comparison = {
        "summary_delta": {"found": 0, "missing": 0, "total": 0},
        "review_delta": {
            "rank_change_count": 1,
            "bpm_drift_warning_count": -1,
            "penalty_reason_counts": {"too_close": 2},
        },
    }

    payload = json.loads(compare_eval_snapshots.comparison_to_json(comparison))

    assert payload == comparison
