#!/usr/bin/env python3
"""Read-only similarity evaluation helper.

This script is intentionally lightweight. It gives Beattrack a repeatable set
of query songs that can be used before/after ranking changes.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from supabase import create_client

from app.routes.similar import (
    _FUSION_WEIGHT_STRATEGIES,
    _apply_discovery_score,
    _compute_hc_similarity,
    _determine_weights,
    _parse_vector,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "similarity_queries.json"
BPM_DRIFT_WARN_THRESHOLD = 12.0


@dataclass(frozen=True)
class QueryCase:
    label: str
    artist: str
    title: str
    expected_traits: list[str]
    avoid_traits: list[str]
    known_bad: list[str]
    too_obvious: list[str]
    duplicate_risks: list[str]
    discovery_intent: str | None


def load_queries(path: Path = FIXTURE_PATH) -> list[QueryCase]:
    rows = json.loads(path.read_text())
    return [
        QueryCase(
            label=row["label"],
            artist=row["artist"],
            title=row["title"],
            expected_traits=list(row.get("expected_traits", [])),
            avoid_traits=list(row.get("avoid_traits", [])),
            known_bad=list(row.get("known_bad", [])),
            too_obvious=list(row.get("too_obvious", [])),
            duplicate_risks=list(row.get("duplicate_risks", [])),
            discovery_intent=row.get("discovery_intent"),
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
        if query.discovery_intent:
            print(f"    intent:   {query.discovery_intent}")
        if query.too_obvious:
            print(f"    obvious:  {', '.join(query.too_obvious)}")
        if query.duplicate_risks:
            print(f"    dup risk: {', '.join(query.duplicate_risks)}")
        if query.known_bad:
            print(f"    bad:      {', '.join(query.known_bad)}")


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


def _rows_for_score_mode(
    song: dict[str, Any],
    rows: list[dict[str, Any]],
    score_mode: str,
) -> list[tuple[str, list[dict[str, Any]]]]:
    if score_mode == "raw":
        return [("raw", rows)]
    if score_mode == "discovery":
        return [("discovery", _apply_discovery_score(rows, song))]
    return [
        ("raw", rows),
        ("discovery", _apply_discovery_score(rows, song)),
    ]


def _format_rank_changes(raw_rows: list[dict[str, Any]], discovery_rows: list[dict[str, Any]], limit: int) -> list[str]:
    raw_rank = {str(row.get("id")): idx for idx, row in enumerate(raw_rows[:limit], start=1)}
    discovery_rank = {str(row.get("id")): idx for idx, row in enumerate(discovery_rows[:limit], start=1)}
    candidate_ids = set(raw_rank) | set(discovery_rank)

    changes: list[tuple[int, str]] = []
    for candidate_id in candidate_ids:
        before = raw_rank.get(candidate_id, limit + 1)
        after = discovery_rank.get(candidate_id, limit + 1)
        delta = before - after
        if delta == 0:
            continue

        row = next(
            (
                item
                for item in discovery_rows
                if str(item.get("id")) == candidate_id
            ),
            None,
        ) or next(item for item in raw_rows if str(item.get("id")) == candidate_id)
        title = f"{row.get('artist')} - {row.get('title')}"
        direction = "up" if delta > 0 else "down"
        penalty = float(row.get("discovery_penalty", 0.0))
        changes.append((abs(delta), f"{title}: {direction} {abs(delta)} (penalty={penalty:.3f})"))

    changes.sort(key=lambda item: item[0], reverse=True)
    return [line for _, line in changes[:5]]


def _parse_bpm(value: Any) -> float | None:
    if value is None:
        return None
    try:
        bpm = float(value)
    except (TypeError, ValueError):
        return None
    if bpm <= 0:
        return None
    return bpm


def _bpm_delta(query_bpm: Any, result_bpm: Any) -> float | None:
    query = _parse_bpm(query_bpm)
    result = _parse_bpm(result_bpm)
    if query is None or result is None:
        return None
    return abs(query - result)


def _format_bpm_drift_notes(song: dict[str, Any], rows: list[dict[str, Any]], limit: int) -> list[str]:
    notes: list[tuple[float, str]] = []
    for rank, row in enumerate(rows[:limit], start=1):
        delta = _bpm_delta(song.get("bpm"), row.get("bpm"))
        if delta is None or delta < BPM_DRIFT_WARN_THRESHOLD:
            continue
        notes.append((
            delta,
            f"#{rank} {row.get('artist')} - {row.get('title')}: bpm_delta={delta:.1f}",
        ))

    notes.sort(key=lambda item: item[0], reverse=True)
    return [line for _, line in notes[:5]]


def _snapshot_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    snapshot: list[dict[str, Any]] = []
    for rank, row in enumerate(rows[:limit], start=1):
        item = {
            "rank": rank,
            "id": str(row.get("id")),
            "artist": row.get("artist"),
            "title": row.get("title"),
            "similarity": float(row.get("similarity", 0)),
            "bpm": row.get("bpm"),
            "genre": row.get("genre"),
        }
        if "sonic_similarity" in row:
            item["sonic_similarity"] = float(row.get("sonic_similarity", 0))
            item["discovery_penalty"] = float(row.get("discovery_penalty", 0))
            item["discovery_penalty_reasons"] = list(row.get("discovery_penalty_reasons") or [])
        snapshot.append(item)
    return snapshot


def _write_snapshot(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _apply_query_limit(queries: list[QueryCase], query_limit: int | None) -> list[QueryCase]:
    if query_limit is None:
        return queries
    if query_limit < 1:
        raise ValueError("query_limit must be at least 1")
    return queries[:query_limit]


def _query_snapshot_metadata(query: QueryCase) -> dict[str, Any]:
    return {
        "artist": query.artist,
        "title": query.title,
        "label": query.label,
        "expected_traits": query.expected_traits,
        "avoid_traits": query.avoid_traits,
        "known_bad": query.known_bad,
        "too_obvious": query.too_obvious,
        "duplicate_risks": query.duplicate_risks,
        "discovery_intent": query.discovery_intent,
    }


def _snapshot_review_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    penalty_reasons: Counter[str] = Counter()
    rank_change_count = 0
    bpm_warning_count = 0

    for query in snapshot.get("queries", []):
        for strategy in query.get("strategies", {}).values():
            rank_change_count += len(strategy.get("rank_changes", []))
            bpm_warning_count += len(strategy.get("bpm_drift_warnings", []))
            for score_rows in strategy.get("scores", {}).values():
                for row in score_rows:
                    penalty_reasons.update(row.get("discovery_penalty_reasons", []))

    return {
        "penalty_reason_counts": dict(sorted(penalty_reasons.items())),
        "rank_change_count": rank_change_count,
        "bpm_drift_warning_count": bpm_warning_count,
    }


def run_read_only_eval(
    queries: list[QueryCase],
    limit: int,
    strategies: list[str],
    score_mode: str,
    snapshot_out: Path | None = None,
) -> None:
    sb = _get_supabase()
    found = 0
    missing = 0
    snapshot: dict[str, Any] | None = None
    if snapshot_out:
        snapshot = {
            "created_at": datetime.now(UTC).isoformat(),
            "limit": limit,
            "strategies": strategies,
            "score_mode": score_mode,
            "bpm_drift_warn_threshold": BPM_DRIFT_WARN_THRESHOLD,
            "queries": [],
        }

    for query in queries:
        print(f"\n## {query.artist} - {query.title} [{query.label}]")
        query_snapshot: dict[str, Any] | None = None
        if snapshot is not None:
            query_snapshot = {
                "query": _query_snapshot_metadata(query),
                "found": False,
                "strategies": {},
            }
            snapshot["queries"].append(query_snapshot)

        song = _find_query_song(sb, query)
        if not song:
            missing += 1
            print("Query song not found in catalog")
            continue

        found += 1
        if query_snapshot is not None:
            query_snapshot["found"] = True
            query_snapshot["catalog_song"] = {
                "id": str(song.get("id")),
                "artist": song.get("artist"),
                "title": song.get("title"),
                "bpm": song.get("bpm"),
                "genre": song.get("genre"),
            }
        print(
            "Query:",
            song.get("artist"),
            "-",
            song.get("title"),
            f"bpm={song.get('bpm')}",
            f"genre={song.get('genre')}",
        )
        candidates = _similar_songs(sb, song, max(limit * 3, limit))
        needs_vectors = len(strategies) > 1
        vectors = _candidate_vectors(sb, candidates) if needs_vectors else {}
        for strategy in strategies:
            print(f"\nStrategy: {strategy}")
            rows = (
                _rank_with_strategy(song, candidates, vectors, strategy)
                if needs_vectors
                else candidates
            )
            score_rows_by_label = _rows_for_score_mode(song, rows, score_mode)
            for label, score_rows in score_rows_by_label:
                print(f"Score: {label}")
                for rank, result in enumerate(score_rows[:limit], start=1):
                    details = [
                        f"{rank:02d}. {result.get('artist')} - {result.get('title')}",
                        f"sim={float(result.get('similarity', 0)):.3f}",
                    ]
                    if "sonic_similarity" in result:
                        details.append(f"sonic={float(result.get('sonic_similarity', 0)):.3f}")
                        details.append(f"penalty={float(result.get('discovery_penalty', 0)):.3f}")
                        reasons = result.get("discovery_penalty_reasons") or []
                        if reasons:
                            details.append(f"reasons={','.join(reasons)}")
                    details.append(f"bpm={result.get('bpm')}")
                    details.append(f"genre={result.get('genre')}")
                    print(" | ".join(details))
            if score_mode == "both":
                raw_rows = next(score_rows for label, score_rows in score_rows_by_label if label == "raw")
                discovery_rows = next(score_rows for label, score_rows in score_rows_by_label if label == "discovery")
                changes = _format_rank_changes(raw_rows, discovery_rows, limit)
                if changes:
                    print("Rank changes:")
                    for change in changes:
                        print(f"- {change}")
                bpm_notes = _format_bpm_drift_notes(song, discovery_rows, limit)
                if bpm_notes:
                    print("BPM drift warnings:")
                    for note in bpm_notes:
                        print(f"- {note}")
            if query_snapshot is not None:
                strategy_snapshot = {
                    "scores": {
                        label: _snapshot_rows(score_rows, limit)
                        for label, score_rows in score_rows_by_label
                    }
                }
                if score_mode == "both":
                    strategy_snapshot["rank_changes"] = changes
                    strategy_snapshot["bpm_drift_warnings"] = bpm_notes
                query_snapshot["strategies"][strategy] = strategy_snapshot

    print(f"\nSummary: found={found} missing={missing} total={len(queries)}")
    if snapshot is not None and snapshot_out is not None:
        snapshot["summary"] = {"found": found, "missing": missing, "total": len(queries)}
        snapshot["review_summary"] = _snapshot_review_summary(snapshot)
        _write_snapshot(snapshot_out, snapshot)
        print(f"Snapshot written: {snapshot_out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Beattrack similarity queries")
    parser.add_argument("--fixture-summary", action="store_true", help="Print query fixture only; no DB access")
    parser.add_argument("--limit", type=int, default=10, help="Number of similar songs to print per query")
    parser.add_argument(
        "--strategies",
        default="balanced",
        help=f"Comma-separated fusion strategies to compare: {', '.join(sorted(_FUSION_WEIGHT_STRATEGIES))}",
    )
    parser.add_argument(
        "--score-mode",
        choices=("raw", "discovery", "both"),
        default="raw",
        help="Compare raw similarity with the conservative discovery score",
    )
    parser.add_argument(
        "--snapshot-out",
        type=Path,
        help="Optional JSON file path for saving a compact evaluation snapshot",
    )
    parser.add_argument(
        "--query-limit",
        type=int,
        help="Optional number of query songs to evaluate from the fixture",
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
    try:
        queries = _apply_query_limit(queries, args.query_limit)
    except ValueError as exc:
        parser.error(str(exc))

    run_read_only_eval(queries, args.limit, strategies, args.score_mode, args.snapshot_out)


if __name__ == "__main__":
    main()
