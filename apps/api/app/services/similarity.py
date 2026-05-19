"""Similarity ranking helpers shared by routes and evaluation scripts.

The functions in this module are intentionally free of FastAPI concerns. They
own score blending, discovery penalties, remix/version deduplication, and MMR
diversity so the route can stay focused on HTTP and database flow.
"""

import json
import logging
import re
import threading
import time
from dataclasses import dataclass

import numpy as np
from supabase import Client

logger = logging.getLogger(__name__)

# Overfetch factor: dedup + MMR need a larger candidate pool
OVERFETCH_FACTOR = 3.0

# MMR diversity parameter: 1.0 = pure relevance, 0.0 = pure diversity
MMR_LAMBDA = 0.7

# Discovery scoring keeps sonic fit as the main signal, but gently reduces
# candidates that are likely to feel too obvious in the primary discovery list.
SAME_ARTIST_PENALTY = 0.06
SAME_TITLE_PENALTY = 0.08
TOO_CLOSE_THRESHOLD = 0.94
TOO_CLOSE_MAX_PENALTY = 0.04

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


_FUSION_WEIGHT_STRATEGIES: dict[str, dict[str, _FusionWeights]] = {
    "balanced": {
        "default_no_mert": _FusionWeights(0.80, 0.0, 0.20),
        "default_with_mert": _FusionWeights(0.65, 0.15, 0.20),
        "focus_no_mert": _FusionWeights(0.60, 0.0, 0.40),
        "focus_with_mert": _FusionWeights(0.55, 0.15, 0.30),
    },
    "acoustic": {
        "default_no_mert": _FusionWeights(0.70, 0.0, 0.30),
        "default_with_mert": _FusionWeights(0.55, 0.20, 0.25),
        "focus_no_mert": _FusionWeights(0.50, 0.0, 0.50),
        "focus_with_mert": _FusionWeights(0.45, 0.20, 0.35),
    },
    "embedding": {
        "default_no_mert": _FusionWeights(0.90, 0.0, 0.10),
        "default_with_mert": _FusionWeights(0.75, 0.15, 0.10),
        "focus_no_mert": _FusionWeights(0.70, 0.0, 0.30),
        "focus_with_mert": _FusionWeights(0.65, 0.15, 0.20),
    },
}


def _determine_weights(
    focus: str | None,
    has_mert: bool,
    genre_weights: dict[str, float] | None,
    strategy: str = "balanced",
) -> _FusionWeights:
    """Select fusion weights based on strategy priority."""
    strategy_weights = _FUSION_WEIGHT_STRATEGIES.get(strategy, _FUSION_WEIGHT_STRATEGIES["balanced"])

    if focus and focus in FOCUS_DIMENSIONS:
        if has_mert:
            return strategy_weights["focus_with_mert"]
        return strategy_weights["focus_no_mert"]

    if genre_weights:
        confidence = min(1.0, sum(genre_weights.values()) * 2)
        base = strategy_weights["default_with_mert" if has_mert else "default_no_mert"]
        if has_mert:
            hc = base.hc + (0.10 * confidence)
            return _FusionWeights(1.0 - hc - base.mert, base.mert, hc)
        hc = base.hc + (0.20 * confidence)
        return _FusionWeights(1.0 - hc, 0.0, hc)

    if has_mert:
        return strategy_weights["default_with_mert"]
    return strategy_weights["default_no_mert"]


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
    strategy: str = "balanced",
) -> list[dict]:
    """Blend learned, handcrafted, and MERT similarities.

    Tri-signal fusion: score = alpha*MusiCNN + beta*MERT + gamma*Handcrafted.
    Falls back to dual fusion when MERT is unavailable.
    """
    result_ids = [str(r["id"]) for r in results]

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
    weights = _determine_weights(focus, has_mert, genre_weights, strategy=strategy)
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
    seen: dict[str, dict] = {}  # key: "artist||base_title" -> best result
    deduped: list[dict] = []

    for r in results:
        key = f"{r['artist'].lower()}||{_base_title(r['title'])}"
        if key not in seen:
            seen[key] = r
            deduped.append(r)

    return deduped


def _apply_discovery_score(results: list[dict], query_song: dict) -> list[dict]:
    """Re-rank toward less obvious songs that still fit sonically.

    The incoming similarity score remains the relevance anchor. Penalties are
    intentionally small so a clearly better sonic match can still win.
    """
    query_artist = str(query_song.get("artist") or "").strip().lower()
    query_title = _base_title(str(query_song.get("title") or ""))

    scored: list[dict] = []
    for row in results:
        sonic_similarity = float(row.get("similarity", 0.0))
        penalty = 0.0
        reasons: list[str] = []

        artist = str(row.get("artist") or "").strip().lower()
        if query_artist and artist == query_artist:
            penalty += SAME_ARTIST_PENALTY
            reasons.append("same_artist")

        title = _base_title(str(row.get("title") or ""))
        if query_title and title == query_title:
            penalty += SAME_TITLE_PENALTY
            reasons.append("same_title")

        if sonic_similarity > TOO_CLOSE_THRESHOLD:
            excess = min(1.0, (sonic_similarity - TOO_CLOSE_THRESHOLD) / (1.0 - TOO_CLOSE_THRESHOLD))
            penalty += excess * TOO_CLOSE_MAX_PENALTY
            reasons.append("too_close")

        scored.append({
            **row,
            "similarity": max(0.0, sonic_similarity - penalty),
            "sonic_similarity": sonic_similarity,
            "discovery_penalty": penalty,
            "discovery_penalty_reasons": reasons,
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored


def _apply_mmr(
    results: list[dict],
    embeddings: dict[str, list[float]],
    limit: int,
    lambda_: float = MMR_LAMBDA,
) -> list[dict]:
    """Re-rank results using Maximal Marginal Relevance for diversity.

    MMR(d) = lambda * Sim(query, d) - (1-lambda) * max(Sim(d, d_already_selected))

    This keeps results both relevant and diverse.
    """
    if len(results) <= limit or not embeddings:
        return results[:limit]

    emb_cache: dict[str, np.ndarray] = {}
    for r in results:
        rid = str(r["id"])
        raw = embeddings.get(rid)
        if raw is not None:
            emb = json.loads(raw) if isinstance(raw, str) else raw
            vec = np.asarray(emb, dtype=np.float64)
            norm = np.linalg.norm(vec)
            emb_cache[rid] = vec / norm if norm > 0 else vec

    selected: list[dict] = [results[0]]
    candidates = list(results[1:])

    while len(selected) < limit and candidates:
        best_score = -float("inf")
        best_idx = 0

        for i, cand in enumerate(candidates):
            cid = str(cand["id"])
            relevance = float(cand.get("similarity", 0))

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
