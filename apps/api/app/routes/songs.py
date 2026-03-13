from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase

router = APIRouter(prefix="/songs", tags=["songs"])


class SongResponse(BaseModel):
    id: str
    title: str
    artist: str
    album: str | None
    bpm: float | None
    musical_key: str | None
    duration_sec: float | None


@router.get("", response_model=list[SongResponse])
async def list_songs(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sb: Client = Depends(get_supabase),
) -> list[SongResponse]:
    query = sb.table("songs").select(
        "id, title, artist, album, bpm, musical_key, duration_sec"
    )
    if q:
        query = query.ilike("title", f"%{q}%")
    result = query.range(offset, offset + limit - 1).execute()
    return [SongResponse(**row) for row in result.data]


@router.get("/{song_id}", response_model=SongResponse)
async def get_song(
    song_id: str,
    sb: Client = Depends(get_supabase),
) -> SongResponse:
    result = (
        sb.table("songs")
        .select("id, title, artist, album, bpm, musical_key, duration_sec")
        .eq("id", song_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Song not found")
    return SongResponse(**result.data)
