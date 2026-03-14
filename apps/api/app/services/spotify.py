"""Spotify metadata via oEmbed."""

import logging
import re
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# Matches open.spotify.com/track/ID URLs (with optional intl prefix and query params)
_SPOTIFY_URL_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-\w+/)?track/([a-zA-Z0-9]+)"
)

# Suffixes to strip from titles (case-insensitive)
_NOISE_RE = re.compile(
    r"\s*[\(\[](Official|Audio|Lyric|Music|HD|4K|Visualizer|Live|Remix|Explicit|Remaster)"
    r"[^\)\]]*[\)\]]",
    re.IGNORECASE,
)


def parse_spotify_url(url: str) -> bool:
    """Check if URL is a valid Spotify track URL."""
    return bool(_SPOTIFY_URL_RE.match(url.strip()))


async def fetch_oembed(url: str) -> dict | None:
    """Fetch track metadata via Spotify oEmbed API."""
    oembed_url = f"https://open.spotify.com/oembed?url={quote(url, safe='')}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(oembed_url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "title": data.get("title", ""),
                "author_name": "",  # Spotify oEmbed doesn't have separate author
            }
    except Exception as exc:
        logger.warning("Spotify oEmbed failed for %s: %s", url, exc)
        return None


def parse_title(title: str, author_name: str = "") -> tuple[str, str]:
    """Extract (artist, track_title) from Spotify oEmbed data.

    Spotify oEmbed title is usually "Track Name" and the HTML contains artist info.
    The title field alone might be "Song - Artist" or just "Song".
    """
    cleaned = _NOISE_RE.sub("", title).strip()

    # Try "Artist - Title" format
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()

    artist = author_name.strip() if author_name else "Unknown"
    return artist, cleaned if cleaned else title
