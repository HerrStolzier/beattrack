"""On-demand song ingestion via Deezer — search, download preview, extract features, store."""

import json
import logging
import os
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import quote

logger = logging.getLogger(__name__)

DEEZER_API = "https://api.deezer.com"
API_DELAY = 0.4


# ---------------------------------------------------------------------------
# Deezer API helpers (extracted from seed_deezer.py for reuse)
# ---------------------------------------------------------------------------


def _deezer_get(endpoint: str, retries: int = 3) -> dict | None:
    """GET a Deezer API endpoint with retry logic."""
    url = f"{DEEZER_API}{endpoint}" if not endpoint.startswith("http") else endpoint
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            resp = urllib.request.urlopen(req, timeout=15)  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                logger.warning("Deezer API error on %s: %s", endpoint, data["error"])
                return None
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                logger.error("Deezer API failed after %d retries: %s — %s", retries, endpoint, exc)
                return None
    return None


def search_deezer_track(artist: str, title: str) -> dict | None:
    """Search Deezer for a track matching artist + title.

    Returns Deezer track dict with id, title, artist.name, preview, album, duration.
    """
    query = f'artist:"{artist}" track:"{title}"'
    data = _deezer_get(f"/search/track?q={quote(query)}&limit=5")
    if not data or not isinstance(data, dict):
        return None

    tracks = data.get("data", [])
    if not tracks:
        # Fallback: less strict search without field qualifiers
        data = _deezer_get(f"/search/track?q={quote(f'{artist} {title}')}&limit=5")
        if not data or not isinstance(data, dict):
            return None
        tracks = data.get("data", [])

    if not tracks:
        return None

    # Prefer exact title match
    title_lower = title.lower()
    artist_lower = artist.lower()
    for t in tracks:
        t_title = t.get("title", "").lower()
        t_artist = t.get("artist", {}).get("name", "").lower()
        if title_lower in t_title and (artist_lower in t_artist or t_artist in artist_lower):
            return t

    # Fallback: first result with a preview URL
    for t in tracks:
        if t.get("preview"):
            return t

    return None


def fetch_fresh_preview_url(deezer_id: int) -> str | None:
    """Fetch a fresh (non-expired) preview URL from Deezer track endpoint."""
    data = _deezer_get(f"/track/{deezer_id}")
    if data and isinstance(data, dict):
        return data.get("preview") or None
    return None


def download_preview(url: str, dest: str) -> bool:
    """Download a 30s preview MP3 from Deezer CDN."""
    try:
        urllib.request.urlretrieve(url, dest)  # noqa: S310
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to download preview: %s — %s", url, exc)
        return False


