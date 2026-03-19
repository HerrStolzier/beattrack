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


@router.post("", status_code=201)
@limiter.limit("30/minute")
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    sb: Client = Depends(get_supabase),
) -> Response:
    try:
        sb.table("feedback").insert(
            {
                "query_song_id": body.query_song_id,
                "result_song_id": body.result_song_id,
                "rating": body.rating,
            }
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Feedback failed: {exc}")
    return Response(status_code=201)


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
