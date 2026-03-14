from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase

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
async def submit_feedback(
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
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid song IDs")
    return Response(status_code=201)


@router.get("/stats", response_model=list[FeedbackStatsItem])
async def get_feedback_stats(
    type: Literal["top", "flop"] = "top",
    limit: int = 20,
    sb: Client = Depends(get_supabase),
) -> list[FeedbackStatsItem]:
    """Get top-rated or worst-rated song pair matches."""
    # Try to refresh the materialized view (ignore errors if no data yet)
    try:
        sb.rpc("refresh_feedback_stats", {}).execute()
    except Exception:
        pass

    result = (
        sb.table("feedback_stats")
        .select("*")
        .order("net_score", desc=(type == "top"))
        .limit(limit)
        .execute()
    )
    return [FeedbackStatsItem(**row) for row in (result.data or [])]
