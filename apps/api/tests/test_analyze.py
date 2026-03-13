"""Tests for app/routes/analyze.py."""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.analyze import _job_status, update_job_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client():
    c = TestClient(app)
    return c


# ---------------------------------------------------------------------------
# Tests — no file upload
# ---------------------------------------------------------------------------

def test_upload_no_file(client):
    """POST /analyze without a file should return 422 (validation error)."""
    resp = client.post("/analyze")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests — unknown job ID
# ---------------------------------------------------------------------------

def test_get_results_unknown_job(client):
    """GET /analyze/<unknown>/results should return 404."""
    resp = client.get("/analyze/unknown-job-id/results")
    assert resp.status_code == 404


def test_get_stream_unknown_job(client):
    """GET /analyze/<unknown>/stream should return 404."""
    resp = client.get("/analyze/unknown-job-id/stream")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — non-audio upload
# ---------------------------------------------------------------------------

def test_upload_non_audio(client):
    """POST /analyze with a .txt file should be rejected with 400."""
    fake_content = b"hello, this is a text file"
    resp = client.post(
        "/analyze",
        files={"file": ("test.txt", io.BytesIO(fake_content), "text/plain")},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests — update_job_status helper
# ---------------------------------------------------------------------------

def test_update_job_status():
    """update_job_status() should set status and extra fields in _job_status."""
    job_id = "test-job-status-001"
    # Seed a job entry
    _job_status[job_id] = {"status": "queued", "progress": 0.0}

    update_job_status(job_id, "processing", progress=0.5)

    assert _job_status[job_id]["status"] == "processing"
    assert _job_status[job_id]["progress"] == 0.5

    # Update to completed with result
    update_job_status(job_id, "completed", progress=1.0, result={"bpm": 128.0})
    assert _job_status[job_id]["status"] == "completed"
    assert _job_status[job_id]["result"]["bpm"] == 128.0

    # Cleanup
    del _job_status[job_id]


def test_update_job_status_unknown_id():
    """update_job_status() on an unknown ID should silently do nothing."""
    update_job_status("nonexistent-id", "processing")
    assert "nonexistent-id" not in _job_status
