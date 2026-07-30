"""Deezer metadata via public API."""

import logging
import re

import httpx

from app.services.http_safe import follow_redirects_within

logger = logging.getLogger(__name__)

# Hosts the share-link resolution may touch. The suffix match in
# host_is_allowed also covers www.deezer.com and link.deezer.com.
_DEEZER_ALLOWED_HOSTS = frozenset({"deezer.com", "deezer.page.link"})

# Matches deezer.com/track/ID or deezer.com/xx/track/ID
_DEEZER_TRACK_RE = re.compile(
    r"https?://(?:www\.)?deezer\.com/(?:\w{2}/)?track/(\d+)"
)

# Matches link.deezer.com share links (short URLs)
_DEEZER_SHARE_RE = re.compile(
    r"https?://(?:link\.)?deezer\.(?:com|page\.link)/\S+"
)


def parse_deezer_url(url: str) -> str | None:
    """Validate a Deezer URL and return the track ID, or None if invalid.

    Supports:
    - https://www.deezer.com/track/12345
    - https://www.deezer.com/de/track/12345
    - https://link.deezer.com/s/... (share links — resolved via redirect)
    """
    m = _DEEZER_TRACK_RE.match(url.strip())
    if m:
        return m.group(1)
    # Share links need to be resolved first
    if _DEEZER_SHARE_RE.match(url.strip()):
        return "share"  # Sentinel — fetch_metadata will resolve it
    return None


async def fetch_metadata(url: str) -> dict | None:
    """Fetch track metadata from Deezer API.

    For share links, follows redirects to get the track ID first.
    Returns dict with 'title' and 'author_name' keys (matching the
    interface used by other platform services).
    """
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        track_id = None

        # Direct track URL
        m = _DEEZER_TRACK_RE.match(url.strip())
        if m:
            track_id = m.group(1)
        else:
            # Share link — resolve it, but only within Deezer hosts.
            # The caller is supposed to have run parse_deezer_url first;
            # re-checking here keeps the function safe on its own.
            stripped = url.strip()
            if not _DEEZER_SHARE_RE.match(stripped):
                logger.warning("Not a Deezer URL, refusing to fetch: %s", url)
                return None

            resolved = await follow_redirects_within(client, stripped, _DEEZER_ALLOWED_HOSTS)
            if not resolved:
                logger.warning("Failed to resolve Deezer share link: %s", url)
                return None

            m = _DEEZER_TRACK_RE.match(resolved)
            if not m:
                logger.warning("Deezer share link did not resolve to track: %s → %s", url, resolved)
                return None
            track_id = m.group(1)

        # Fetch track info from Deezer API
        try:
            resp = await client.get(f"https://api.deezer.com/track/{track_id}")
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                logger.warning("Deezer API error for track %s: %s", track_id, data["error"])
                return None

            return {
                "title": data.get("title", ""),
                "author_name": data.get("artist", {}).get("name", ""),
            }
        except Exception as exc:
            logger.warning("Deezer API request failed for track %s: %s", track_id, exc)
            return None
