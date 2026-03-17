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
    """Try to find a song in DB by title, then by artist. Returns song dict or None."""
    if title:
        result = (
            sb.table("songs")
            .select("id, title, artist, album, bpm, musical_key, duration_sec")
            .ilike("title", f"%{_escape_like(title)}%")
            .limit(5)
            .execute()
        )
        if result.data:
            return result.data[0]

    if artist:
        result = (
            sb.table("songs")
            .select("id, title, artist, album, bpm, musical_key, duration_sec")
            .ilike("artist", f"%{_escape_like(artist)}%")
            .limit(5)
            .execute()
        )
        if result.data:
            return result.data[0]

    return None


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
