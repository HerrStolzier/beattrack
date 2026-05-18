#!/usr/bin/env python3
"""Read-only report for negative feedback reason tags."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass
from typing import Any

from supabase import create_client


KNOWN_REASON_TAGS = (
    "wrong_energy",
    "wrong_genre",
    "duplicate_version",
    "too_obvious",
    "bad_metadata",
    "other",
)

SUGGESTED_RANKING_CHECKS = {
    "wrong_energy": "Review BPM drift, rhythm focus, and intensity features in eval_similarity.py.",
    "wrong_genre": "Inspect genre metadata quality and whether sonic ranking is over-serving cross-genre neighbors.",
    "duplicate_version": "Review base-title deduplication and same-title discovery penalties.",
    "too_obvious": "Review same-artist, same-title, and too-close discovery penalties.",
    "bad_metadata": "Inspect Deezer metadata, title normalization, and artist/title matching.",
    "other": "Read free-form notes or sample affected pairs before changing ranking.",
    "untagged": "Improve feedback capture or sample recent thumbs-down pairs manually.",
}


@dataclass(frozen=True)
class ReasonSummary:
    reason_tag: str
    count: int
    share: float


def summarize_reason_tags(rows: list[dict[str, Any]]) -> list[ReasonSummary]:
    counts: Counter[str] = Counter()
    for row in rows:
        if int(row.get("rating", 0)) >= 0:
            continue
        reason = row.get("reason_tag") or "untagged"
        counts[str(reason)] += 1

    total = sum(counts.values())
    if total == 0:
        return []

    known_order = {tag: idx for idx, tag in enumerate((*KNOWN_REASON_TAGS, "untagged"))}
    return [
        ReasonSummary(reason_tag=tag, count=count, share=count / total)
        for tag, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], known_order.get(item[0], len(known_order)), item[0]),
        )
    ]


def print_summary(summary: list[ReasonSummary]) -> None:
    if not summary:
        print("No negative feedback reason tags found.")
        return

    print("Negative feedback reasons")
    for item in summary:
        suggestion = SUGGESTED_RANKING_CHECKS.get(item.reason_tag, "Sample affected pairs before changing ranking.")
        print(f"- {item.reason_tag}: {item.count} ({item.share:.1%})")
        print(f"  next: {suggestion}")


def summary_to_json(summary: list[ReasonSummary]) -> str:
    payload = {
        "negative_feedback_reasons": [
            {
                "reason_tag": item.reason_tag,
                "count": item.count,
                "share": item.share,
                "suggested_ranking_check": SUGGESTED_RANKING_CHECKS.get(
                    item.reason_tag,
                    "Sample affected pairs before changing ranking.",
                ),
            }
            for item in summary
        ]
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _get_supabase():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)


def fetch_feedback_rows(limit: int) -> list[dict[str, Any]]:
    result = (
        _get_supabase()
        .table("feedback")
        .select("rating,reason_tag")
        .eq("rating", -1)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def main() -> None:
    parser = argparse.ArgumentParser(description="Report negative feedback reason tags")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum recent negative feedback rows to inspect")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    summary = summarize_reason_tags(fetch_feedback_rows(args.limit))
    if args.format == "json":
        print(summary_to_json(summary))
    else:
        print_summary(summary)


if __name__ == "__main__":
    main()
