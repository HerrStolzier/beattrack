import logging
import os

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase

logger = logging.getLogger(__name__)

FEEDBACK_BOOST_ENABLED = os.getenv("FEEDBACK_BOOST", "").lower() in ("true", "1", "yes")
POSITIVE_BOOST = 0.05
NEGATIVE_PENALTY = 0.03
MIN_SIMILARITY = 0.3

router = APIRouter(prefix="/similar", tags=["similar"])


VALID_FOCUS_CATEGORIES = {"timbre", "harmony", "rhythm", "brightness", "intensity"}

# Mapping of focus categories to handcrafted_norm dimension indices
# Based on the 44-dim handcrafted vector layout:
#   [0:13]  MFCC mean, [13:26] MFCC stdev, [26:38] HPCP 12-bin,
#   [38] Spectral Centroid, [39] Spectral Rolloff, [40] BPM,
#   [41] ZCR, [42] Avg Loudness, [43] Danceability
FOCUS_DIMENSIONS: dict[str, list[int]] = {
    "timbre": list(range(0, 26)),       # MFCC mean + stdev (26 dims)
    "harmony": list(range(26, 38)),     # HPCP 12-bin (12 dims)
    "rhythm": [40, 43],                 # BPM + Danceability
    "brightness": [38, 39],             # Spectral Centroid + Rolloff
    "intensity": [41, 42],              # ZCR + Avg Loudness
}


class SimilarRequest(BaseModel):
    song_id: str
    limit: int = 20
    min_bpm: float | None = None
    max_bpm: float | None = None
    exclude_ids: list[str] = []
    focus: str | None = None


