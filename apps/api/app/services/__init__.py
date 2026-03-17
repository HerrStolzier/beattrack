"""Shared utilities for music platform services."""
import re

# Suffixes to strip from titles (case-insensitive)
_NOISE_RE = re.compile(
    r"\s*[\(\[](Official|Audio|Lyric|Music|HD|4K|Visualizer|Live|Remix|Explicit|Remaster)"
    r"[^\)\]]*[\)\]]",
    re.IGNORECASE,
)


def parse_title(title: str, author_name: str = "") -> tuple[str, str]:
    """Extract (artist, track_title) from platform metadata.

    Handles common patterns:
      - "Artist - Title"
      - Plain title with separate author_name

    Used by SoundCloud, Spotify, and Apple Music services.
    """
    cleaned = _NOISE_RE.sub("", title).strip()

    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()

    artist = author_name.strip() if author_name else "Unknown"
    return artist, cleaned if cleaned else title
