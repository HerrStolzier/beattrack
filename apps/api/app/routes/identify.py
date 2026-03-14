from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client

from app.db import get_supabase
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

router = APIRouter(prefix="/identify", tags=["identify"])


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards in user input."""
    return value.replace("%", r"\%").replace("_", r"\_")


async def _match_in_db(artist: str, title: str, sb: Client) -> dict | None:
    """Try to find a song in DB by title, then by artist. Returns song dict or None."""
    # Phase 1: title match
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

    # Phase 2: artist match
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


class YouTubeRequest(BaseModel):
    url: str


class IdentifyRequest(BaseModel):
    url: str


class IdentifyResponse(BaseModel):
    matched: bool
    song: dict | None = None
    parsed_artist: str | None = None
    parsed_title: str | None = None
    message: str


@router.post("/youtube", response_model=IdentifyResponse)
async def identify_youtube(req: YouTubeRequest, sb: Client = Depends(get_supabase)):
    # 1. URL validieren
    video_id = parse_youtube_url(req.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # 2. oEmbed Metadata laden
    oembed = fetch_oembed(req.url)
    if not oembed:
        raise HTTPException(status_code=502, detail="Could not fetch YouTube metadata")

    # 3. Artist + Title parsen
    artist, title = parse_title(oembed.get("title", ""), oembed.get("author_name", ""))

    # 4. Fuzzy DB Match — Songs mit ähnlichem Titel suchen
    result = sb.table("songs").select(
        "id, title, artist, album, bpm, musical_key, duration_sec"
    ).ilike("title", f"%{_escape_like(title)}%").limit(5).execute()

    if result.data:
        return IdentifyResponse(
            matched=True,
            song=result.data[0],
            parsed_artist=artist,
            parsed_title=title,
            message=f"Found match: {result.data[0]['artist']} - {result.data[0]['title']}",
        )

    # 5. Auch nach Artist suchen
    result2 = sb.table("songs").select(
        "id, title, artist, album, bpm, musical_key, duration_sec"
    ).ilike("artist", f"%{_escape_like(artist)}%").limit(5).execute()

    if result2.data:
        return IdentifyResponse(
            matched=True,
            song=result2.data[0],
            parsed_artist=artist,
            parsed_title=title,
            message=f"Found match by artist: {result2.data[0]['artist']} - {result2.data[0]['title']}",
        )

    return IdentifyResponse(
        matched=False,
        parsed_artist=artist,
        parsed_title=title,
        message="No match found. Upload the audio file for analysis.",
    )


@router.post("/soundcloud", response_model=IdentifyResponse)
async def identify_soundcloud(body: IdentifyRequest, sb: Client = Depends(get_supabase)):
    if not parse_soundcloud_url(body.url):
        raise HTTPException(status_code=400, detail="Invalid SoundCloud URL")

    meta = await sc_fetch_oembed(body.url)
    if not meta:
        raise HTTPException(status_code=502, detail="Could not fetch SoundCloud metadata")

    artist, title = sc_parse_title(meta["title"], meta["author_name"])
    match = await _match_in_db(artist, title, sb)

    return IdentifyResponse(
        matched=match is not None,
        song=match,
        parsed_artist=artist,
        parsed_title=title,
        message=f"Match: {match['artist']} — {match['title']}" if match else "Kein Match im Katalog gefunden.",
    )


@router.post("/spotify", response_model=IdentifyResponse)
async def identify_spotify(body: IdentifyRequest, sb: Client = Depends(get_supabase)):
    if not parse_spotify_url(body.url):
        raise HTTPException(status_code=400, detail="Invalid Spotify URL")

    meta = await sp_fetch_oembed(body.url)
    if not meta:
        raise HTTPException(status_code=502, detail="Could not fetch Spotify metadata")

    artist, title = sp_parse_title(meta["title"], meta["author_name"])
    match = await _match_in_db(artist, title, sb)

    return IdentifyResponse(
        matched=match is not None,
        song=match,
        parsed_artist=artist,
        parsed_title=title,
        message=f"Match: {match['artist']} — {match['title']}" if match else "Kein Match im Katalog gefunden.",
    )
