"""YouTube oEmbed service for URL validation and metadata extraction."""
import re
import logging
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# Matches standard watch, short youtu.be, and Shorts URLs
_VIDEO_ID_RE = re.compile(r'(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})')

# Allowed YouTube hostnames (exact match prevents SSRF via youtube.com.evil.com)
_ALLOWED_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}

# Suffixes to strip from titles (case-insensitive)
_STRIP_SUFFIXES = re.compile(
    r'\s*\((?:'
    r'official\s+(?:video|audio|music\s+video|lyric\s+video)|'
    r'lyrics?|audio|hd|4k|official|visualizer|live|remix|explicit'
    r')\)',
    re.IGNORECASE,
)


def parse_youtube_url(url: str) -> str | None:
    """Validate a YouTube URL and return its video ID, or None if invalid."""
    if not url:
        return None
    match = _VIDEO_ID_RE.search(url)
    if not match:
        return None
    # Validate actual hostname to prevent SSRF
    parsed = urlparse(url.strip())
    if parsed.hostname not in _ALLOWED_HOSTS:
        return None
    return match.group(1)


def fetch_oembed(url: str) -> dict | None:
    """Fetch YouTube oEmbed metadata for the given URL.

    Returns a dict with at least ``title`` and ``author_name`` keys,
    or None if the request fails.
    """
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
    try:
        resp = requests.get(oembed_url, timeout=10)
        if resp.status_code != 200:
            logger.warning("oEmbed returned HTTP %s for %s", resp.status_code, url)
            return None
        return resp.json()
    except Exception as exc:
        logger.warning("oEmbed fetch error for %s: %s", url, exc)
        return None


def _strip_noise(title: str) -> str:
    """Remove common marketing suffixes from a song title."""
    title = _STRIP_SUFFIXES.sub("", title)
    return title.strip()


def parse_title(title: str, author: str) -> tuple[str, str]:
    """Heuristically split a YouTube title into (artist, song_title).

    Handles the patterns:
      - "Artist - Song Title"
      - "Song Title by Artist"
      - "Artist | Song Title"

    Falls back to (author, title) when no pattern matches.
    """
    title = _strip_noise(title)

    # "Artist - Song Title"
    if " - " in title:
        parts = title.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()

    # "Artist | Song Title"
    if " | " in title:
        parts = title.split(" | ", 1)
        return parts[0].strip(), parts[1].strip()

    # "Song Title by Artist"
    by_match = re.match(r'^(.+?)\s+by\s+(.+)$', title, re.IGNORECASE)
    if by_match:
        return by_match.group(2).strip(), by_match.group(1).strip()

    # Fallback
    return author.strip(), title.strip()
