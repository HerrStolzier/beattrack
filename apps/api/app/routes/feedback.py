from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase

router = APIRouter(prefix="/feedback", tags=["feedback"])


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
