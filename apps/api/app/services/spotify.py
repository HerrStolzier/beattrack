"""Spotify metadata via oEmbed + Open Graph scraping."""

import logging
import re
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# Matches open.spotify.com/track/ID URLs (with optional intl prefix and query params)
_SPOTIFY_URL_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-\w+/)?track/([a-zA-Z0-9]+)"
)

# OG description pattern: "Artist · Album · Song · Year"
_OG_DESC_RE = re.compile(r'property="og:description"\s+content="([^"]+)"')


def parse_spotify_url(url: str) -> str | None:
    """Validate a Spotify track URL and return the track ID, or None if invalid."""
    m = _SPOTIFY_URL_RE.match(url.strip())
    return m.group(1) if m else None


async def fetch_oembed(url: str) -> dict | None:
    """Fetch track metadata via Spotify oEmbed + OG meta tags for artist."""
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        # 1) oEmbed for track title
        oembed_url = f"https://open.spotify.com/oembed?url={quote(url, safe='')}"
        try:
            resp = await client.get(oembed_url)
            resp.raise_for_status()
            data = resp.json()
            title = data.get("title", "")
        except Exception as exc:
            logger.warning("Spotify oEmbed failed for %s: %s", url, exc)
            return None

        # 2) Scrape track page for og:description → artist name
        #    Reconstruct URL from validated track ID to prevent SSRF via redirects
        track_id = parse_spotify_url(url)
        safe_url = f"https://open.spotify.com/track/{track_id}" if track_id else url
        author_name = ""
        try:
            page = await client.get(
                safe_url, headers={"User-Agent": "Mozilla/5.0 (compatible; Beattrack/1.0)"}
            )
            if page.status_code == 200:
                match = _OG_DESC_RE.search(page.text)
                if match:
                    # Pattern: "Artist · Album · Song · Year"
                    parts = match.group(1).split(" · ")
                    if parts:
                        author_name = parts[0].strip()
        except Exception as exc:
            logger.debug("Spotify OG scrape failed for %s: %s", url, exc)

        return {"title": title, "author_name": author_name}


# Re-export shared parse_title for backwards compatibility with identify.py imports
from app.services import parse_title as parse_title  # noqa: F811
