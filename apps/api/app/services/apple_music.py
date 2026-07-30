"""Apple Music metadata via iTunes Lookup API."""

import logging
import re
from urllib.parse import parse_qs, urlparse

import httpx

logger = logging.getLogger(__name__)

# Obergrenze für zu prüfende URLs. Zweite Verteidigungslinie hinter
# IdentifyRequest.url — die Prüfer sind auch direkt aufrufbar.
MAX_URL_LENGTH = 2048

# Matches music.apple.com track URLs:
# /album/{name}/{albumId}?i={trackId}  OR  /song/{name}/{trackId}
#
# Der Query-Teil steht bewusst NICHT in der Regex: das frühere
# `\?.*?i=(\d+)` war ein fauler Quantor und ließ die Regex bei langen
# Eingaben polynomial backtracken (CodeQL py/polynomial-redos).
# Die Track-ID aus `?i=` wird darum unten separat geparst.
_AM_TRACK_RE = re.compile(
    r"https?://music\.apple\.com/\w+/"
    r"(?:album/[\w-]+/\d+"       # album URL — Track-ID steckt in ?i=
    r"|song/[\w-]+/(\d+))"       # direct song URL
)

# Shortened Apple Music URLs
_AM_SHORT_RE = re.compile(r"https?://(?:music\.lnk\.to|song\.link)/\w+")


def parse_apple_music_url(url: str) -> str | None:
    """Extract track ID from Apple Music URL. Returns track ID or None."""
    stripped = url.strip()
    if len(stripped) > MAX_URL_LENGTH:
        return None

    # match statt search: die URL muss am Anfang stehen, sonst ist sie keine
    # Apple-Music-URL. Deckt sich mit den anderen Plattform-Prüfern.
    m = _AM_TRACK_RE.match(stripped)
    if not m:
        return None

    song_id = m.group(1)
    if song_id:
        return song_id

    # Album-URL: die Track-ID steht im ?i=-Parameter, nicht im Pfad.
    values = parse_qs(urlparse(stripped).query).get("i")
    if values and values[0].isdigit():
        return values[0]
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
