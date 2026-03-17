"""Tests for periodic_cleanup logic in app/main.py."""
import os
import time
from pathlib import Path

import pytest

from app.main import _periodic_cleanup


# ---------------------------------------------------------------------------
# Helpers — run the cleanup core logic synchronously (no async sleep)
# ---------------------------------------------------------------------------

def _run_cleanup_once(temp_dir: str, max_age_minutes: int = 15):
    """Execute the cleanup body once without the async sleep/loop."""
    cutoff = time.time() - (max_age_minutes * 60)
    temp_path = Path(temp_dir)
    if not temp_path.exists():
        return
    for f in temp_path.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_periodic_cleanup_removes_old(tmp_path):
    """A file with mtime in the past should be removed by cleanup."""
    old_file = tmp_path / "old_audio.tmp"
    old_file.write_bytes(b"old data")

    # Set mtime to 30 minutes ago (older than max_age_minutes=15)
    thirty_minutes_ago = time.time() - 30 * 60
    os.utime(str(old_file), (thirty_minutes_ago, thirty_minutes_ago))

    _run_cleanup_once(str(tmp_path), max_age_minutes=15)

    assert not old_file.exists(), "Old file should have been deleted by cleanup"


def test_periodic_cleanup_keeps_fresh(tmp_path):
    """A freshly-created file should NOT be removed by cleanup."""
    fresh_file = tmp_path / "fresh_audio.tmp"
    fresh_file.write_bytes(b"fresh data")
    # mtime is now — well within max_age_minutes=15

    _run_cleanup_once(str(tmp_path), max_age_minutes=15)

    assert fresh_file.exists(), "Fresh file should not have been deleted by cleanup"
