"""AcoustID fingerprinting and lookup service."""
import logging
import os
import shutil
import subprocess
import time

import httpx

logger = logging.getLogger(__name__)

_ACOUSTID_API_URL = "https://api.acoustid.org/v2/lookup"
_MIN_INTERVAL = 0.5  # max 2 requests per second
_last_call: float = 0.0


def fingerprint_file(audio_path: str) -> tuple[str, int] | None:
    """Compute AcoustID fingerprint for an audio file using fpcalc.

    Returns (fingerprint, duration) or None if fpcalc is not installed or fails.
    """
    fpcalc = shutil.which("fpcalc")
    if fpcalc is None:
        logger.warning("fpcalc not found — install chromaprint to enable AcoustID fingerprinting")
        return None

    try:
        result = subprocess.run(
            [fpcalc, "-plain", audio_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning("fpcalc exited with code %d: %s", result.returncode, result.stderr)
            return None

        lines = result.stdout.strip().splitlines()
        if len(lines) < 2:
            logger.warning("fpcalc output too short: %r", result.stdout)
            return None

        duration = int(lines[0].strip())
        fingerprint = lines[1].strip()
        return fingerprint, duration

    except subprocess.TimeoutExpired:
        logger.warning("fpcalc timed out for %s", audio_path)
        return None
    except Exception as exc:
        logger.warning("fpcalc failed for %s: %s", audio_path, exc)
        return None


def lookup(fingerprint: str, duration: int, api_key: str) -> str | None:
    """Look up a fingerprint on AcoustID and return the MusicBrainz Recording ID.

    Rate-limited to max 2 requests per second.
    Returns MBID string or None if not found / error.
    """
    global _last_call

    if not api_key:
        logger.warning("ACOUSTID_API_KEY not set — skipping AcoustID lookup")
        return None

    # Rate limiting: ensure at least _MIN_INTERVAL between calls
    elapsed = time.monotonic() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call = time.monotonic()

    try:
        response = httpx.post(
            _ACOUSTID_API_URL,
            data={
                "client": api_key,
                "fingerprint": fingerprint,
                "duration": str(duration),
                "meta": "recordingids",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            return None

        # Take first result with recordings
        for result in results:
            recordings = result.get("recordings", [])
            if recordings:
                return recordings[0].get("id")

        return None

    except httpx.HTTPStatusError as exc:
        logger.warning("AcoustID HTTP error: %s", exc)
        return None
    except Exception as exc:
        logger.warning("AcoustID lookup failed: %s", exc)
        return None


def lookup_file(audio_path: str) -> str | None:
    """Convenience: fingerprint a file and look it up on AcoustID.

    Returns MBID or None.
    """
    api_key = os.environ.get("ACOUSTID_API_KEY", "")
    if not api_key:
        logger.warning("ACOUSTID_API_KEY not set — skipping AcoustID lookup")
        return None

    result = fingerprint_file(audio_path)
    if result is None:
        return None

    fingerprint, duration = result
    return lookup(fingerprint, duration, api_key)
