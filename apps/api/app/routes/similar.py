import logging

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from supabase import Client

from app.db import get_supabase
from app.services.similarity import (
    OVERFETCH_FACTOR,
    VALID_FOCUS_CATEGORIES,
    _apply_discovery_score,
    _apply_late_fusion,
    _apply_mmr,
    _deduplicate_versions,
    _parse_vector,
)

logger = logging.getLogger(__name__)

MIN_SIMILARITY = 0.3

router = APIRouter(prefix="/similar", tags=["similar"])


class SimilarRequest(BaseModel):
    song_id: str
    limit: int = 20
    min_bpm: float | None = None
    max_bpm: float | None = None
    exclude_ids: list[str] = []
    focus: str | None = None

    @field_validator("focus")
    @classmethod
    def validate_focus(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_FOCUS_CATEGORIES:
            raise ValueError(f"Invalid focus: {v}. Valid: {', '.join(sorted(VALID_FOCUS_CATEGORIES))}")
        return v


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


@router.post("", response_model=list[SimilarSong])
async def find_similar(
    body: SimilarRequest,
    sb: Client = Depends(get_supabase),
) -> list[SimilarSong]:
    # 1. Fetch query song (including MERT embedding if available)
    song_result = (
        sb.table("songs")
        .select("id, title, artist, learned_embedding, handcrafted_norm, mert_embedding, genre")
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
    # Overfetch 3x to feed dedup + MMR diversity re-ranking
    exclude_set = set(body.exclude_ids)
    exclude_extra = min(len(exclude_set), 50)
    fetch_count = int(body.limit * OVERFETCH_FACTOR) + exclude_extra
    rpc_params: dict = {
        "query_embedding": str(embedding),
        "match_count": fetch_count,
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

    focus = body.focus

    # 3. Late fusion with handcrafted + MERT features
    query_handcrafted: list[float] | None = query_song.get("handcrafted_norm")
    query_mert = _parse_vector(query_song.get("mert_embedding"))
    if query_handcrafted and results:
        try:
            results = _apply_late_fusion(
                results, query_handcrafted, sb,
                focus=focus, query_genre=query_song.get("genre"),
                query_mert=query_mert,
            )
        except Exception as exc:
            logger.warning("Late fusion failed, returning learned-only results: %s", exc)

    # 4. Discovery scoring: less obvious, still sonically close
    results = _apply_discovery_score(results, query_song)

    # 5. Deduplicate remix/version variants (keep best per base track)
    results = _deduplicate_versions(results)

    # 6. MMR diversity re-ranking (use learned embeddings for inter-result distance)
    if len(results) > body.limit:
        result_ids = [str(r["id"]) for r in results]
        emb_result = (
            sb.table("songs")
            .select("id, learned_embedding")
            .in_("id", result_ids)
            .execute()
        )
        emb_map = {
            str(row["id"]): row["learned_embedding"]
            for row in (emb_result.data or [])
            if row.get("learned_embedding")
        }
        results = _apply_mmr(results, emb_map, body.limit)
    else:
        results = results[: body.limit]

    return _to_similar_songs(results)


def _to_similar_songs(results: list[dict]) -> list[SimilarSong]:
    """Convert raw result dicts to SimilarSong models, filtering by minimum similarity."""
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


def _fetch_embedding(sb: Client, song_id: str) -> tuple[list[float], list[float] | None]:
    """Fetch learned_embedding and handcrafted_norm for a song. Raises HTTPException on failure."""
    result = (
        sb.table("songs")
        .select("learned_embedding, handcrafted_norm")
        .eq("id", song_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    embedding = result.data.get("learned_embedding")
    if not embedding:
        raise HTTPException(status_code=422, detail=f"Song {song_id} has no embedding")
    return embedding, result.data.get("handcrafted_norm")


# ---------------------------------------------------------------------------
# Blend — find songs between two reference songs
# ---------------------------------------------------------------------------

class BlendRequest(BaseModel):
    song_id_a: str
    song_id_b: str
    limit: int = 20


@router.post("/blend", response_model=list[SimilarSong])
async def find_blend(
    body: BlendRequest,
    sb: Client = Depends(get_supabase),
) -> list[SimilarSong]:
    """Find songs sonically between two reference songs (centroid search)."""
    emb_a, hc_a = _fetch_embedding(sb, body.song_id_a)
    emb_b, hc_b = _fetch_embedding(sb, body.song_id_b)

    # Compute centroid of learned embeddings
    centroid = ((np.asarray(emb_a) + np.asarray(emb_b)) / 2).tolist()

    rpc_params: dict = {
        "query_embedding": str(centroid),
        "match_count": int(body.limit * OVERFETCH_FACTOR) + 2,  # overfetch for seeds + dedup + MMR
    }
    try:
        rpc_result = sb.rpc("find_similar_songs", rpc_params).execute()
    except Exception as exc:
        logger.error("Blend search failed: %s", exc)
        raise HTTPException(status_code=502, detail="Blend search failed")

    results = rpc_result.data or []
    # Exclude the two seed songs
    seed_ids = {body.song_id_a, body.song_id_b}
    results = [r for r in results if str(r["id"]) not in seed_ids]

    # Late fusion with centroid of handcrafted features
    if hc_a and hc_b and results:
        hc_centroid = ((np.asarray(hc_a) + np.asarray(hc_b)) / 2).tolist()
        try:
            results = _apply_late_fusion(results, hc_centroid, sb)
        except Exception as exc:
            logger.warning("Blend late fusion failed: %s", exc)

    results = _deduplicate_versions(results)
    return _to_similar_songs(results[: body.limit])


# ---------------------------------------------------------------------------
# Vibe — find songs similar to ALL of 2-5 seed songs (intersection search)
# ---------------------------------------------------------------------------

class VibeRequest(BaseModel):
    song_ids: list[str]
    limit: int = 20

    @field_validator("song_ids")
    @classmethod
    def validate_song_ids(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("At least 2 songs required")
        if len(v) > 5:
            raise ValueError("Maximum 5 songs allowed")
        return v


@router.post("/vibe", response_model=list[SimilarSong])
async def find_vibe(
    body: VibeRequest,
    sb: Client = Depends(get_supabase),
) -> list[SimilarSong]:
    """Find songs similar to ALL seed songs (intersection approach)."""
    seed_set = set(body.song_ids)

    # Fetch embeddings for all seeds
    embeddings: list[list[float]] = []
    for song_id in body.song_ids:
        emb, _ = _fetch_embedding(sb, song_id)
        embeddings.append(emb)

    # Search from each seed (broader search for intersection)
    per_seed_count = 100
    all_results: list[list[dict]] = []

    for emb in embeddings:
        rpc_params = {
            "query_embedding": str(emb),
            "match_count": per_seed_count,
        }
        try:
            rpc_result = sb.rpc("find_similar_songs", rpc_params).execute()
            all_results.append(rpc_result.data or [])
        except Exception as exc:
            logger.warning("Vibe search failed for one seed: %s", exc)
            all_results.append([])

    # Build intersection: songs appearing in at least 2 seed results
    song_scores: dict[str, list[float]] = {}
    song_data: dict[str, dict] = {}
    for result_list in all_results:
        for r in result_list:
            rid = str(r["id"])
            if rid in seed_set:
                continue
            if rid not in song_scores:
                song_scores[rid] = []
                song_data[rid] = r
            song_scores[rid].append(float(r.get("similarity", 0)))

    # Filter: must appear in at least 2 seed results
    min_appearances = min(2, len(body.song_ids))
    candidates = [
        {**song_data[rid], "similarity": min(scores)}  # worst-case similarity
        for rid, scores in song_scores.items()
        if len(scores) >= min_appearances
    ]
    candidates.sort(key=lambda x: x["similarity"], reverse=True)

    # Fallback: if intersection is too small, use centroid
    if len(candidates) < body.limit:
        centroid = np.mean(embeddings, axis=0).tolist()
        rpc_params = {
            "query_embedding": str(centroid),
            "match_count": body.limit + len(seed_set),
        }
        try:
            rpc_result = sb.rpc("find_similar_songs", rpc_params).execute()
            fallback = [r for r in (rpc_result.data or []) if str(r["id"]) not in seed_set]
            # Merge: existing candidates first, then fallback (deduped)
            existing_ids = {str(c["id"]) for c in candidates}
            for r in fallback:
                if str(r["id"]) not in existing_ids:
                    candidates.append(r)
                    if len(candidates) >= body.limit:
                        break
        except Exception as exc:
            logger.warning("Vibe centroid fallback failed: %s", exc)

    candidates = _deduplicate_versions(candidates)
    return _to_similar_songs(candidates[: body.limit])
