"""SoundCloud metadata via oEmbed (supports shortened URLs)."""

import logging
import re
from urllib.parse import quote

import httpx

from app.services.http_safe import follow_redirects_within

logger = logging.getLogger(__name__)

# Hosts the shortlink resolution may touch. The suffix match in
# host_is_allowed also covers on.soundcloud.com and www.soundcloud.com.
_SC_ALLOWED_HOSTS = frozenset({"soundcloud.com"})

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


async def _resolve_shortened_url(url: str, client: httpx.AsyncClient) -> str | None:
    """Resolve on.soundcloud.com shortened URL to full soundcloud.com URL.

    Redirects are followed hop by hop with the host checked before each
    request, so a shortlink pointing off SoundCloud is refused instead of
    fetched (CodeQL py/full-ssrf).
    """
    # Some endpoints answer HEAD without the redirect, hence the GET retry.
    for method in ("HEAD", "GET"):
        resolved = await follow_redirects_within(
            client, url, _SC_ALLOWED_HOSTS, method=method
        )
        if resolved and _SC_URL_RE.match(resolved):
            return resolved
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
