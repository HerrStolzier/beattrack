import json
import logging
import re
import threading
import time
from dataclasses import dataclass

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from supabase import Client

from app.db import get_supabase

logger = logging.getLogger(__name__)

MIN_SIMILARITY = 0.3

# Overfetch factor: dedup + MMR need a larger candidate pool
_OVERFETCH_FACTOR = 3.0

# MMR diversity parameter: 1.0 = pure relevance, 0.0 = pure diversity
_MMR_LAMBDA = 0.7

# Regex to extract base title by stripping (...), [...], and common suffixes
_STRIP_PARENS = re.compile(r"\s*[\(\[].*?[\)\]]\s*")
_STRIP_SUFFIXES = re.compile(
    r"\s*[-–—]\s*(?:radio edit|extended|remix|original mix|club mix|dub mix|"
    r"instrumental|acoustic|live|remaster(?:ed)?|slowed|sped up|mix cut|mixed|"
    r"feat\..*|ft\..*)$",
    re.IGNORECASE,
)

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


def _parse_vector(raw) -> list[float] | None:
    """Parse a vector that may come as string from Supabase."""
    if raw is None:
        return None
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


@dataclass
class _FusionWeights:
    learned: float
    mert: float
    hc: float


def _determine_weights(
    focus: str | None,
    has_mert: bool,
    genre_weights: dict[str, float] | None,
) -> _FusionWeights:
    """Select fusion weights based on strategy priority."""
    if focus and focus in FOCUS_DIMENSIONS:
        if has_mert:
            return _FusionWeights(0.55, 0.15, 0.30)
        return _FusionWeights(0.60, 0.0, 0.40)

    if genre_weights:
        confidence = min(1.0, sum(genre_weights.values()) * 2)
        if has_mert:
            hc = 0.15 + (0.15 * confidence)
            return _FusionWeights(1.0 - hc - 0.15, 0.15, hc)
        hc = 0.2 + (0.2 * confidence)
        return _FusionWeights(1.0 - hc, 0.0, hc)

    if has_mert:
        return _FusionWeights(0.65, 0.15, 0.20)
    return _FusionWeights(0.80, 0.0, 0.20)


def _compute_hc_similarity(
    query_hc: list[float],
    result_hc: list[float],
    focus_dims: list[int] | None,
    genre_weights: dict[str, float] | None,
) -> float:
    """Compute handcrafted similarity using the appropriate strategy."""
    if focus_dims:
        return _cosine_similarity(
            _extract_dims(query_hc, focus_dims),
            _extract_dims(result_hc, focus_dims),
        )

    if genre_weights:
        default_w = 1.0 / len(FOCUS_DIMENSIONS)
        raw = {cat: genre_weights.get(cat, default_w) for cat in FOCUS_DIMENSIONS}
        total = sum(raw.values())
        norm = {cat: w / total for cat, w in raw.items()} if total > 0 else raw
        sim = 0.0
        for cat, dims in FOCUS_DIMENSIONS.items():
            sim += norm[cat] * _cosine_similarity(
                _extract_dims(query_hc, dims),
                _extract_dims(result_hc, dims),
            )
        return sim

    return _cosine_similarity(query_hc, result_hc)


def _apply_late_fusion(
    results: list[dict],
    query_handcrafted: list[float],
    sb: Client,
    focus: str | None = None,
    query_genre: str | None = None,
    query_mert: list[float] | None = None,
) -> list[dict]:
    """Blend learned, handcrafted, and MERT similarities.

    Tri-signal fusion: score = α·MusiCNN + β·MERT + γ·Handcrafted
    Falls back to dual fusion when MERT is unavailable.
    """
    result_ids = [str(r["id"]) for r in results]

    # Fetch handcrafted + MERT embeddings in one query
    vec_result = (
        sb.table("songs")
        .select("id, handcrafted_norm, mert_embedding")
        .in_("id", result_ids)
        .execute()
    )
    hc_map: dict[str, list[float]] = {}
    mert_map: dict[str, list[float]] = {}
    for row in vec_result.data or []:
        rid = str(row["id"])
        hc = _parse_vector(row.get("handcrafted_norm"))
        if hc:
            hc_map[rid] = hc
        mert = _parse_vector(row.get("mert_embedding"))
        if mert:
            mert_map[rid] = mert

    has_mert = bool(query_mert and mert_map)
    genre_weights = _get_genre_weights(sb, query_genre) if not focus else None
    weights = _determine_weights(focus, has_mert, genre_weights)
    focus_dims = FOCUS_DIMENSIONS.get(focus) if focus else None

    fused: list[dict] = []
    for row in results:
        rid = str(row["id"])
        learned_sim: float = row.get("similarity", 0.0)
        hc_vec = hc_map.get(rid)

        if not hc_vec:
            fused.append({**row, "similarity": learned_sim})
            continue

        hc_sim = _compute_hc_similarity(query_handcrafted, hc_vec, focus_dims, genre_weights)

        mert_sim = 0.0
        if has_mert:
            result_mert = mert_map.get(rid)
            if result_mert and query_mert:
                mert_sim = _cosine_similarity(query_mert, result_mert)

        fused_score = weights.learned * learned_sim + weights.mert * mert_sim + weights.hc * hc_sim
        fused.append({**row, "similarity": fused_score})

    fused.sort(key=lambda x: x["similarity"], reverse=True)
    return fused


