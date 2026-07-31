"""Tests for app/routes/analyze.py."""
import io
from unittest.mock import MagicMock, patch

from app.services import jobs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _supabase_mock():
    """Supabase mock whose builder methods chain, exposing the update payload."""
    sb = MagicMock()
    builder = sb.table.return_value
    for method in ("select", "eq", "in_", "insert", "update"):
        getattr(builder, method).return_value = builder
    return sb, builder


# ---------------------------------------------------------------------------
# Tests — no file upload
# ---------------------------------------------------------------------------

def test_upload_no_file(client):
    """POST /analyze without a file should return 422 (validation error)."""
    resp = client.post("/analyze")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests — unknown job ID
#
# Job status lives in Postgres since the split into api/worker containers, so
# these routes hit the database. get_job is patched to keep tests offline.
# ---------------------------------------------------------------------------

def test_get_results_unknown_job(client):
    """GET /analyze/<unknown>/results should return 404."""
    with patch("app.services.jobs.get_job", return_value=None):
        resp = client.get("/analyze/unknown-job-id/results")
    assert resp.status_code == 404


def test_get_stream_unknown_job(client):
    """GET /analyze/<unknown>/stream should return 404."""
    with patch("app.services.jobs.get_job", return_value=None):
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
# Tests — jobs.update_job_status
# ---------------------------------------------------------------------------

def test_update_job_status_writes_progress():
    """update_job_status() should write status and progress to analysis_jobs."""
    sb, builder = _supabase_mock()
    with patch("app.services.jobs.get_supabase", return_value=sb):
        jobs.update_job_status("test-job-status-001", "processing", progress=0.5)

    row = builder.update.call_args[0][0]
    assert row["status"] == "processing"
    assert row["progress"] == 0.5
    # Not just the payload: a dropped execute() or a wrong table would leave the
    # worker's progress unwritten while this test still passed.
    sb.table.assert_called_with("analysis_jobs")
    builder.eq.assert_called_with("id", "test-job-status-001")
    builder.execute.assert_called_once()


def test_update_job_status_completed_carries_result():
    """A completed job should carry its result and a completion timestamp."""
    sb, builder = _supabase_mock()
    with patch("app.services.jobs.get_supabase", return_value=sb):
        jobs.update_job_status(
            "test-job-status-001", "completed", progress=1.0, result={"bpm": 128.0}
        )

    row = builder.update.call_args[0][0]
    assert row["status"] == "completed"
    assert row["result"]["bpm"] == 128.0
    assert row["completed_at"]


def test_update_job_status_survives_db_error():
    """A failing status update must never abort the analysis."""
    sb = MagicMock()
    sb.table.side_effect = RuntimeError("database unreachable")
    with patch("app.services.jobs.get_supabase", return_value=sb):
        jobs.update_job_status("nonexistent-id", "processing")


# ---------------------------------------------------------------------------
# Tests — jobs.get_job
# ---------------------------------------------------------------------------

def test_get_job_unknown_returns_none():
    """An unknown job ID should yield None, not an empty dict."""
    sb, builder = _supabase_mock()
    builder.execute.return_value = MagicMock(data=[])
    with patch("app.services.jobs.get_supabase", return_value=sb):
        assert jobs.get_job("nonexistent-id") is None

    # The mock answers empty for any query, so pin the scoping explicitly:
    # without the id filter get_job could hand back a different job's row.
    sb.table.assert_called_with("analysis_jobs")
    builder.eq.assert_called_with("id", "nonexistent-id")


def test_get_job_reports_stalled_job_as_failed():
    """A processing job without progress past STALL_AFTER_SEC counts as failed."""
    from datetime import datetime, timedelta, timezone

    stalled_at = datetime.now(timezone.utc) - timedelta(seconds=jobs.STALL_AFTER_SEC + 60)
    sb, builder = _supabase_mock()
    builder.execute.return_value = MagicMock(data=[{
        "id": "stalled-job",
        "status": "processing",
        "progress": 0.1,
        "updated_at": stalled_at.isoformat(),
        "audio_path": "/data/uploads/stalled-job.mp3",
    }])

    with patch("app.services.jobs.get_supabase", return_value=sb):
        job = jobs.get_job("stalled-job")

    assert job["status"] == "failed"
    assert "stalled" in job["error"].lower()
