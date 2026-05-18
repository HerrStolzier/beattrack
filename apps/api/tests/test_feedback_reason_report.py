"""Tests for the feedback reason report helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "report_feedback_reasons.py"
spec = importlib.util.spec_from_file_location("report_feedback_reasons", SCRIPT_PATH)
assert spec and spec.loader
report_feedback_reasons = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = report_feedback_reasons
spec.loader.exec_module(report_feedback_reasons)


def test_summarize_reason_tags_counts_negative_feedback_only():
    rows = [
        {"rating": -1, "reason_tag": "wrong_energy"},
        {"rating": -1, "reason_tag": "wrong_energy"},
        {"rating": -1, "reason_tag": "too_obvious"},
        {"rating": -1, "reason_tag": None},
        {"rating": 1, "reason_tag": "wrong_energy"},
    ]

    summary = report_feedback_reasons.summarize_reason_tags(rows)

    assert [(item.reason_tag, item.count, item.share) for item in summary] == [
        ("wrong_energy", 2, pytest.approx(0.5)),
        ("too_obvious", 1, pytest.approx(0.25)),
        ("untagged", 1, pytest.approx(0.25)),
    ]


def test_summarize_reason_tags_handles_no_negative_feedback():
    assert report_feedback_reasons.summarize_reason_tags([{"rating": 1, "reason_tag": "wrong_energy"}]) == []


def test_summary_to_json_returns_machine_readable_payload():
    summary = [
        report_feedback_reasons.ReasonSummary("wrong_energy", 2, 0.5),
        report_feedback_reasons.ReasonSummary("too_obvious", 1, 0.25),
    ]

    payload = json.loads(report_feedback_reasons.summary_to_json(summary))

    assert payload == {
        "negative_feedback_reasons": [
            {
                "reason_tag": "wrong_energy",
                "count": 2,
                "share": 0.5,
                "suggested_ranking_check": "Review BPM drift, rhythm focus, and intensity features in eval_similarity.py.",
            },
            {
                "reason_tag": "too_obvious",
                "count": 1,
                "share": 0.25,
                "suggested_ranking_check": "Review same-artist, same-title, and too-close discovery penalties.",
            },
        ]
    }


def test_print_summary_includes_suggested_ranking_check(capsys):
    summary = [report_feedback_reasons.ReasonSummary("duplicate_version", 3, 1.0)]

    report_feedback_reasons.print_summary(summary)

    captured = capsys.readouterr()
    assert "duplicate_version: 3 (100.0%)" in captured.out
    assert "Review base-title deduplication" in captured.out
