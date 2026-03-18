"""Batch ingest endpoint — accepts Deezer track metadata, extracts features on Railway, stores in DB.

Protected by admin secret. Temporary endpoint for bulk DB expansion.
"""

import logging
import os

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ingest", tags=["admin"])

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")
MAX_BATCH_SIZE = 10


class TrackItem(BaseModel):
    deezer_id: int
    title: str
    artist: str
    artist_id: int | None = None
    album: str | None = None
    duration: int = 0
    preview_url: str | None = None


class BatchIngestRequest(BaseModel):
    tracks: list[TrackItem]


class BatchIngestResponse(BaseModel):
    queued: int
    succeeded: int
    failed: int
    errors: list[str]


def _verify_admin(authorization: str | None) -> None:
    if not ADMIN_SECRET:
        raise HTTPException(503, "ADMIN_SECRET not configured")
    if authorization != f"Bearer {ADMIN_SECRET}":
        raise HTTPException(403, "Unauthorized")


def _ingest_single(track_dict: dict) -> tuple[bool, str]:
    """Worker function: ingest a single track. Returns (success, message)."""
    try:
        from app.services.ingest import extract_and_store

        deezer_track = {
            "id": track_dict["deezer_id"],
            "title": track_dict["title"],
            "artist": {"name": track_dict["artist"], "id": track_dict.get("artist_id")},
            "album": {"title": track_dict.get("album")},
            "duration": track_dict.get("duration", 0),
            "preview": track_dict.get("preview_url"),
        }

        result = extract_and_store(deezer_track, expand_neighbors=False)
        if result:
            return True, f"{track_dict['artist']} — {track_dict['title']}"
        return False, f"Extraction failed: {track_dict['deezer_id']}"
    except Exception as exc:
        return False, f"Error {track_dict['deezer_id']}: {exc!s:.200}"


@router.post("/batch", response_model=BatchIngestResponse)
def batch_ingest(
    body: BatchIngestRequest,
    authorization: str | None = Header(None),
):
    """Ingest a batch of Deezer tracks: download preview → extract features → store in DB.

    Max 20 tracks per request. Runs extraction in parallel (2 workers).
    Protected by ADMIN_SECRET bearer token.
    """
    _verify_admin(authorization)

    if len(body.tracks) > MAX_BATCH_SIZE:
        raise HTTPException(400, f"Max {MAX_BATCH_SIZE} tracks per batch")

    if not body.tracks:
        return BatchIngestResponse(queued=0, succeeded=0, failed=0, errors=[])

    # Check which deezer_ids already exist
    from app.db import get_supabase

    sb = get_supabase()
    deezer_ids = [t.deezer_id for t in body.tracks]
    try:
        existing = sb.table("songs").select("deezer_id").in_("deezer_id", deezer_ids).execute()
        existing_ids = {r["deezer_id"] for r in (existing.data or [])}
    except Exception:
        existing_ids = set()

    # Filter out already-existing tracks
    new_tracks = [t for t in body.tracks if t.deezer_id not in existing_ids]
    skipped = len(body.tracks) - len(new_tracks)

    if not new_tracks:
        return BatchIngestResponse(
            queued=len(body.tracks),
            succeeded=skipped,  # Already existed
            failed=0,
            errors=[],
        )

    succeeded = skipped
    failed = 0
    errors: list[str] = []

    # Process sequentially (ProcessPoolExecutor causes fork issues in containers)
    for t in new_tracks:
        td = t.model_dump()
        ok, msg = _ingest_single(td)
        if ok:
            succeeded += 1
        else:
            failed += 1
            errors.append(msg)

    logger.info("Batch ingest: %d/%d succeeded, %d failed", succeeded, len(body.tracks), failed)
    return BatchIngestResponse(
        queued=len(body.tracks),
        succeeded=succeeded,
        failed=failed,
        errors=errors[:10],  # Limit error output
    )


@router.get("/status")
def ingest_status(authorization: str | None = Header(None)):
    """Get total song count in DB."""
    _verify_admin(authorization)
    from app.db import get_supabase

    sb = get_supabase()
    return {"status": "ok"}