def extract_and_store(
    deezer_track: dict,
    *,
    expand_neighbors: bool = True,
    max_neighbors: int = 10,
) -> dict | None:
    """Download preview, extract features, insert into DB. Returns song dict or None.

    This is a synchronous, blocking function — call from a worker process.
    """
    import sys
    from pathlib import Path

    deezer_id = deezer_track["id"]
    title = deezer_track.get("title", "Unknown")
    artist = deezer_track.get("artist", {}).get("name", "Unknown")
    album = deezer_track.get("album", {}).get("title")
    duration = deezer_track.get("duration", 0)

    logger.info("Auto-ingest: %s — %s (deezer_id=%d)", artist, title, deezer_id)

    # 1. Get fresh preview URL (HMAC-signed URLs expire quickly)
    preview_url = fetch_fresh_preview_url(deezer_id)
    if not preview_url:
        preview_url = deezer_track.get("preview")
    if not preview_url:
        logger.warning("No preview URL for deezer_id=%d", deezer_id)
        return None

    # 2. Download preview to temp file
    temp_dir = tempfile.mkdtemp(prefix="beattrack_ingest_")
    preview_path = os.path.join(temp_dir, f"{deezer_id}.mp3")

    try:
        if not download_preview(preview_url, preview_path):
            return None

        # 3. Extract features via subprocess (same as seed_deezer.py)
        import subprocess

        extract_script = str(Path(__file__).parent.parent / "workers" / "extract.py")
        model_path = str(Path(__file__).parent.parent.parent / "models" / "msd-musicnn-1.pb")
        env = {**os.environ, "MUSICNN_MODEL_PATH": model_path}
        result = subprocess.run(
            [sys.executable, extract_script, preview_path],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if result.returncode != 0:
            # Filter out CUDA warnings from stderr to find real error
            stderr_lines = [
                line for line in result.stderr.splitlines()
                if "libcuda" not in line and "tensorflow" not in line.lower()
            ]
            real_stderr = "\n".join(stderr_lines[-5:]) if stderr_lines else result.stderr[:500]
            logger.error(
                "Feature extraction failed for deezer_id=%d (exit=%d): %s",
                deezer_id, result.returncode, real_stderr,
            )
            return None

        if not result.stdout.strip():
            logger.error("Feature extraction returned empty output for deezer_id=%d", deezer_id)
            return None

        features = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        logger.error("Feature extraction timed out for deezer_id=%d", deezer_id)
        return None
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("Extraction error for deezer_id=%d: %s", deezer_id, exc)
        return None
    finally:
        # Clean up temp files
        try:
            os.unlink(preview_path)
            os.rmdir(temp_dir)
        except OSError:
            pass

    # 4. Normalize handcrafted features
    from app.db import get_supabase
    from app.services.features import normalize_handcrafted

    sb = get_supabase()
    handcrafted_norm = features["handcrafted"]
    try:
        config_result = sb.table("config").select("value").eq("key", "normalization_stats").single().execute()
        if config_result.data:
            raw_value = config_result.data["value"]
            stats = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
            handcrafted_norm = normalize_handcrafted(features["handcrafted"], stats)
    except Exception as exc:
        logger.warning("Could not normalize handcrafted features: %s", exc)

    # 5. Resolve genre from Deezer album
    from app.services.genre import resolve_genre_from_album

    album_id = deezer_track.get("album", {}).get("id")
    genre = resolve_genre_from_album(album_id, deezer_get=_deezer_get)

    # 6. Insert into DB
    song_data = {
        "title": title,
        "artist": artist,
        "album": album,
        "duration_sec": features.get("duration") or duration,
        "bpm": features.get("bpm"),
        "musical_key": features.get("key", "Unknown"),
        "learned_embedding": features["learned"],
        "handcrafted_raw": features["handcrafted"],
        "handcrafted_norm": handcrafted_norm,
        "source": "deezer",
        "embedding_type": "real",
        "metadata_status": "complete",
        "genre": genre,
        "deezer_id": deezer_id,
    }

    try:
        # Use bulk_import_songs RPC (SECURITY DEFINER) to bypass RLS
        rpc_result = sb.rpc("bulk_import_songs", {"rows": [song_data]}).execute()
        logger.info("Auto-ingest complete: %s — %s (deezer_id=%d)", artist, title, deezer_id)

        # Fetch the inserted song to return it
        fetch_result = (
            sb.table("songs")
            .select("id, title, artist, album, bpm, musical_key, duration_sec, deezer_id")
            .eq("deezer_id", deezer_id)
            .single()
            .execute()
        )
        song = fetch_result.data
        if song:
            # 6. Queue neighbor expansion (async)
            if expand_neighbors:
                _queue_neighbor_expansion(deezer_track, max_neighbors)
            return song
    except Exception as exc:
        # Might be a duplicate (deezer_id unique constraint)
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            logger.info("Song already exists: deezer_id=%d", deezer_id)
            try:
                existing = (
                    sb.table("songs")
                    .select("id, title, artist, album, bpm, musical_key, duration_sec, deezer_id")
                    .eq("deezer_id", deezer_id)
                    .single()
                    .execute()
                )
                return existing.data
            except Exception:
                pass
        else:
            logger.error("Failed to insert song deezer_id=%d: %s", deezer_id, exc)

    return None


def _queue_neighbor_expansion(deezer_track: dict, max_neighbors: int = 10) -> None:
    """Queue background ingestion of related tracks from the same artist."""
    try:
        from app.workers import ingest_neighbors

        artist_id = deezer_track.get("artist", {}).get("id")
        if artist_id:
            ingest_neighbors.defer(artist_id=artist_id, max_tracks=max_neighbors)
            logger.info("Queued neighbor expansion for artist_id=%d", artist_id)
    except Exception as exc:
        # Non-critical — don't fail the main ingest
        logger.warning("Failed to queue neighbor expansion: %s", exc)


def ingest_artist_top_tracks(artist_id: int, max_tracks: int = 10) -> int:
    """Ingest top tracks from a Deezer artist that aren't already in the DB.

    Returns number of newly ingested tracks.
    """
    from app.db import get_supabase

    time.sleep(API_DELAY)
    data = _deezer_get(f"/artist/{artist_id}/top?limit={max_tracks}")
    if not data or not isinstance(data, dict):
        return 0

    tracks = data.get("data", [])
    if not tracks:
        return 0

    # Check which deezer_ids are already in DB
    sb = get_supabase()
    deezer_ids = [t["id"] for t in tracks if t.get("id")]
    try:
        existing = (
            sb.table("songs")
            .select("deezer_id")
            .in_("deezer_id", deezer_ids)
            .execute()
        )
        existing_ids = {r["deezer_id"] for r in (existing.data or [])}
    except Exception:
        existing_ids = set()

    ingested = 0
    for track in tracks:
        if track.get("id") in existing_ids:
            continue
        if not track.get("preview"):
            continue

        time.sleep(API_DELAY)  # Rate limit between ingests
        result = extract_and_store(track, expand_neighbors=False)
        if result:
            ingested += 1

    logger.info("Neighbor expansion: ingested %d/%d tracks for artist_id=%d", ingested, len(tracks), artist_id)
    return ingested
