import hashlib
import logging
from enum import Enum
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackStatsItem(BaseModel):
    query_song_id: str
    result_song_id: str
    total_up: int
    total_down: int
    net_score: int
    total_votes: int


class FeedbackRequest(BaseModel):
    query_song_id: str
    result_song_id: str
    rating: Literal[1, -1]
    focus: str | None = None
    ab_group: str | None = None


class ClickAction(str, Enum):
    PLAY = "play"
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    PLAYLIST = "playlist"
    SIMILAR = "similar"
    FEEDBACK_UP = "feedback_up"
    FEEDBACK_DOWN = "feedback_down"


class ClickEventRequest(BaseModel):
    session_hash: str
    query_song_id: str | None = None
    result_song_id: str | None = None
    result_rank: int | None = None
    ab_group: str
    action: ClickAction


@router.post("", status_code=201)
@limiter.limit("5/minute")
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    sb: Client = Depends(get_supabase),
) -> Response:
    # DSGVO-konform: SHA256-Hash, nur erste 16 Zeichen (nicht re-identifizierbar)
    ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]

    try:
        sb.table("feedback").insert(
            {
                "query_song_id": body.query_song_id,
                "result_song_id": body.result_song_id,
                "rating": body.rating,
                "ip_hash": ip_hash,
                "focus_active": body.focus,
                "ab_group": body.ab_group,
            }
        ).execute()
    except Exception as exc:
        logger.error("Feedback insert failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid song IDs")
    return Response(status_code=201)


@router.post("/click", status_code=201)
@limiter.limit("60/minute")
async def track_click(
    request: Request,
    body: ClickEventRequest,
    sb: Client = Depends(get_supabase),
) -> Response:
    """Track a user interaction for A/B testing CTR analysis."""
    try:
        sb.table("click_events").insert(
            {
                "session_hash": body.session_hash,
                "query_song_id": body.query_song_id,
                "result_song_id": body.result_song_id,
                "result_rank": body.result_rank,
                "ab_group": body.ab_group,
                "action": body.action,
            }
        ).execute()
    except Exception as exc:
        logger.debug("Click tracking failed (non-blocking): %s", exc)
    return Response(status_code=201)


class GenreFocusWeight(BaseModel):
    genre: str
    focus_category: str
    weight: float
    vote_count: int


@router.get("/weights", response_model=list[GenreFocusWeight])
async def get_genre_weights(
    genre: str | None = None,
    sb: Client = Depends(get_supabase),
) -> list[GenreFocusWeight]:
    """Get learned genre-specific focus weights from feedback data."""
    query = sb.table("genre_focus_weights").select("*")
    if genre:
        query = query.eq("genre", genre)
    result = query.order("genre").order("weight", desc=True).execute()
    return [GenreFocusWeight(**row) for row in (result.data or [])]


@router.get("/stats", response_model=list[FeedbackStatsItem])
async def get_feedback_stats(
    type: Literal["top", "flop"] = "top",
    limit: int = 20,
    sb: Client = Depends(get_supabase),
) -> list[FeedbackStatsItem]:
    """Get top-rated or worst-rated song pair matches."""
    result = (
        sb.table("feedback_stats")
        .select("*")
        .order("net_score", desc=(type == "top"))
        .limit(limit)
        .execute()
    )
    return [FeedbackStatsItem(**row) for row in (result.data or [])]
