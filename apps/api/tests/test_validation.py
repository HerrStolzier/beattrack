"""Tests for app/services/validation.py."""
import io
import os
import random

import pytest
from fastapi import HTTPException, UploadFile

from app.services.validation import validate_audio, validate_upload


# ---------------------------------------------------------------------------
# validate_audio (sync)
# ---------------------------------------------------------------------------

def test_validate_audio_valid_wav(audio_wav_path):
    result = validate_audio(audio_wav_path)
    assert "duration_sec" in result
    assert result["duration_sec"] > 0


def test_validate_audio_corrupt_file(tmp_path):
    corrupt = tmp_path / "corrupt.wav"
    corrupt.write_bytes(bytes(random.getrandbits(8) for _ in range(1024)))
    with pytest.raises(HTTPException) as exc_info:
        validate_audio(str(corrupt))
    assert exc_info.value.status_code == 422


def test_validate_audio_nonexistent(tmp_path):
    missing = str(tmp_path / "does_not_exist.wav")
    with pytest.raises(HTTPException) as exc_info:
        validate_audio(missing)
    assert exc_info.value.status_code in (422, 500)


# ---------------------------------------------------------------------------
# validate_upload (async)
# ---------------------------------------------------------------------------

def _make_upload_file(content: bytes, filename: str = "test.mp3", size: int | None = None):
    """Create a minimal UploadFile backed by BytesIO."""
    file_obj = io.BytesIO(content)
    upload = UploadFile(filename=filename, file=file_obj)
    # Manually set size so validation can use it without reading
    upload.size = size if size is not None else len(content)
    return upload


async def test_validate_upload_valid_mp3():
    """A file starting with ID3 magic bytes should pass validation."""
    # Minimal ID3v2.4 header followed by zeros — enough for magic detection
    mp3_content = b"ID3\x04\x00\x00" + b"\x00" * 128
    upload = _make_upload_file(mp3_content, filename="track.mp3")
    # Should not raise
    await validate_upload(upload)


async def test_validate_upload_fake_audio(fake_mp3_path):
    """A .mp3 file with PHP content should be rejected (400)."""
    with open(fake_mp3_path, "rb") as fh:
        content = fh.read()
    upload = _make_upload_file(content, filename="fake.mp3")
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(upload)
    assert exc_info.value.status_code == 400


async def test_validate_upload_too_large(oversized_file_path):
    """A file larger than 50 MB should be rejected (400)."""
    fifty_mb_plus_one = 50 * 1024 * 1024 + 1
    # We only pass size metadata — no need to load the full sparse file into memory
    content = b"ID3\x04\x00\x00" + b"\x00" * 64  # valid-looking content for MIME pass
    upload = _make_upload_file(content, filename="big.mp3", size=fifty_mb_plus_one)
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(upload)
    assert exc_info.value.status_code == 400