class SimilarSong(BaseModel):
    id: str
    title: str
    artist: str
    album: str | None
    bpm: float | None
    musical_key: str | None = None
    duration_sec: float | None = None
    genre: str | None = None
    deezer_id: int | None = None
    similarity: float


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors using numpy."""
    a_arr, b_arr = np.asarray(a), np.asarray(b)
    norm_a, norm_b = np.linalg.norm(a_arr), np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


def _extract_dims(vec: list[float], dims: list[int]) -> list[float]:
    """Extract specific dimension indices from a vector."""
    return [vec[i] for i in dims if i < len(vec)]


def _apply_late_fusion(
    results: list[dict],
    query_handcrafted: list[float],
    sb: Client,
    focus: str | None = None,
) -> list[dict]:
    """Blend learned_similarity with handcrafted cosine similarity.

    Default: 80/20 fusion.
    With focus: 60/40 fusion using only the focused feature dimensions.
    """
    result_ids = [str(r["id"]) for r in results]
    hc_result = (
        sb.table("songs")
        .select("id, handcrafted_norm")
        .in_("id", result_ids)
        .execute()
    )
    hc_map: dict[str, list[float]] = {
        str(row["id"]): row["handcrafted_norm"]
        for row in (hc_result.data or [])
        if row.get("handcrafted_norm")
    }

    # Determine fusion weights and dimensions
    if focus and focus in FOCUS_DIMENSIONS:
        learned_weight, hc_weight = 0.6, 0.4
        focus_dims = FOCUS_DIMENSIONS[focus]
        query_vec = _extract_dims(query_handcrafted, focus_dims)
    else:
        learned_weight, hc_weight = 0.8, 0.2
        query_vec = query_handcrafted
        focus_dims = None

    fused: list[dict] = []
    for row in results:
        learned_sim: float = row.get("similarity", 0.0)
        hc_vec = hc_map.get(str(row["id"]))
        if hc_vec:
            result_vec = _extract_dims(hc_vec, focus_dims) if focus_dims else hc_vec
            hc_sim = _cosine_similarity(query_vec, result_vec)
            fused_score = learned_weight * learned_sim + hc_weight * hc_sim
        else:
            fused_score = learned_sim
        fused.append({**row, "similarity": fused_score})

    fused.sort(key=lambda x: x["similarity"], reverse=True)
    return fused


def _apply_feedback_boost(
    results: list[dict],
    query_song_id: str,
    sb: Client,
) -> list[dict]:
    """Adjust similarity scores based on user feedback."""
    result_ids = [str(r["id"]) for r in results]
    fb_result = (
        sb.table("feedback_stats")
        .select("result_song_id, net_score")
        .eq("query_song_id", query_song_id)
        .in_("result_song_id", result_ids)
        .execute()
    )
    fb_map: dict[str, int] = {
        str(row["result_song_id"]): row["net_score"]
        for row in (fb_result.data or [])
    }

    for r in results:
        net = fb_map.get(str(r["id"]), 0)
        if net > 0:
            r["similarity"] = min(1.0, r["similarity"] + POSITIVE_BOOST)
        elif net < 0:
            r["similarity"] = max(0.0, r["similarity"] - NEGATIVE_PENALTY)

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results


@router.post("", response_model=list[SimilarSong])
async def find_similar(
    body: SimilarRequest,
    sb: Client = Depends(get_supabase),
) -> list[SimilarSong]:
    # 1. Fetch query song
    song_result = (
        sb.table("songs")
        .select("id, learned_embedding, handcrafted_norm")
        .eq("id", body.song_id)
        .single()
        .execute()
    )
    if not song_result.data:
        raise HTTPException(status_code=404, detail="Song not found")

    query_song = song_result.data
    embedding = query_song.get("learned_embedding")
    if not embedding:
        raise HTTPException(status_code=422, detail="Song has no embedding")

    # 2. Vector similarity search via RPC
    # Fetch extra results to compensate for exclude_ids filtering
    exclude_set = set(body.exclude_ids)
    overfetch = min(len(exclude_set), 50)  # cap to avoid excessive queries
    rpc_params: dict = {
        "query_embedding": str(embedding),
        "match_count": body.limit + overfetch,
        "exclude_id": body.song_id,
    }
    if body.min_bpm is not None:
        rpc_params["min_bpm"] = body.min_bpm
    if body.max_bpm is not None:
        rpc_params["max_bpm"] = body.max_bpm

    try:
        rpc_result = sb.rpc("find_similar_songs", rpc_params).execute()
    except Exception as exc:
        logger.error("Similarity search failed: %s", exc)
        raise HTTPException(status_code=502, detail="Similarity search failed")
    results = rpc_result.data or []

    # Filter out excluded IDs (for chain discovery / journey mode)
    if exclude_set:
        results = [r for r in results if str(r["id"]) not in exclude_set]
    results = results[: body.limit]

    # Validate focus parameter
    focus = body.focus
    if focus and focus not in VALID_FOCUS_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Invalid focus: {focus}. Valid: {', '.join(sorted(VALID_FOCUS_CATEGORIES))}")

    # 3. Late fusion with handcrafted features
    query_handcrafted: list[float] | None = query_song.get("handcrafted_norm")
    if query_handcrafted and results:
        try:
            results = _apply_late_fusion(results, query_handcrafted, sb, focus=focus)
        except Exception as exc:
            logger.warning("Late fusion failed, returning learned-only results: %s", exc)

    # 4. Optional feedback-based score adjustment
    if FEEDBACK_BOOST_ENABLED and results:
        try:
            results = _apply_feedback_boost(results, body.song_id, sb)
        except Exception as exc:
            logger.warning("Feedback boost failed: %s", exc)

    return [
        SimilarSong(
            id=str(r["id"]),
            title=r["title"],
            artist=r["artist"],
            album=r.get("album"),
            bpm=r.get("bpm"),
            musical_key=r.get("musical_key"),
            duration_sec=r.get("duration_sec"),
            genre=r.get("genre"),
            deezer_id=r.get("deezer_id"),
            similarity=float(r["similarity"]),
        )
        for r in results
        if float(r["similarity"]) >= MIN_SIMILARITY
    ]
