"""Procrastinate job queue for async audio analysis."""
import logging
import os

import procrastinate

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get Postgres connection URL for Procrastinate.

    Uses Supavisor transaction mode (port 6543) for connection pooling.
    Falls back to DATABASE_URL if SUPABASE_DB_URL not set.
    """
    url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL", "")
    if not url:
        logger.warning("No database URL configured (SUPABASE_DB_URL or DATABASE_URL). "
                       "Procrastinate job queue will not function.")
    return url


# Procrastinate app — initialized lazily
app = procrastinate.App(
    connector=procrastinate.SyncPsycopgConnector(
        conninfo=get_database_url(),
    ),
    worker_defaults={
        "listen_notify": False,  # Saves 1 connection, uses polling (5s interval)
    },
)


def process_analysis_result(features: dict, job_id: str) -> dict:
    """Insert song into DB, run similarity search, return result.

    This is extracted from the task for testability.
    Errors in DB operations are caught and logged — they do not abort the job.
    """
    from app.db import get_supabase
    from app.services.features import normalize_handcrafted

    sb = get_supabase()

    # 1. Try to normalize handcrafted features using stats from config table
    handcrafted = features["handcrafted"]
    try:
        config_result = sb.table("config").select("value").eq("key", "normalization_stats").single().execute()
        if config_result.data:
            import json as _json
            raw_value = config_result.data["value"]
            stats = _json.loads(raw_value) if isinstance(raw_value, str) else raw_value
            handcrafted = normalize_handcrafted(features["handcrafted"], stats)
    except Exception as exc:
        logger.warning("Could not load normalization stats, using raw features: %s", exc)

    # 2. Insert song into songs table
    song_id = job_id  # Use job_id as song_id for simplicity
    song_data = {
        "id": song_id,
        "title": f"Upload {job_id[:8]}",
        "artist": "Unknown",
        "bpm": features["bpm"],
        "musical_key": features["key"],
        "duration_sec": features.get("duration", 0),
        "learned_embedding": features["learned"],
        "handcrafted_norm": handcrafted,
        "metadata_status": "uploaded",
    }

    try:
        sb.table("songs").insert(song_data).execute()
    except Exception as exc:
        logger.error("Failed to insert song %s: %s", song_id, exc)
        # Don't fail the whole job — still return features

    # 3. Find similar songs via RPC
    similar_songs = []
    try:
        rpc_result = sb.rpc("find_similar_songs", {
            "query_embedding": str(features["learned"]),
            "match_count": 20,
            "exclude_id": song_id,
        }).execute()
        similar_songs = [
            {
                "id": str(r["id"]),
                "title": r["title"],
                "artist": r["artist"],
                "album": r.get("album"),
                "bpm": r.get("bpm"),
                "similarity": float(r["similarity"]),
            }
            for r in (rpc_result.data or [])
        ]
    except Exception as exc:
        logger.error("Similarity search failed for %s: %s", song_id, exc)

    return {
        "song_id": song_id,
        "learned": features["learned"],
        "handcrafted": handcrafted,
        "bpm": features["bpm"],
        "key": features["key"],
        "duration": features.get("duration", 0),
        "similar_songs": similar_songs,
    }


@app.task(name="analyze_audio", retry=1, pass_context=True)
def analyze_audio(context, *, audio_path: str, job_id: str):
    """Main analysis task: extract features → normalize → insert into DB → find similar songs.

    This runs in the Procrastinate worker process, NOT in the FastAPI event loop.
    """
    from app.services.features import extract_features_safe, FeatureExtractionError

    logger.info("Starting analysis for job %s: %s", job_id, audio_path)

    from app.routes.analyze import update_job_status

    update_job_status(job_id, "processing", progress=0.1)

    # 1. Extract features via subprocess
    try:
        features = extract_features_safe(audio_path)
    except FeatureExtractionError as exc:
        logger.error("Feature extraction failed for job %s", job_id)
        update_job_status(job_id, "failed", error=str(exc))
        raise

    logger.info("Extraction complete for job %s: learned=%d dims, handcrafted=%d dims, bpm=%.1f",
                job_id, len(features["learned"]), len(features["handcrafted"]), features["bpm"])

    update_job_status(job_id, "processing", progress=0.8)

    # 2. Insert into DB + find similar songs
    try:
        result = process_analysis_result(features, job_id)
    except Exception as exc:
        logger.warning("DB processing failed, returning features only: %s", exc)
        result = {
            "learned": features["learned"],
            "handcrafted": features["handcrafted"],
            "bpm": features["bpm"],
            "key": features["key"],
            "duration": features.get("duration", 0),
            "similar_songs": [],
        }

    update_job_status(job_id, "completed", progress=1.0, result=result)
    return result
