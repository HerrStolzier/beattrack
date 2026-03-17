"""SoundCloud metadata via oEmbed (supports shortened URLs)."""

import logging
import re
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# Matches soundcloud.com/artist/track URLs
_SC_URL_RE = re.compile(
    r"https?://(?:www\.)?soundcloud\.com/([\w-]+)/([\w-]+)"
)

# Matches shortened on.soundcloud.com URLs
_SC_SHORT_RE = re.compile(r"https?://on\.soundcloud\.com/\w+")

def parse_soundcloud_url(url: str) -> bool:
    """Check if URL is a valid SoundCloud track URL (including shortened)."""
    stripped = url.strip()
    return bool(_SC_URL_RE.match(stripped) or _SC_SHORT_RE.match(stripped))


def _is_soundcloud_host(url: str) -> bool:
    """Verify that a resolved URL points to soundcloud.com."""
    from urllib.parse import urlparse
    host = urlparse(url).hostname
    return host is not None and (host == "soundcloud.com" or host.endswith(".soundcloud.com"))


async def _resolve_shortened_url(url: str, client: httpx.AsyncClient) -> str | None:
    """Resolve on.soundcloud.com shortened URL to full soundcloud.com URL."""
    try:
        resp = await client.head(url, follow_redirects=True)
        resolved = str(resp.url)
        if _SC_URL_RE.match(resolved) and _is_soundcloud_host(resolved):
            return resolved
        # HEAD might not redirect — try GET
        resp = await client.get(url, follow_redirects=True)
        resolved = str(resp.url)
        if _SC_URL_RE.match(resolved) and _is_soundcloud_host(resolved):
            return resolved
    except Exception as exc:
        logger.debug("SoundCloud URL resolution failed for %s: %s", url, exc)
    return None


async def fetch_oembed(url: str) -> dict | None:
    """Fetch track metadata via SoundCloud oEmbed API."""
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        # Resolve shortened URLs first
        resolved_url = url
        if _SC_SHORT_RE.match(url.strip()):
            resolved = await _resolve_shortened_url(url, client)
            if resolved:
                resolved_url = resolved
            else:
                logger.warning("Could not resolve SoundCloud shortened URL: %s", url)
                return None

        oembed_url = f"https://soundcloud.com/oembed?url={quote(resolved_url, safe='')}&format=json"
        try:
            resp = await client.get(oembed_url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "title": data.get("title", ""),
                "author_name": data.get("author_name", ""),
            }
        except Exception as exc:
            logger.warning("SoundCloud oEmbed failed for %s: %s", resolved_url, exc)
            return None


# Re-export shared parse_title for backwards compatibility with identify.py imports
from app.services import parse_title as parse_title  # noqa: F811
