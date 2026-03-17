"""Apple Music metadata via iTunes Lookup API."""

import logging
import re

import httpx

logger = logging.getLogger(__name__)

# Matches music.apple.com track URLs:
# /album/{name}/{albumId}?i={trackId}  OR  /song/{name}/{trackId}
_AM_TRACK_RE = re.compile(
    r"https?://music\.apple\.com/\w+/"
    r"(?:album/[\w-]+/\d+\?.*?i=(\d+)"  # album URL with ?i=trackId
    r"|song/[\w-]+/(\d+))"               # direct song URL
)

# Shortened Apple Music URLs
_AM_SHORT_RE = re.compile(r"https?://(?:music\.lnk\.to|song\.link)/\w+")


def parse_apple_music_url(url: str) -> str | None:
    """Extract track ID from Apple Music URL. Returns track ID or None."""
    m = _AM_TRACK_RE.search(url.strip())
    if m:
        return m.group(1) or m.group(2)
    return None


async def fetch_metadata(url: str) -> dict | None:
    """Fetch track metadata via iTunes Lookup API."""
    track_id = parse_apple_music_url(url)
    if not track_id:
        return None

    lookup_url = f"https://itunes.apple.com/lookup?id={track_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(lookup_url)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                logger.warning("iTunes lookup returned no results for ID %s", track_id)
                return None

            track = results[0]
            return {
                "title": track.get("trackName", ""),
                "author_name": track.get("artistName", ""),
            }
    except Exception as exc:
        logger.warning("iTunes lookup failed for %s: %s", track_id, exc)
        return None


# Re-export shared parse_title for backwards compatibility with identify.py imports
from app.services import parse_title as parse_title  # noqa: F811
