from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase
from app.limiter import limiter
from app.services.youtube import parse_youtube_url, fetch_oembed, parse_title
from app.services.soundcloud import (
    parse_soundcloud_url,
    fetch_oembed as sc_fetch_oembed,
    parse_title as sc_parse_title,
)
from app.services.spotify import (
    parse_spotify_url,
    fetch_oembed as sp_fetch_oembed,
    parse_title as sp_parse_title,
)
from app.services.apple_music import (
    parse_apple_music_url,
    fetch_metadata as am_fetch_metadata,
    parse_title as am_parse_title,
)

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


@router.post("/youtube", response_model=IdentifyResponse)
@limiter.limit("20/minute")
async def identify_youtube(request: Request, body: IdentifyRequest, sb: Client = Depends(get_supabase)):
    video_id = parse_youtube_url(body.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    oembed = fetch_oembed(body.url)
    if not oembed:
        raise HTTPException(status_code=502, detail="Could not fetch YouTube metadata")

    artist, title = parse_title(oembed.get("title", ""), oembed.get("author_name", ""))
    match = _match_in_db(artist, title, sb)

    return IdentifyResponse(
        matched=match is not None,
        song=match,
        parsed_artist=artist,
        parsed_title=title,
        message=f"Match: {match['artist']} — {match['title']}" if match else "Kein Match im Katalog gefunden.",
    )


@router.post("/soundcloud", response_model=IdentifyResponse)
@limiter.limit("20/minute")
async def identify_soundcloud(request: Request, body: IdentifyRequest, sb: Client = Depends(get_supabase)):
    if not parse_soundcloud_url(body.url):
        raise HTTPException(status_code=400, detail="Invalid SoundCloud URL")

    meta = await sc_fetch_oembed(body.url)
    if not meta:
        raise HTTPException(status_code=502, detail="Could not fetch SoundCloud metadata")

    artist, title = sc_parse_title(meta["title"], meta["author_name"])
    match = _match_in_db(artist, title, sb)

    return IdentifyResponse(
        matched=match is not None,
        song=match,
        parsed_artist=artist,
        parsed_title=title,
        message=f"Match: {match['artist']} — {match['title']}" if match else "Kein Match im Katalog gefunden.",
    )


@router.post("/spotify", response_model=IdentifyResponse)
@limiter.limit("20/minute")
async def identify_spotify(request: Request, body: IdentifyRequest, sb: Client = Depends(get_supabase)):
    if not parse_spotify_url(body.url):
        raise HTTPException(status_code=400, detail="Invalid Spotify URL")

    meta = await sp_fetch_oembed(body.url)
    if not meta:
        raise HTTPException(status_code=502, detail="Could not fetch Spotify metadata")

    artist, title = sp_parse_title(meta["title"], meta["author_name"])
    match = _match_in_db(artist, title, sb)

    return IdentifyResponse(
        matched=match is not None,
        song=match,
        parsed_artist=artist,
        parsed_title=title,
        message=f"Match: {match['artist']} — {match['title']}" if match else "Kein Match im Katalog gefunden.",
    )


@router.post("/apple_music", response_model=IdentifyResponse)
@limiter.limit("20/minute")
async def identify_apple_music(request: Request, body: IdentifyRequest, sb: Client = Depends(get_supabase)):
    if not parse_apple_music_url(body.url):
        raise HTTPException(status_code=400, detail="Invalid Apple Music URL")

    meta = await am_fetch_metadata(body.url)
    if not meta:
        raise HTTPException(status_code=502, detail="Could not fetch Apple Music metadata")

    artist, title = am_parse_title(meta["title"], meta["author_name"])
    match = _match_in_db(artist, title, sb)

    return IdentifyResponse(
        matched=match is not None,
        song=match,
        parsed_artist=artist,
        parsed_title=title,
        message=f"Match: {match['artist']} — {match['title']}" if match else "Kein Match im Katalog gefunden.",
    )
