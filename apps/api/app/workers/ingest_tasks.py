"""Import-safe ingest worker logic."""

import json
import logging

logger = logging.getLogger(__name__)


def run_ingest_from_deezer(*, deezer_track_json: str):
    """Auto-ingest a single song from Deezer."""
    deezer_track = json.loads(deezer_track_json)
    logger.info(
        "Ingest task: %s - %s (deezer_id=%d)",
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


def run_ingest_neighbors(*, artist_id: int, max_tracks: int = 10):
    """Ingest top tracks from an artist to expand the neighborhood."""
    logger.info("Neighbor expansion: artist_id=%d, max_tracks=%d", artist_id, max_tracks)
    from app.services.ingest import ingest_artist_top_tracks

    count = ingest_artist_top_tracks(artist_id, max_tracks)
    logger.info("Neighbor expansion complete: %d new tracks for artist_id=%d", count, artist_id)
    return {"artist_id": artist_id, "ingested": count}
