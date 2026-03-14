"""Shared pytest fixtures for beattrack API tests."""
import io
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Set env vars before any app import so get_supabase() won't crash
# ---------------------------------------------------------------------------
os.environ.setdefault("SUPABASE_URL", "http://mock")
os.environ.setdefault("SUPABASE_ANON_KEY", "mock")

from app.main import app  # noqa: E402 — must be after env vars
from app.db import get_supabase  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).parent.parent.parent.parent / "phase0" / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_supabase_mock():
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    for method in ("select", "eq", "ilike", "in_", "range", "insert", "single", "limit"):
        getattr(builder, method).return_value = builder
    return sb, builder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """TestClient with dependency_overrides cleanup."""
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def supabase_mock():
    """Return (sb, builder) MagicMock tuple."""
    return _make_supabase_mock()


@pytest.fixture()
def audio_wav_path():
    """Absolute path to sine_440hz.wav test fixture."""
    p = _FIXTURE_DIR / "sine_440hz.wav"
    assert p.exists(), f"Fixture not found: {p}"
    return str(p)


@pytest.fixture()
def audio_wav_1000_path():
    """Absolute path to sine_1000hz.wav test fixture."""
    p = _FIXTURE_DIR / "sine_1000hz.wav"
    assert p.exists(), f"Fixture not found: {p}"
    return str(p)


@pytest.fixture()
def fake_mp3_path(tmp_path):
    """Temp file with .mp3 extension but PHP content (MIME mismatch test)."""
    f = tmp_path / "fake.mp3"
    f.write_bytes(b"<?php echo 'evil'; ?>")
    return str(f)


@pytest.fixture()
def oversized_file_path(tmp_path):
    """Sparse temp file >50 MB (does not actually allocate 50 MB on disk)."""
    f = tmp_path / "big.mp3"
    # Create a sparse file: seek past 50 MB + 1 byte and write a single null byte
    fifty_mb_plus_one = 50 * 1024 * 1024 + 1
    with open(f, "wb") as fh:
        fh.seek(fifty_mb_plus_one)
        fh.write(b"\x00")
    return str(f)
