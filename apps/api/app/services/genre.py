"""Genre resolution via Deezer Album API.

Deezer has no genre at track level — only at album level.
We fetch /album/{id} to get genre_id + genres.data[] and map
to BeatTrack's internal genre taxonomy.
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deezer genre_id → BeatTrack genre mapping
#
# Deezer top-level genres (from /genre endpoint):
#   0=All, 85=Alternative, 106=Electro, 113=Dance, 129=Jazz,
#   130=Acoustic, 132=Asian, 152=Klassik, 116=Rap/Hip Hop,
#   129=Jazz, 165=R&B, 466=Folk, 464=Metal, 169=Soul/Funk,
#   98=Reggae, 173=Films/Games, 186=Latino, 197=Monde, 2=Country
#
# We keep electronic sub-mapping granular for BeatTrack's catalog.
# ---------------------------------------------------------------------------

DEEZER_GENRE_MAP: dict[int, str] = {
    # Electronic family
    106: "Electro",
    113: "Dance",
    # Adjacent genres worth keeping
    85: "Alternative",
    116: "Hip Hop",
    129: "Jazz",
    165: "R&B",
    169: "Soul / Funk",
    464: "Metal",
    466: "Folk",
    152: "Klassik",
    130: "Acoustic",
    98: "Reggae",
    186: "Latino",
    2: "Country",
    173: "Soundtrack",
    132: "World",
    197: "World",
}

# Genre IDs that are Electronic-adjacent (for catalog filtering)
ELECTRONIC_GENRE_IDS: set[int] = {106, 113, 85}


def map_deezer_genre(genre_id: int | None) -> str:
    """Map a Deezer genre_id to BeatTrack's internal genre label."""
    if genre_id and genre_id in DEEZER_GENRE_MAP:
        return DEEZER_GENRE_MAP[genre_id]
    return "Electronic"


def resolve_genre_from_album(album_id: int | None, *, deezer_get: callable) -> str:
    """Fetch album from Deezer and extract genre.

    Args:
        album_id: Deezer album ID (from track search response).
        deezer_get: Callable that takes an endpoint string and returns dict|None.

    Returns:
        Genre string (falls back to "Electronic" if unavailable).
    """
    if not album_id:
        return "Electronic"

    album = deezer_get(f"/album/{album_id}")
    if not album or not isinstance(album, dict):
        return "Electronic"

    # Primary: genre_id field
    genre_id = album.get("genre_id")
    if genre_id and genre_id in DEEZER_GENRE_MAP:
        return DEEZER_GENRE_MAP[genre_id]

    # Fallback: first entry in genres.data[]
    genres_data = album.get("genres", {}).get("data", [])
    for g in genres_data:
        gid = g.get("id")
        if gid and gid in DEEZER_GENRE_MAP:
            return DEEZER_GENRE_MAP[gid]
        # If genre not in our map, use Deezer's name directly
        name = g.get("name")
        if name:
            return name

    return "Electronic"
