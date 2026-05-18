#!/usr/bin/env python3
"""Compare compact eval_similarity JSON snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_snapshot(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    return snapshot.get("summary", {})


def _review_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    return snapshot.get("review_summary", {})


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_summary = _summary(before)
    after_summary = _summary(after)
    before_review = _review_summary(before)
    after_review = _review_summary(after)

    before_reasons = before_review.get("penalty_reason_counts", {})
    after_reasons = after_review.get("penalty_reason_counts", {})
    reason_keys = sorted(set(before_reasons) | set(after_reasons))

    return {
        "summary_delta": {
            "found": int(after_summary.get("found", 0)) - int(before_summary.get("found", 0)),
            "missing": int(after_summary.get("missing", 0)) - int(before_summary.get("missing", 0)),
            "total": int(after_summary.get("total", 0)) - int(before_summary.get("total", 0)),
        },
        "review_delta": {
            "rank_change_count": int(after_review.get("rank_change_count", 0))
            - int(before_review.get("rank_change_count", 0)),
            "bpm_drift_warning_count": int(after_review.get("bpm_drift_warning_count", 0))
            - int(before_review.get("bpm_drift_warning_count", 0)),
            "penalty_reason_counts": {
                key: int(after_reasons.get(key, 0)) - int(before_reasons.get(key, 0))
                for key in reason_keys
            },
        },
    }


def print_comparison(comparison: dict[str, Any]) -> None:
    print("Snapshot comparison")
    print("Summary delta")
    for key, value in comparison["summary_delta"].items():
        print(f"- {key}: {value:+d}")

    print("Review delta")
    review = comparison["review_delta"]
    print(f"- rank_change_count: {review['rank_change_count']:+d}")
    print(f"- bpm_drift_warning_count: {review['bpm_drift_warning_count']:+d}")
    print("Penalty reason delta")
    for key, value in review["penalty_reason_counts"].items():
        print(f"- {key}: {value:+d}")


def comparison_to_json(comparison: dict[str, Any]) -> str:
    return json.dumps(comparison, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare eval_similarity JSON snapshots")
    parser.add_argument("before", type=Path, help="Baseline snapshot JSON")
    parser.add_argument("after", type=Path, help="New snapshot JSON")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    args = parser.parse_args()

    comparison = compare_snapshots(load_snapshot(args.before), load_snapshot(args.after))
    if args.format == "json":
        print(comparison_to_json(comparison))
    else:
        print_comparison(comparison)


if __name__ == "__main__":
    main()
