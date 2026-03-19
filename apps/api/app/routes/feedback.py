import hashlib
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase
from app.limiter import limiter

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
            }
        ).execute()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid song IDs")
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
