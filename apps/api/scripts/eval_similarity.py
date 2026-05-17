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

from app.routes.similar import (
    _FUSION_WEIGHT_STRATEGIES,
    _compute_hc_similarity,
    _determine_weights,
    _parse_vector,
)


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
        .select("id,title,artist,bpm,musical_key,genre,learned_embedding,handcrafted_norm,mert_embedding")
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


def _candidate_vectors(sb, candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ids = [str(row["id"]) for row in candidates]
    if not ids:
        return {}

    result = (
        sb.table("songs")
        .select("id,handcrafted_norm,mert_embedding")
        .in_("id", ids)
        .execute()
    )
    return {str(row["id"]): row for row in (result.data or [])}


def _rank_with_strategy(
    song: dict[str, Any],
    candidates: list[dict[str, Any]],
    vectors: dict[str, dict[str, Any]],
    strategy: str,
) -> list[dict[str, Any]]:
    query_hc = _parse_vector(song.get("handcrafted_norm"))
    query_mert = _parse_vector(song.get("mert_embedding"))
    has_mert = bool(query_mert)
    weights = _determine_weights(
        focus=None,
        has_mert=has_mert,
        genre_weights=None,
        strategy=strategy,
    )

    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        learned_sim = float(candidate.get("similarity", 0))
        extra = vectors.get(str(candidate["id"]), {})
        hc_vec = _parse_vector(extra.get("handcrafted_norm"))
        mert_vec = _parse_vector(extra.get("mert_embedding"))
        hc_sim = _compute_hc_similarity(query_hc, hc_vec, None, None) if query_hc and hc_vec else learned_sim
        mert_sim = _compute_hc_similarity(query_mert, mert_vec, None, None) if query_mert and mert_vec else 0.0
        score = (weights.learned * learned_sim) + (weights.mert * mert_sim) + (weights.hc * hc_sim)
        ranked.append({**candidate, "similarity": score})

    ranked.sort(key=lambda row: float(row.get("similarity", 0)), reverse=True)
    return ranked


def run_read_only_eval(queries: list[QueryCase], limit: int, strategies: list[str]) -> None:
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
        candidates = _similar_songs(sb, song, max(limit * 3, limit))
        vectors = _candidate_vectors(sb, candidates) if len(strategies) > 1 else {}
        for strategy in strategies:
            print(f"\nStrategy: {strategy}")
            rows = (
                _rank_with_strategy(song, candidates, vectors, strategy)
                if len(strategies) > 1
                else candidates
            )
            for rank, result in enumerate(rows[:limit], start=1):
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
    parser.add_argument(
        "--strategies",
        default="balanced",
        help=f"Comma-separated fusion strategies to compare: {', '.join(sorted(_FUSION_WEIGHT_STRATEGIES))}",
    )
    args = parser.parse_args()

    queries = load_queries()
    if args.fixture_summary:
        print_fixture_summary(queries)
        return

    strategies = [item.strip() for item in args.strategies.split(",") if item.strip()]
    unknown = [item for item in strategies if item not in _FUSION_WEIGHT_STRATEGIES]
    if unknown:
        parser.error(f"Unknown strategies: {', '.join(unknown)}")

    run_read_only_eval(queries, args.limit, strategies)


if __name__ == "__main__":
    main()
