#!/usr/bin/env python3
"""Read-only catalog health report for Beattrack."""

from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any

from supabase import create_client


PAGE_SIZE = 1000


def _client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])


def _estimated_count(sb, column: str = "id", **filters: Any) -> int:
    query = sb.table("songs").select(column, count="planned").limit(1)
    for key, value in filters.items():
        if value == "NULL":
            query = query.filter(key, "is", "null")
        elif value == "NOT_NULL":
            query = query.filter(key, "not.is", "null")
        else:
            query = query.eq(key, value)
    result = query.execute()
    return int(result.count or 0)


def _scan_rows(sb, columns: str, *, scan_limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for start in range(0, scan_limit, PAGE_SIZE):
        end = min(start + PAGE_SIZE - 1, scan_limit - 1)
        result = sb.table("songs").select(columns).range(start, end).execute()
        batch = result.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
    return rows


def _duplicate_count(values: list[Any]) -> int:
    counts = Counter(value for value in values if value not in (None, ""))
    return sum(count - 1 for count in counts.values() if count > 1)


def _normalization_stats(sb) -> dict[str, Any] | None:
    result = (
        sb.table("config")
        .select("value")
        .eq("key", "normalization_stats")
        .maybe_single()
        .execute()
    )
    if not result.data:
        return None
    value = result.data.get("value")
    return json.loads(value) if isinstance(value, str) else value


def main() -> None:
    scan_limit = int(os.environ.get("CATALOG_HEALTH_SCAN_LIMIT", "200000"))
    sb = _client()

    total = _estimated_count(sb)
    missing_genre = _estimated_count(sb, "id", genre="NULL")
    missing_mert = _estimated_count(sb, "id", mert_embedding="NULL")

    scanned = _scan_rows(sb, "id,title,artist,deezer_id", scan_limit=scan_limit)
    duplicate_deezer_ids = _duplicate_count([row.get("deezer_id") for row in scanned])
    duplicate_title_artist = _duplicate_count(
        [
            f"{str(row.get('artist') or '').strip().lower()}||{str(row.get('title') or '').strip().lower()}"
            for row in scanned
        ]
    )
    stats = _normalization_stats(sb)

    print("# Catalog Health")
    print(f"total_songs_estimated: {total}")
    print(f"missing_genre_estimated: {missing_genre}")
    print(f"missing_mert_embedding_estimated: {missing_mert}")
    print(f"scanned_for_duplicates: {len(scanned)}")
    print(f"duplicate_deezer_ids_in_scan: {duplicate_deezer_ids}")
    print(f"duplicate_title_artist_pairs_in_scan: {duplicate_title_artist}")
    if stats:
        print(f"normalization_stats_dim: {stats.get('dim')}")
        print(f"normalization_stats_n_songs: {stats.get('n_songs')}")
    else:
        print("normalization_stats: missing")


if __name__ == "__main__":
    main()
