import logging
import threading
import time

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from supabase import Client

from app.db import get_supabase

logger = logging.getLogger(__name__)

MIN_SIMILARITY = 0.3

# ---------------------------------------------------------------------------
# Genre-specific focus weights cache (Phase 1: Feature Importance Learning)
# ---------------------------------------------------------------------------
_genre_weights_lock = threading.Lock()
_genre_weights_cache: dict[str, dict[str, float]] = {}
_genre_weights_ts: float = 0
_GENRE_WEIGHTS_TTL = 300  # 5 minutes


def _get_genre_weights(sb: Client, genre: str | None) -> dict[str, float] | None:
    """Load genre-specific focus weights from materialized view (cached 5 min)."""
    global _genre_weights_cache, _genre_weights_ts

    if genre is None:
        return None

    now = time.time()
    if now - _genre_weights_ts > _GENRE_WEIGHTS_TTL:
        with _genre_weights_lock:
            # Double-checked locking: another thread may have updated while we waited
            if now - _genre_weights_ts > _GENRE_WEIGHTS_TTL:
                try:
                    result = sb.table("genre_focus_weights").select("*").execute()
                    new_cache: dict[str, dict[str, float]] = {}
                    for row in result.data or []:
                        g = row["genre"]
                        if g not in new_cache:
                            new_cache[g] = {}
                        new_cache[g][row["focus_category"]] = float(row["weight"])
                    _genre_weights_cache = new_cache
                    _genre_weights_ts = now
                    if new_cache:
                        logger.info("Loaded genre focus weights for %d genres", len(new_cache))
                except Exception as exc:
                    logger.debug("Could not load genre_focus_weights: %s", exc)
                    _genre_weights_ts = now  # don't retry immediately

    return _genre_weights_cache.get(genre)

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
    query_genre: str | None = None,
) -> list[dict]:
    """Blend learned_similarity with handcrafted cosine similarity.

    Priority order:
    1. Explicit focus → 60/40 on focused dimensions only
    2. Genre weights from feedback → weighted per-category fusion (adaptive 20-40% hc)
    3. Default → 80/20 flat fusion
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

    # --- Determine fusion strategy ---
    genre_weights = None
    if focus and focus in FOCUS_DIMENSIONS:
        # Strategy 1: Explicit focus → 60/40 on subset
        learned_weight, hc_weight = 0.6, 0.4
        focus_dims = FOCUS_DIMENSIONS[focus]
        query_vec = _extract_dims(query_handcrafted, focus_dims)
    else:
        focus_dims = None
        query_vec = query_handcrafted
        # Strategy 2: Genre-learned weights (Phase 1 Feature Importance)
        genre_weights = _get_genre_weights(sb, query_genre)
        if genre_weights:
            # Confidence: more votes → trust handcrafted more (20-40%)
            confidence = min(1.0, sum(genre_weights.values()) * 2)
            hc_weight = 0.2 + (0.2 * confidence)
            learned_weight = 1.0 - hc_weight
        else:
            # Strategy 3: Default flat fusion
            learned_weight, hc_weight = 0.8, 0.2

    fused: list[dict] = []
    for row in results:
        learned_sim: float = row.get("similarity", 0.0)
        hc_vec = hc_map.get(str(row["id"]))
        if not hc_vec:
            fused.append({**row, "similarity": learned_sim})
            continue

        if focus_dims:
            # Single-focus: compare only focused dimensions
            result_vec = _extract_dims(hc_vec, focus_dims)
            hc_sim = _cosine_similarity(query_vec, result_vec)
        elif genre_weights:
            # Genre-weighted: per-category similarity, weighted by feedback
            # Normalize weights to sum to 1.0 to prevent score inflation
            default_w = 1.0 / len(FOCUS_DIMENSIONS)
            raw_weights = {cat: genre_weights.get(cat, default_w) for cat in FOCUS_DIMENSIONS}
            total_w = sum(raw_weights.values())
            norm_weights = {cat: w / total_w for cat, w in raw_weights.items()} if total_w > 0 else raw_weights
            hc_sim = 0.0
            for cat, cat_dims in FOCUS_DIMENSIONS.items():
                q_sub = _extract_dims(query_handcrafted, cat_dims)
                r_sub = _extract_dims(hc_vec, cat_dims)
                hc_sim += norm_weights[cat] * _cosine_similarity(q_sub, r_sub)
        else:
            # Flat: full-vector comparison
            hc_sim = _cosine_similarity(query_vec, hc_vec)

        fused_score = learned_weight * learned_sim + hc_weight * hc_sim
        fused.append({**row, "similarity": fused_score})

    fused.sort(key=lambda x: x["similarity"], reverse=True)
    return fused


@router.post("", response_model=list[SimilarSong])
async def find_similar(
    body: SimilarRequest,
    sb: Client = Depends(get_supabase),
) -> list[SimilarSong]:
    # 1. Fetch query song
    song_result = (
        sb.table("songs")
        .select("id, learned_embedding, handcrafted_norm, genre")
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

    focus = body.focus

    # 3. Late fusion with handcrafted features
    query_handcrafted: list[float] | None = query_song.get("handcrafted_norm")
    if query_handcrafted and results:
        try:
            results = _apply_late_fusion(results, query_handcrafted, sb, focus=focus, query_genre=query_song.get("genre"))
        except Exception as exc:
            logger.warning("Late fusion failed, returning learned-only results: %s", exc)

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
        "match_count": body.limit + 2,  # overfetch to exclude seeds
    }
    try:
        rpc_result = sb.rpc("find_similar_songs", rpc_params).execute()
    except Exception as exc:
        logger.error("Blend search failed: %s", exc)
        raise HTTPException(status_code=502, detail="Blend search failed")

    results = rpc_result.data or []
    # Exclude the two seed songs
    seed_ids = {body.song_id_a, body.song_id_b}
    results = [r for r in results if str(r["id"]) not in seed_ids][: body.limit]

    # Late fusion with centroid of handcrafted features
    if hc_a and hc_b and results:
        hc_centroid = ((np.asarray(hc_a) + np.asarray(hc_b)) / 2).tolist()
        try:
            results = _apply_late_fusion(results, hc_centroid, sb)
        except Exception as exc:
            logger.warning("Blend late fusion failed: %s", exc)

    return _to_similar_songs(results)


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

    return _to_similar_songs(candidates[: body.limit])
