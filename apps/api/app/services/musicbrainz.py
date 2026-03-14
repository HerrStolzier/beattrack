"""MusicBrainz metadata lookup service."""
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_MB_API_BASE = "https://musicbrainz.org/ws/2"
_USER_AGENT = "beattrack/0.1.0 (https://beattrack.vercel.app)"
_MIN_INTERVAL = 1.0  # max 1 request per second
_last_call: float = 0.0


def lookup_recording(mbid: str) -> Optional[dict]:
    """Fetch recording metadata from MusicBrainz by MBID.

    Rate-limited to max 1 request per second as required by MusicBrainz policy.
    Returns dict with keys: title, artist, album — or None on error / not found.
    """
    global _last_call

    # Rate limiting
    elapsed = time.monotonic() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call = time.monotonic()

    url = f"{_MB_API_BASE}/recording/{mbid}"
    params = {"inc": "artists+releases", "fmt": "json"}
    headers = {"User-Agent": _USER_AGENT}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 404:
            logger.info("MusicBrainz recording not found: %s", mbid)
            return None
        response.raise_for_status()
        data = response.json()

        title = data.get("title", "")

        artist = ""
        artist_credits = data.get("artist-credit", [])
        if artist_credits:
            parts = []
            for credit in artist_credits:
                if isinstance(credit, dict):
                    artist_obj = credit.get("artist", {})
                    name = artist_obj.get("name", "")
                    join = credit.get("joinphrase", "")
                    if name:
                        parts.append(name + join)
            artist = "".join(parts).strip()

        album = ""
        releases = data.get("releases", [])
        if releases:
            album = releases[0].get("title", "")

        return {"title": title, "artist": artist, "album": album}

    except requests.HTTPError as exc:
        logger.warning("MusicBrainz HTTP error for %s: %s", mbid, exc)
        return None
    except Exception as exc:
        logger.warning("MusicBrainz lookup failed for %s: %s", mbid, exc)
        return None
