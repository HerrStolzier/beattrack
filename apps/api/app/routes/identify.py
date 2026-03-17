import re
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase
from app.limiter import limiter
from app.services import parse_title
from app.services.apple_music import parse_apple_music_url, fetch_metadata as am_fetch_metadata
from app.services.soundcloud import parse_soundcloud_url, fetch_oembed as sc_fetch_oembed
from app.services.spotify import parse_spotify_url, fetch_oembed as sp_fetch_oembed
from app.services.youtube import fetch_oembed as yt_fetch_oembed, parse_title as yt_parse_title, parse_youtube_url

router = APIRouter(prefix="/identify", tags=["identify"])


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards in user input."""
    return value.replace("%", r"\%").replace("_", r"\_")


def _match_in_db(artist: str, title: str, sb: Client) -> dict | None:
    """Find a song in DB using trigram similarity on artist + title.

    Strategy:
    1. Combined artist+title search ranked by similarity (best match).
    2. Falls back to title-only if no combined match.
    Requires pg_trgm extension (already enabled via GIN indexes).
    """
    select_cols = "id, title, artist, album, bpm, musical_key, duration_sec, deezer_id"

    # Strategy 1: Combined artist + title (most precise)
    if artist and title:
        result = (
            sb.table("songs")
            .select(select_cols)
            .ilike("artist", f"%{_escape_like(artist)}%")
            .ilike("title", f"%{_escape_like(title)}%")
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]

    # Strategy 2: Title-only, but validate artist similarity before accepting
    if title:
        result = (
            sb.table("songs")
            .select(select_cols)
            .ilike("title", f"%{_escape_like(title)}%")
            .limit(10)
            .execute()
        )
        if result.data:
            if artist:
                # Only accept if at least one result has a similar artist
                artist_clean = _clean_artist(artist)
                for song in result.data:
                    if _artists_match(artist_clean, _clean_artist(song["artist"])):
                        return song
                # No artist match — don't return a wrong song
                return None
            return result.data[0]

    # Strategy 3: Artist-only (last resort, only if title is empty)
    if artist and not title:
        result = (
            sb.table("songs")
            .select(select_cols)
            .ilike("artist", f"%{_escape_like(artist)}%")
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]

    return None


def _clean_artist(name: str) -> str:
    """Normalize artist name for comparison. Strips ' - Topic' suffix from YouTube Music."""
    name = re.sub(r'\s*-\s*Topic$', '', name, flags=re.IGNORECASE)
    return name.strip().lower()


def _artists_match(a: str, b: str) -> bool:
    """Check if two artist names plausibly refer to the same artist."""
    if not a or not b:
        return False
    if a == b:
        return True
    # Substring match (handles "Prok & Fitch" vs "Prok")
    if a in b or b in a:
        return True
    # Check if any word (3+ chars) from one appears in the other
    words_a = {w for w in a.split() if len(w) >= 3}
    words_b = {w for w in b.split() if len(w) >= 3}
    return bool(words_a & words_b)


class IdentifyRequest(BaseModel):
    url: str


class IdentifyResponse(BaseModel):
    matched: bool
    song: dict | None = None
    parsed_artist: str | None = None
    parsed_title: str | None = None
    message: str


async def _identify_platform(
    url: str,
    sb: Client,
    *,
    validate_url: Callable[[str], Any],
    fetch_meta: Callable[[str], Coroutine[Any, Any, dict | None]],
    platform_name: str,
    title_parser: Callable[[str, str], tuple[str, str]] = parse_title,
) -> IdentifyResponse:
    """Generic identify handler shared by all platform endpoints."""
    if not validate_url(url):
        raise HTTPException(status_code=400, detail=f"Invalid {platform_name} URL")

    meta = await fetch_meta(url)

    if not meta:
        raise HTTPException(status_code=502, detail=f"Could not fetch {platform_name} metadata")

    artist, title = title_parser(meta.get("title", ""), meta.get("author_name", ""))
    match = _match_in_db(artist, title, sb)

    return IdentifyResponse(
        matched=match is not None,
        song=match,
        parsed_artist=artist,
        parsed_title=title,
        message=(
            f"Match: {match['artist']} — {match['title']}"
            if match
            else "Kein Match im Katalog gefunden."
        ),
    )


@router.post("/youtube", response_model=IdentifyResponse)
@limiter.limit("20/minute")
async def identify_youtube(
    request: Request, body: IdentifyRequest, sb: Client = Depends(get_supabase),
):
    return await _identify_platform(
        body.url, sb,
        validate_url=parse_youtube_url,
        fetch_meta=yt_fetch_oembed,
        platform_name="YouTube",
        title_parser=yt_parse_title,
    )


@router.post("/soundcloud", response_model=IdentifyResponse)
@limiter.limit("20/minute")
async def identify_soundcloud(
    request: Request, body: IdentifyRequest, sb: Client = Depends(get_supabase),
):
    return await _identify_platform(
        body.url, sb,
        validate_url=parse_soundcloud_url,
        fetch_meta=sc_fetch_oembed,
        platform_name="SoundCloud",
    )


@router.post("/spotify", response_model=IdentifyResponse)
@limiter.limit("20/minute")
async def identify_spotify(
    request: Request, body: IdentifyRequest, sb: Client = Depends(get_supabase),
):
    return await _identify_platform(
        body.url, sb,
        validate_url=parse_spotify_url,
        fetch_meta=sp_fetch_oembed,
        platform_name="Spotify",
    )


@router.post("/apple_music", response_model=IdentifyResponse)
@limiter.limit("20/minute")
async def identify_apple_music(
    request: Request, body: IdentifyRequest, sb: Client = Depends(get_supabase),
):
    return await _identify_platform(
        body.url, sb,
        validate_url=parse_apple_music_url,
        fetch_meta=am_fetch_metadata,
        platform_name="Apple Music",
    )
