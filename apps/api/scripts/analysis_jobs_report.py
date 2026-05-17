#!/usr/bin/env python3
"""Read-only report for recent failed or stuck analysis jobs."""

from __future__ import annotations

import os
from collections import Counter

from supabase import create_client


def _client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])


def main() -> None:
    limit = int(os.environ.get("ANALYSIS_JOBS_REPORT_LIMIT", "50"))
    sb = _client()
    result = (
        sb.table("analysis_jobs")
        .select("id,status,attempt_count,error_code,last_error,created_at,updated_at")
        .in_("status", ["failed", "queued", "processing"])
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = result.data or []
    failed = [row for row in rows if row.get("status") == "failed"]
    active = [row for row in rows if row.get("status") in {"queued", "processing"}]

    print("# Analysis Jobs Report")
    print(f"rows_checked: {len(rows)}")
    print(f"failed_rows: {len(failed)}")
    print(f"active_rows: {len(active)}")

    if failed:
        print("\nfailed_by_error_code:")
        for code, count in Counter(row.get("error_code") or "unknown" for row in failed).most_common():
            print(f"- {code}: {count}")

    print("\nrecent_rows:")
    for row in rows[:20]:
        print(
            f"- {row.get('updated_at')} | {row.get('status')} | attempts={row.get('attempt_count')} | "
            f"{row.get('error_code') or '-'} | {row.get('id')}"
        )
        if row.get("last_error"):
            print(f"  error: {row['last_error']}")


if __name__ == "__main__":
    main()
