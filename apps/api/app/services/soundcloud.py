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

# Suffixes to strip from titles (case-insensitive)
_NOISE_RE = re.compile(
    r"\s*[\(\[](Official|Audio|Lyric|Music|HD|4K|Visualizer|Live|Remix|Explicit)"
    r"[^\)\]]*[\)\]]",
    re.IGNORECASE,
)


def parse_soundcloud_url(url: str) -> bool:
    """Check if URL is a valid SoundCloud track URL (including shortened)."""
    stripped = url.strip()
    return bool(_SC_URL_RE.match(stripped) or _SC_SHORT_RE.match(stripped))


async def _resolve_shortened_url(url: str, client: httpx.AsyncClient) -> str | None:
    """Resolve on.soundcloud.com shortened URL to full soundcloud.com URL."""
    try:
        resp = await client.head(url, follow_redirects=True)
        resolved = str(resp.url)
        if _SC_URL_RE.match(resolved):
            return resolved
        # HEAD might not redirect — try GET
        resp = await client.get(url, follow_redirects=True)
        resolved = str(resp.url)
        if _SC_URL_RE.match(resolved):
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


def parse_title(title: str, author_name: str = "") -> tuple[str, str]:
    """Extract (artist, track_title) from SoundCloud oEmbed data.

    SoundCloud title is usually just the track name.
    author_name is the uploader/artist.
    """
    cleaned = _NOISE_RE.sub("", title).strip()

    # SoundCloud titles sometimes use "Artist - Title" format
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()

    # Default: author_name is artist, title is track
    artist = author_name.strip() if author_name else "Unknown"
    return artist, cleaned if cleaned else title
