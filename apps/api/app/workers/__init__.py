"""Procrastinate job queue registration for async background work."""

import logging
import os

import procrastinate

from app.workers.analysis import process_analysis_result, run_analysis_task
from app.workers.ingest_tasks import run_ingest_from_deezer, run_ingest_neighbors

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get Postgres connection URL for Procrastinate.

    Uses Supavisor transaction mode (port 6543) for connection pooling.
    Falls back to DATABASE_URL if SUPABASE_DB_URL not set.
    """
    url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL", "")
    if not url:
        logger.warning(
            "No database URL configured (SUPABASE_DB_URL or DATABASE_URL). "
            "Procrastinate job queue will not function."
        )
    return url


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
    """Main analysis task registered with Procrastinate."""
    return run_analysis_task(
        audio_path=audio_path,
        job_id=job_id,
        process_result=process_analysis_result,
    )


@app.task(name="ingest_from_deezer", retry=1, pass_context=True)
def ingest_from_deezer(context, *, deezer_track_json: str):
    """Auto-ingest a single song from Deezer."""
    return run_ingest_from_deezer(deezer_track_json=deezer_track_json)


@app.task(name="ingest_neighbors", retry=0, pass_context=True)
def ingest_neighbors(context, *, artist_id: int, max_tracks: int = 10):
    """Background task: ingest top tracks from an artist."""
    return run_ingest_neighbors(artist_id=artist_id, max_tracks=max_tracks)
