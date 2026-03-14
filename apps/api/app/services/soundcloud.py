"""SoundCloud metadata via oEmbed."""

import logging
import re
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# Matches soundcloud.com/artist/track URLs
_SC_URL_RE = re.compile(
    r"https?://(?:www\.)?soundcloud\.com/([\w-]+)/([\w-]+)"
)

# Suffixes to strip from titles (case-insensitive)
_NOISE_RE = re.compile(
    r"\s*[\(\[](Official|Audio|Lyric|Music|HD|4K|Visualizer|Live|Remix|Explicit)"
    r"[^\)\]]*[\)\]]",
    re.IGNORECASE,
)


def parse_soundcloud_url(url: str) -> bool:
    """Check if URL is a valid SoundCloud track URL."""
    return bool(_SC_URL_RE.match(url.strip()))


async def fetch_oembed(url: str) -> dict | None:
    """Fetch track metadata via SoundCloud oEmbed API."""
    oembed_url = f"https://soundcloud.com/oembed?url={quote(url, safe='')}&format=json"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(oembed_url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "title": data.get("title", ""),
                "author_name": data.get("author_name", ""),
            }
    except Exception as exc:
        logger.warning("SoundCloud oEmbed failed for %s: %s", url, exc)
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
