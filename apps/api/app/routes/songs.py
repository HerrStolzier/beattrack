import math

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase

router = APIRouter(prefix="/songs", tags=["songs"])


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards in user input."""
    return value.replace("%", r"\%").replace("_", r"\_")


class SongResponse(BaseModel):
    id: str
    title: str
    artist: str
    album: str | None
    bpm: float | None
    musical_key: str | None
    duration_sec: float | None
    genre: str | None = None
    deezer_id: int | None = None


class SongCount(BaseModel):
    count: int


@router.get("/count/total", response_model=SongCount)
async def get_song_count(
    sb: Client = Depends(get_supabase),
) -> SongCount:
    """Return total number of songs in the database."""
    result = sb.table("songs").select("id", count="exact").execute()
    return SongCount(count=result.count or 0)


@router.get("/genres", response_model=list[str])
async def list_genres(
    sb: Client = Depends(get_supabase),
) -> list[str]:
    """Return distinct genre values from the catalog."""
    result = sb.rpc(
        "get_distinct_genres", {}
    ).execute()
    return [row["genre"] for row in (result.data or []) if row.get("genre")]


@router.get("", response_model=list[SongResponse])
async def list_songs(
    q: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sb: Client = Depends(get_supabase),
) -> list[SongResponse]:
    query = sb.table("songs").select(
        "id, title, artist, album, bpm, musical_key, duration_sec, genre, deezer_id"
    )
    if q:
        escaped = _escape_like(q)
        query = query.or_(f"title.ilike.%{escaped}%,artist.ilike.%{escaped}%")
    if genre:
        query = query.eq("genre", genre)
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return [SongResponse(**row) for row in result.data]


@router.get("/{song_id}", response_model=SongResponse)
async def get_song(
    song_id: str,
    sb: Client = Depends(get_supabase),
) -> SongResponse:
    result = (
        sb.table("songs")
        .select("id, title, artist, album, bpm, musical_key, duration_sec, genre, deezer_id")
        .eq("id", song_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Song not found")
    return SongResponse(**result.data)


class RadarFeatures(BaseModel):
    timbre: float
    harmony: float
    rhythm: float
    brightness: float
    intensity: float


def _compute_radar(hc: list[float]) -> RadarFeatures:
    """Compute 5 radar categories from 44-dim handcrafted vector.

    Indices: MFCC mean [0:13], MFCC stdev [13:26], HPCP [26:38],
    spectral_centroid [38], spectral_rolloff [39], BPM [40],
    ZCR [41], average_loudness [42], danceability [43].
    """
    if len(hc) < 44:
        return RadarFeatures(timbre=0, harmony=0, rhythm=0, brightness=0, intensity=0)

    # Timbre: RMS of MFCC means (skip first = energy)
    mfcc = hc[1:13]
    timbre = math.sqrt(sum(x * x for x in mfcc) / len(mfcc))

    # Harmony: mean absolute HPCP
    hpcp = hc[26:38]
    harmony = sum(abs(x) for x in hpcp) / len(hpcp)

    # Rhythm: combine BPM (normalized to 0-1 range: 60-200) and danceability
    bpm_norm = max(0, min(1, (hc[40] - 60) / 140)) if hc[40] > 0 else 0
    dance = max(0, min(1, hc[43]))
    rhythm = 0.5 * bpm_norm + 0.5 * dance

    # Brightness: spectral centroid + rolloff
    brightness = 0.5 * max(0, min(1, hc[38])) + 0.5 * max(0, min(1, hc[39]))

    # Intensity: loudness + ZCR
    loudness = max(0, min(1, hc[42]))
    zcr = max(0, min(1, hc[41]))
    intensity = 0.6 * loudness + 0.4 * zcr

    return RadarFeatures(
        timbre=round(min(1, timbre), 3),
        harmony=round(min(1, harmony), 3),
        rhythm=round(rhythm, 3),
        brightness=round(brightness, 3),
        intensity=round(intensity, 3),
    )


@router.get("/{song_id}/features", response_model=RadarFeatures)
async def get_song_features(
    song_id: str,
    sb: Client = Depends(get_supabase),
) -> RadarFeatures:
    """Return 5-category radar features for a song."""
    result = (
        sb.table("songs")
        .select("handcrafted_norm")
        .eq("id", song_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Song not found")

    hc = result.data.get("handcrafted_norm")
    if not hc:
        raise HTTPException(status_code=422, detail="Song has no features")

    return _compute_radar(hc)


class BatchFeaturesRequest(BaseModel):
    song_ids: list[str]


class BatchFeaturesItem(BaseModel):
    song_id: str
    features: RadarFeatures


@router.post("/features/batch", response_model=list[BatchFeaturesItem])
async def get_batch_features(
    body: BatchFeaturesRequest,
    sb: Client = Depends(get_supabase),
) -> list[BatchFeaturesItem]:
    """Return radar features for multiple songs in one call (max 30)."""
    ids = body.song_ids[:30]
    result = (
        sb.table("songs")
        .select("id, handcrafted_norm")
        .in_("id", ids)
        .execute()
    )
    items = []
    for row in result.data or []:
        hc = row.get("handcrafted_norm")
        if hc:
            items.append(BatchFeaturesItem(
                song_id=str(row["id"]),
                features=_compute_radar(hc),
            ))
    return items
