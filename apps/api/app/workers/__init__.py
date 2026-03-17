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


def process_analysis_result(features: dict, job_id: str, audio_path: str = "") -> dict:
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

    # 2. AcoustID fingerprinting + MusicBrainz metadata enrichment
    song_title = f"Upload {job_id[:8]}"
    song_artist = "Unknown"
    song_album = None
    musicbrainz_id = None

    if audio_path:
        try:
            from app.services.acoustid import fingerprint_file, lookup as acoustid_lookup
            from app.services.musicbrainz import lookup_recording
            import os as _os

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
                            "AcoustID resolved job %s → MBID %s (%s – %s)",
                            job_id, mbid, song_artist, song_title,
                        )
        except Exception as exc:
            logger.warning("AcoustID/MusicBrainz enrichment failed for job %s: %s", job_id, exc)

    # 3. Insert song into songs table
    song_id = job_id  # Use job_id as song_id for simplicity
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
        # Don't fail the whole job — still return features

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

    # 2. Insert into DB + find similar songs (pass audio_path for AcoustID enrichment)
    try:
        result = process_analysis_result(features, job_id, audio_path=audio_path)
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


@app.task(name="ingest_from_deezer", retry=1, pass_context=True)
def ingest_from_deezer(context, *, deezer_track_json: str):
    """Auto-ingest a single song from Deezer: download preview → extract → store.

    Triggered when identify can't find a song in the DB but finds it on Deezer.
    """
    import json as _json

    deezer_track = _json.loads(deezer_track_json)
    logger.info(
        "Ingest task: %s — %s (deezer_id=%d)",
        deezer_track.get("artist", {}).get("name", "?"),
        deezer_track.get("title", "?"),
        deezer_track.get("id", 0),
    )

    from app.services.ingest import extract_and_store

    result = extract_and_store(deezer_track, expand_neighbors=True)
    if result:
        logger.info("Ingest complete: %s (id=%s)", result.get("title"), result.get("id"))
    else:
        logger.warning("Ingest failed for deezer_id=%d", deezer_track.get("id", 0))
    return result


@app.task(name="ingest_neighbors", retry=0, pass_context=True)
def ingest_neighbors(context, *, artist_id: int, max_tracks: int = 10):
    """Background task: ingest top tracks from an artist to expand the neighborhood.

    Low priority — runs after the main ingest completes.
    """
    logger.info("Neighbor expansion: artist_id=%d, max_tracks=%d", artist_id, max_tracks)
    from app.services.ingest import ingest_artist_top_tracks

    count = ingest_artist_top_tracks(artist_id, max_tracks)
    logger.info("Neighbor expansion complete: %d new tracks for artist_id=%d", count, artist_id)
    return {"artist_id": artist_id, "ingested": count}