def _base_title(title: str) -> str:
    """Strip remix/version suffixes to get the canonical base title."""
    t = _STRIP_PARENS.sub("", title)
    t = _STRIP_SUFFIXES.sub("", t)
    return t.strip().lower()


def _deduplicate_versions(results: list[dict]) -> list[dict]:
    """Keep only the highest-scoring version per base track (artist + base title).

    Remix variants like "Café Del Mar (Deadmau5 Remix)" and "Café Del Mar (Orbital Remix)"
    collapse to a single entry — the one with the best similarity score.
    Results must be pre-sorted by similarity descending.
    """
    seen: dict[str, dict] = {}  # key: "artist||base_title" → best result
    deduped: list[dict] = []

    for r in results:
        key = f"{r['artist'].lower()}||{_base_title(r['title'])}"
        if key not in seen:
            seen[key] = r
            deduped.append(r)
        # else: skip — first occurrence has highest score (pre-sorted)

    return deduped


def _apply_mmr(
    results: list[dict],
    embeddings: dict[str, list[float]],
    limit: int,
    lambda_: float = _MMR_LAMBDA,
) -> list[dict]:
    """Re-rank results using Maximal Marginal Relevance for diversity.

    MMR(d) = λ * Sim(query, d) - (1-λ) * max(Sim(d, d_already_selected))

    This ensures results are both relevant AND diverse — avoids returning
    5 songs that all sound identical to each other.
    """
    if len(results) <= limit or not embeddings:
        return results[:limit]

    # Precompute normalized embedding vectors for fast cosine
    emb_cache: dict[str, np.ndarray] = {}
    for r in results:
        rid = str(r["id"])
        raw = embeddings.get(rid)
        if raw is not None:
            emb = json.loads(raw) if isinstance(raw, str) else raw
            vec = np.asarray(emb, dtype=np.float64)
            norm = np.linalg.norm(vec)
            emb_cache[rid] = vec / norm if norm > 0 else vec

    # Start with the highest-scoring result
    selected: list[dict] = [results[0]]
    candidates = list(results[1:])

    while len(selected) < limit and candidates:
        best_score = -float("inf")
        best_idx = 0

        for i, cand in enumerate(candidates):
            cid = str(cand["id"])
            relevance = float(cand.get("similarity", 0))

            # Max similarity to any already-selected result
            cand_emb = emb_cache.get(cid)
            if cand_emb is not None:
                max_sim_to_selected = max(
                    (float(np.dot(cand_emb, emb_cache[str(s["id"])]))
                     for s in selected if str(s["id"]) in emb_cache),
                    default=0.0,
                )
            else:
                max_sim_to_selected = 0.0

            mmr_score = lambda_ * relevance - (1 - lambda_) * max_sim_to_selected

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i

        selected.append(candidates.pop(best_idx))

    return selected


@router.post("", response_model=list[SimilarSong])
async def find_similar(
    body: SimilarRequest,
    sb: Client = Depends(get_supabase),
) -> list[SimilarSong]:
    # 1. Fetch query song (including MERT embedding if available)
    song_result = (
        sb.table("songs")
        .select("id, learned_embedding, handcrafted_norm, mert_embedding, genre")
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
    fetch_count = int(body.limit * _OVERFETCH_FACTOR) + exclude_extra
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

    # 4. Deduplicate remix/version variants (keep best per base track)
    results = _deduplicate_versions(results)

    # 5. MMR diversity re-ranking (use learned embeddings for inter-result distance)
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
        "match_count": int(body.limit * _OVERFETCH_FACTOR) + 2,  # overfetch for seeds + dedup + MMR
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
