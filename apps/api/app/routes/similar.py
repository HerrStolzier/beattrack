import logging
import math

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client

logger = logging.getLogger(__name__)

from app.db import get_supabase

router = APIRouter(prefix="/similar", tags=["similar"])


class SimilarRequest(BaseModel):
    song_id: str
    limit: int = 20
    min_bpm: float | None = None
    max_bpm: float | None = None


class SimilarSong(BaseModel):
    id: str
    title: str
    artist: str
    album: str | None
    bpm: float | None
    similarity: float


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@router.post("", response_model=list[SimilarSong])
async def find_similar(
    body: SimilarRequest,
    sb: Client = Depends(get_supabase),
) -> list[SimilarSong]:
    # 1. Fetch query song's learned_embedding and handcrafted_norm
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

    # Convert embedding to the string format expected by the DB function
    embedding_str = str(embedding)

    # 2. Call find_similar_songs via RPC
    rpc_params: dict = {
        "query_embedding": embedding_str,
        "match_count": body.limit,
        "exclude_id": body.song_id,
    }
    if body.min_bpm is not None:
        rpc_params["min_bpm"] = body.min_bpm
    if body.max_bpm is not None:
        rpc_params["max_bpm"] = body.max_bpm

    try:
        rpc_result = sb.rpc("find_similar_songs", rpc_params).execute()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Similarity search failed: {exc}")
    results = rpc_result.data or []

    # 3. Late Fusion: blend learned_similarity with handcrafted cosine similarity
    try:
        query_handcrafted: list[float] | None = query_song.get("handcrafted_norm")

        if query_handcrafted and results:
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

            fused: list[dict] = []
            for row in results:
                learned_sim: float = row.get("similarity", 0.0)
                hc_vec = hc_map.get(str(row["id"]))
                if hc_vec:
                    hc_sim = _cosine_similarity(query_handcrafted, hc_vec)
                    fused_score = 0.8 * learned_sim + 0.2 * hc_sim
                else:
                    fused_score = learned_sim
                fused.append({**row, "similarity": fused_score})

            # 4. Re-sort by fused score
            fused.sort(key=lambda x: x["similarity"], reverse=True)
            results = fused
    except Exception as exc:
        logger.warning("Late fusion failed, returning learned-only results: %s", exc)

    return [
        SimilarSong(
            id=str(r["id"]),
            title=r["title"],
            artist=r["artist"],
            album=r.get("album"),
            bpm=r.get("bpm"),
            similarity=float(r["similarity"]),
        )
        for r in results
    ]
