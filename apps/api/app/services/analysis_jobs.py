"""Persistence helpers for uploaded audio analysis jobs."""
from datetime import UTC, datetime
from typing import Any

from app.db import get_supabase

TERMINAL_STATUSES = {"completed", "failed"}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def create_analysis_job(
    job_id: str,
    *,
    audio_path: str,
    duration_sec: float | None,
) -> None:
    """Create a queued analysis job row."""
    now = _utc_now()
    get_supabase().table("analysis_jobs").insert({
        "id": job_id,
        "status": "queued",
        "progress": 0.0,
        "audio_path": audio_path,
        "duration_sec": duration_sec,
        "created_at": now,
        "updated_at": now,
    }).execute()


def get_analysis_job(job_id: str) -> dict[str, Any] | None:
    """Return a persisted analysis job, or None when it does not exist."""
    result = (
        get_supabase()
        .table("analysis_jobs")
        .select("*")
        .eq("id", job_id)
        .maybe_single()
        .execute()
    )
    return result.data


def update_analysis_job(job_id: str, status: str, **kwargs: Any) -> None:
    """Update an analysis job row with a new status and optional fields."""
    payload: dict[str, Any] = {
        "status": status,
        "updated_at": _utc_now(),
        **kwargs,
    }
    if status in TERMINAL_STATUSES:
        payload["completed_at"] = payload["updated_at"]

    get_supabase().table("analysis_jobs").update(payload).eq("id", job_id).execute()
