#!/usr/bin/env python3
"""Read-only similarity evaluation helper.

This script is intentionally lightweight. It gives Beattrack a repeatable set
of query songs that can be used before/after ranking changes.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from supabase import create_client


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "similarity_queries.json"


@dataclass(frozen=True)
class QueryCase:
    label: str
    artist: str
    title: str
    expected_traits: list[str]
    avoid_traits: list[str]


def load_queries(path: Path = FIXTURE_PATH) -> list[QueryCase]:
    rows = json.loads(path.read_text())
    return [
        QueryCase(
            label=row["label"],
            artist=row["artist"],
            title=row["title"],
            expected_traits=list(row.get("expected_traits", [])),
            avoid_traits=list(row.get("avoid_traits", [])),
        )
        for row in rows
    ]


def print_fixture_summary(queries: list[QueryCase]) -> None:
    print(f"Loaded {len(queries)} query cases")
    for idx, query in enumerate(queries, start=1):
        expected = ", ".join(query.expected_traits)
        avoid = ", ".join(query.avoid_traits)
        print(f"{idx:02d}. {query.artist} - {query.title} [{query.label}]")
        print(f"    expected: {expected}")
        print(f"    avoid:    {avoid}")


def _get_supabase():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)


def _find_query_song(sb, query: QueryCase) -> dict[str, Any] | None:
    result = (
        sb.table("songs")
        .select("id,title,artist,bpm,musical_key,genre,learned_embedding")
        .ilike("artist", f"%{query.artist}%")
        .ilike("title", f"%{query.title}%")
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def _similar_songs(sb, song: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    rpc_result = sb.rpc(
        "find_similar_songs",
        {
            "query_embedding": str(song["learned_embedding"]),
            "match_count": limit,
            "exclude_id": song["id"],
        },
    ).execute()
    return rpc_result.data or []


def run_read_only_eval(queries: list[QueryCase], limit: int) -> None:
    sb = _get_supabase()
    found = 0
    missing = 0

    for query in queries:
        print(f"\n## {query.artist} - {query.title} [{query.label}]")
        song = _find_query_song(sb, query)
        if not song:
            missing += 1
            print("Query song not found in catalog")
            continue

        found += 1
        print(
            "Query:",
            song.get("artist"),
            "-",
            song.get("title"),
            f"bpm={song.get('bpm')}",
            f"genre={song.get('genre')}",
        )
        for rank, result in enumerate(_similar_songs(sb, song, limit), start=1):
            print(
                f"{rank:02d}. {result.get('artist')} - {result.get('title')}"
                f" | sim={float(result.get('similarity', 0)):.3f}"
                f" | bpm={result.get('bpm')}"
                f" | genre={result.get('genre')}"
            )

    print(f"\nSummary: found={found} missing={missing} total={len(queries)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Beattrack similarity queries")
    parser.add_argument("--fixture-summary", action="store_true", help="Print query fixture only; no DB access")
    parser.add_argument("--limit", type=int, default=10, help="Number of similar songs to print per query")
    args = parser.parse_args()

    queries = load_queries()
    if args.fixture_summary:
        print_fixture_summary(queries)
        return

    run_read_only_eval(queries, args.limit)


if __name__ == "__main__":
    main()
