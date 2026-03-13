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


@app.task(name="analyze_audio", retry=1, pass_context=True)
def analyze_audio(context, *, audio_path: str, job_id: str):
    """Main analysis task: extract features → normalize → insert into DB → find similar songs.

    This runs in the Procrastinate worker process, NOT in the FastAPI event loop.
    """
    from app.services.features import extract_features_safe, normalize_handcrafted, FeatureExtractionError

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

    # 2. Normalize handcrafted features (Z-score)
    # Note: normalization stats loaded from config table at runtime
    # For now, store raw — normalization applied when stats are available

    result = {
        "learned": features["learned"],
        "handcrafted": features["handcrafted"],
        "bpm": features["bpm"],
        "key": features["key"],
        "duration": features.get("duration", 0),
    }

    update_job_status(job_id, "completed", progress=1.0, result=result)
    return result
