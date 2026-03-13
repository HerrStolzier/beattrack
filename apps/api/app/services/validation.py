"""Audio validation utilities for upload and file integrity checks."""
import json
import logging
import subprocess

import magic
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

_ALLOWED_MIME_TYPES = {
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/ogg",
    "audio/x-flac",
}

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB in bytes
_MAX_DURATION_SEC = 900.0  # 15 minutes


async def validate_upload(file: UploadFile) -> None:
    """Validate an uploaded file for MIME type and size constraints.

    Reads the file content, checks magic bytes for a valid audio MIME type,
    and enforces a 50 MB size limit.

    Raises:
        HTTPException: 400 if MIME type is not audio or file exceeds 50 MB.
    """
    # Read the full content to check both size and magic bytes
    content = await file.read()

    # Reset stream so downstream consumers can re-read if needed
    await file.seek(0)

    # Size check — prefer Content-Length header when available, fall back to len(content)
    content_length = file.size if file.size is not None else len(content)
    if content_length > _MAX_FILE_SIZE:
        logger.warning(
            "Upload rejected: file size %d bytes exceeds limit of %d bytes",
            content_length,
            _MAX_FILE_SIZE,
        )
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed size is 50 MB.",
        )

    # MIME check via magic bytes (fake-file detection)
    # Use larger buffer — ID3-tagged MP3s may need >2KB for libmagic to find the MPEG frame
    detected_mime = magic.from_buffer(content[:16384], mime=True)
    # Fallback: ID3 header (0x494433) is always audio/mpeg
    if detected_mime == "application/octet-stream" and content[:3] == b"ID3":
        detected_mime = "audio/mpeg"
    logger.debug("Detected MIME type from magic bytes: %s", detected_mime)

    if detected_mime not in _ALLOWED_MIME_TYPES:
        logger.warning(
            "Upload rejected: detected MIME type '%s' is not an allowed audio type",
            detected_mime,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{detected_mime}'. "
                "Accepted types: MP3, WAV, FLAC, OGG."
            ),
        )


def validate_audio(path: str) -> dict:
    """Run ffprobe on a local file and validate it is a conforming audio file.

    Checks that the file is a valid audio container and that its duration does
    not exceed 15 minutes (900 seconds).

    Args:
        path: Absolute path to the audio file on disk.

    Returns:
        dict with key ``duration_sec`` (float).

    Raises:
        HTTPException: 422 if ffprobe fails or the file is not valid audio.
        HTTPException: 400 if duration exceeds the allowed maximum.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        logger.error("ffprobe not found — cannot validate audio file")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: ffprobe not available.",
        )
    except subprocess.TimeoutExpired:
        logger.error("ffprobe timed out while probing '%s'", path)
        raise HTTPException(
            status_code=422,
            detail="Audio validation timed out.",
        )

    if result.returncode != 0:
        logger.warning(
            "ffprobe returned non-zero exit code %d for '%s': %s",
            result.returncode,
            path,
            result.stderr,
        )
        raise HTTPException(
            status_code=422,
            detail="Invalid or unreadable audio file.",
        )

    try:
        probe = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse ffprobe output for '%s': %s", path, exc)
        raise HTTPException(
            status_code=422,
            detail="Audio validation failed: unexpected probe output.",
        )

    # Require at least one audio stream
    streams = probe.get("streams", [])
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio_streams:
        logger.warning("No audio streams found in '%s'", path)
        raise HTTPException(
            status_code=422,
            detail="File contains no audio streams.",
        )

    # Extract duration from format block (most reliable source)
    fmt = probe.get("format", {})
    raw_duration = fmt.get("duration")
    if raw_duration is None:
        # Fall back to first audio stream duration
        raw_duration = audio_streams[0].get("duration")

    if raw_duration is None:
        logger.warning("Could not determine duration for '%s'", path)
        raise HTTPException(
            status_code=422,
            detail="Could not determine audio duration.",
        )

    try:
        duration_sec = float(raw_duration)
    except (TypeError, ValueError) as exc:
        logger.error("Non-numeric duration value '%s' for '%s': %s", raw_duration, path, exc)
        raise HTTPException(
            status_code=422,
            detail="Audio validation failed: invalid duration value.",
        )

    if duration_sec > _MAX_DURATION_SEC:
        logger.warning(
            "Audio rejected: duration %.1f s exceeds limit of %.1f s for '%s'",
            duration_sec,
            _MAX_DURATION_SEC,
            path,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Audio too long ({duration_sec:.0f} s). "
                "Maximum allowed duration is 15 minutes."
            ),
        )

    logger.info("Audio validated: duration=%.1f s, path='%s'", duration_sec, path)
    return {"duration_sec": duration_sec}
