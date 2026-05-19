"""Import-safe analysis worker logic."""

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


def process_analysis_result(features: dict, job_id: str, audio_path: str = "") -> dict:
    """Insert song into DB, run similarity search, return result.

    Errors in DB operations are caught and logged. They do not abort the job.
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

    # 2. AcoustID fingerprinting + MusicBrainz metadata enrichment
    song_title = f"Upload {job_id[:8]}"
    song_artist = "Unknown"
    song_album = None
    musicbrainz_id = None

    if audio_path:
        try:
            import os as _os

            from app.services.acoustid import fingerprint_file
            from app.services.acoustid import lookup as acoustid_lookup
            from app.services.musicbrainz import lookup_recording

            api_key = _os.environ.get("ACOUSTID_API_KEY", "")
            fp_result = fingerprint_file(audio_path)
            if fp_result is not None and api_key:
                fingerprint, duration = fp_result
                mbid = acoustid_lookup(fingerprint, duration, api_key)
                if mbid:
                    mb_data = lookup_recording(mbid)
                    if mb_data:
                        musicbrainz_id = mbid
                        song_title = mb_data.get("title") or song_title
                        song_artist = mb_data.get("artist") or song_artist
                        song_album = mb_data.get("album") or None
                        logger.info(
                            "AcoustID resolved job %s -> MBID %s (%s - %s)",
                            job_id, mbid, song_artist, song_title,
                        )
        except Exception as exc:
            logger.warning("AcoustID/MusicBrainz enrichment failed for job %s: %s", job_id, exc)

    # 3. Insert song into songs table
    song_id = job_id
    song_data: dict = {
        "id": song_id,
        "title": song_title,
        "artist": song_artist,
        "bpm": features["bpm"],
        "musical_key": features["key"],
        "duration_sec": features.get("duration", 0),
        "learned_embedding": features["learned"],
        "handcrafted_norm": handcrafted,
        "metadata_status": "uploaded",
    }
    if song_album is not None:
        song_data["album"] = song_album
    if musicbrainz_id is not None:
        song_data["musicbrainz_id"] = musicbrainz_id

    try:
        sb.table("songs").insert(song_data).execute()
    except Exception as exc:
        logger.error("Failed to insert song %s: %s", song_id, exc)

    # 4. Find similar songs via RPC
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


def run_analysis_task(
    *,
    audio_path: str,
    job_id: str,
    process_result: Callable[[dict, str, str], dict] = process_analysis_result,
) -> dict:
    """Run audio extraction, persistence updates, and result assembly."""
    from app.services.analysis_jobs import mark_analysis_job_processing, update_analysis_job
    from app.services.features import FeatureExtractionError, extract_features_safe

    logger.info("Starting analysis for job %s: %s", job_id, audio_path)
    mark_analysis_job_processing(job_id, progress=0.1)

    try:
        features = extract_features_safe(audio_path)
    except FeatureExtractionError as exc:
        logger.error("Feature extraction failed for job %s", job_id)
        update_analysis_job(
            job_id,
            "failed",
            progress=1.0,
            last_error=str(exc),
            error_code="feature_extraction_failed",
        )
        raise

    logger.info(
        "Extraction complete for job %s: learned=%d dims, handcrafted=%d dims, bpm=%.1f",
        job_id,
        len(features["learned"]),
        len(features["handcrafted"]),
        features["bpm"],
    )

    update_analysis_job(job_id, "processing", progress=0.8)

    try:
        result = process_result(features, job_id, audio_path)
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

    update_analysis_job(job_id, "completed", progress=1.0, result=result)
    return result
