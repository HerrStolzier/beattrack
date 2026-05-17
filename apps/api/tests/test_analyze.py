"""Tests for app/routes/analyze.py and persistent analysis job status."""
import importlib
import io
import sys
import types
from unittest.mock import MagicMock


def _response(data):
    resp = MagicMock()
    resp.data = data
    return resp


def _supabase_table_mock():
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    for method in (
        "select",
        "eq",
        "insert",
        "update",
        "maybe_single",
    ):
        getattr(builder, method).return_value = builder
    return sb, builder


def _install_fake_procrastinate(monkeypatch):
    fake_procrastinate = types.SimpleNamespace()

    class FakeConnector:
        def __init__(self, *args, **kwargs):
            pass

    class FakeApp:
        def __init__(self, *args, **kwargs):
            pass

        def task(self, *args, **kwargs):
            def decorate(func):
                func.defer = lambda **defer_kwargs: None
                return func

            return decorate

    fake_procrastinate.SyncPsycopgConnector = FakeConnector
    fake_procrastinate.App = FakeApp
    monkeypatch.setitem(sys.modules, "procrastinate", fake_procrastinate)


def test_create_analysis_job_inserts_queued_row(monkeypatch):
    from app.services import analysis_jobs

    sb, builder = _supabase_table_mock()
    builder.execute.return_value = _response([{}])
    monkeypatch.setattr(analysis_jobs, "get_supabase", lambda: sb)

    analysis_jobs.create_analysis_job(
        "11111111-1111-1111-1111-111111111111",
        audio_path="/tmp/upload.mp3",
        duration_sec=42.5,
    )

    sb.table.assert_called_once_with("analysis_jobs")
    inserted = builder.insert.call_args.args[0]
    assert inserted["id"] == "11111111-1111-1111-1111-111111111111"
    assert inserted["status"] == "queued"
    assert inserted["progress"] == 0.0
    assert inserted["audio_path"] == "/tmp/upload.mp3"
    assert inserted["duration_sec"] == 42.5
    assert "created_at" in inserted
    assert "updated_at" in inserted


def test_get_analysis_job_returns_row(monkeypatch):
    from app.services import analysis_jobs

    sb, builder = _supabase_table_mock()
    row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "status": "completed",
        "progress": 1.0,
        "result": {"bpm": 128.0},
    }
    builder.execute.return_value = _response(row)
    monkeypatch.setattr(analysis_jobs, "get_supabase", lambda: sb)

    job = analysis_jobs.get_analysis_job("11111111-1111-1111-1111-111111111111")

    assert job == row
    builder.select.assert_called_once_with("*")
    builder.eq.assert_called_once_with("id", "11111111-1111-1111-1111-111111111111")
    builder.maybe_single.assert_called_once()


def test_get_analysis_job_returns_none_for_missing_row(monkeypatch):
    from app.services import analysis_jobs

    sb, builder = _supabase_table_mock()
    builder.execute.return_value = _response(None)
    monkeypatch.setattr(analysis_jobs, "get_supabase", lambda: sb)

    assert analysis_jobs.get_analysis_job("11111111-1111-1111-1111-111111111111") is None


def test_update_analysis_job_writes_status_and_result(monkeypatch):
    from app.services import analysis_jobs

    sb, builder = _supabase_table_mock()
    builder.execute.return_value = _response([{}])
    monkeypatch.setattr(analysis_jobs, "get_supabase", lambda: sb)

    analysis_jobs.update_analysis_job(
        "11111111-1111-1111-1111-111111111111",
        "completed",
        progress=1.0,
        result={"bpm": 128.0},
    )

    payload = builder.update.call_args.args[0]
    assert payload["status"] == "completed"
    assert payload["progress"] == 1.0
    assert payload["result"] == {"bpm": 128.0}
    assert "updated_at" in payload
    assert "completed_at" in payload
    builder.eq.assert_called_once_with("id", "11111111-1111-1111-1111-111111111111")


def test_update_analysis_job_writes_error_fields(monkeypatch):
    from app.services import analysis_jobs

    sb, builder = _supabase_table_mock()
    builder.execute.return_value = _response([{}])
    monkeypatch.setattr(analysis_jobs, "get_supabase", lambda: sb)

    analysis_jobs.update_analysis_job(
        "11111111-1111-1111-1111-111111111111",
        "failed",
        progress=1.0,
        last_error="Audio analysis timed out.",
        error_code="feature_extraction_failed",
    )

    payload = builder.update.call_args.args[0]
    assert payload["status"] == "failed"
    assert payload["last_error"] == "Audio analysis timed out."
    assert payload["error_code"] == "feature_extraction_failed"
    assert "completed_at" in payload


def test_upload_no_file(client):
    """POST /analyze without a file should return 422 (validation error)."""
    resp = client.post("/analyze")
    assert resp.status_code == 422


def test_get_results_unknown_job(client, monkeypatch):
    """GET /analyze/<unknown>/results should return 404."""
    monkeypatch.setattr("app.routes.analyze.get_analysis_job", lambda job_id: None)

    resp = client.get("/analyze/11111111-1111-1111-1111-111111111111/results")

    assert resp.status_code == 404


def test_get_results_completed_job(client, monkeypatch):
    """GET /analyze/<job>/results should return persisted completed results."""
    monkeypatch.setattr(
        "app.routes.analyze.get_analysis_job",
        lambda job_id: {
            "id": job_id,
            "status": "completed",
            "progress": 1.0,
            "result": {"bpm": 128.0},
            "last_error": None,
            "error_code": None,
        },
    )

    resp = client.get("/analyze/11111111-1111-1111-1111-111111111111/results")

    assert resp.status_code == 200
    assert resp.json() == {
        "job_id": "11111111-1111-1111-1111-111111111111",
        "status": "completed",
        "progress": 1.0,
        "result": {"bpm": 128.0},
        "error": None,
        "error_code": None,
    }


def test_get_results_failed_job(client, monkeypatch):
    """GET /analyze/<job>/results should expose persisted error details."""
    monkeypatch.setattr(
        "app.routes.analyze.get_analysis_job",
        lambda job_id: {
            "id": job_id,
            "status": "failed",
            "progress": 1.0,
            "result": None,
            "last_error": "Audio analysis timed out.",
            "error_code": "feature_extraction_failed",
        },
    )

    resp = client.get("/analyze/11111111-1111-1111-1111-111111111111/results")

    assert resp.status_code == 200
    assert resp.json()["error"] == "Audio analysis timed out."
    assert resp.json()["error_code"] == "feature_extraction_failed"


def test_get_stream_unknown_job(client, monkeypatch):
    """GET /analyze/<unknown>/stream should return 404."""
    monkeypatch.setattr("app.routes.analyze.get_analysis_job", lambda job_id: None)

    resp = client.get("/analyze/11111111-1111-1111-1111-111111111111/stream")

    assert resp.status_code == 404


def test_upload_non_audio(client):
    """POST /analyze with a .txt file should be rejected with 400."""
    fake_content = b"hello, this is a text file"
    resp = client.post(
        "/analyze",
        files={"file": ("test.txt", io.BytesIO(fake_content), "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_creates_persistent_job_and_enqueues(client, monkeypatch, tmp_path):
    """POST /analyze should create a persistent queued job before enqueueing."""
    created = {}

    async def fake_validate_upload(file):
        return None

    monkeypatch.setattr("app.routes.analyze.validate_upload", fake_validate_upload)
    monkeypatch.setattr(
        "app.routes.analyze.validate_audio",
        lambda path: {"duration_sec": 12.0},
    )
    monkeypatch.setattr("app.routes.analyze.TEMP_DIR", str(tmp_path))

    def fake_create(job_id, *, audio_path, duration_sec):
        created["job_id"] = job_id
        created["audio_path"] = audio_path
        created["duration_sec"] = duration_sec

    monkeypatch.setattr("app.routes.analyze.create_analysis_job", fake_create)

    class FakeAnalyzeAudio:
        def defer(self, *, audio_path, job_id):
            created["deferred"] = {"audio_path": audio_path, "job_id": job_id}

    fake_workers = types.SimpleNamespace(analyze_audio=FakeAnalyzeAudio())
    monkeypatch.setitem(sys.modules, "app.workers", fake_workers)

    resp = client.post(
        "/analyze",
        files={"file": ("test.mp3", io.BytesIO(b"audio bytes"), "audio/mpeg")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    assert created["job_id"] == body["job_id"]
    assert created["duration_sec"] == 12.0
    assert created["deferred"]["job_id"] == body["job_id"]


def test_worker_updates_persistent_job_to_completed(monkeypatch):
    """The worker should persist processing and completed state changes."""
    _install_fake_procrastinate(monkeypatch)
    sys.modules.pop("app.workers", None)
    workers = importlib.import_module("app.workers")

    updates = []

    monkeypatch.setattr(
        "app.services.features.extract_features_safe",
        lambda path: {
            "learned": [0.1] * 200,
            "handcrafted": [0.2] * 44,
            "bpm": 128.0,
            "key": "Am",
            "duration": 30.0,
        },
    )
    monkeypatch.setattr(
        workers,
        "process_analysis_result",
        lambda features, job_id, audio_path: {"song_id": job_id, "bpm": features["bpm"]},
    )
    monkeypatch.setattr(
        "app.services.analysis_jobs.update_analysis_job",
        lambda job_id, status, **kwargs: updates.append((job_id, status, kwargs)),
    )

    workers.analyze_audio(
        None,
        job_id="11111111-1111-1111-1111-111111111111",
        audio_path="/tmp/a.mp3",
    )

    assert updates[0][1] == "processing"
    assert updates[0][2]["progress"] == 0.1
    assert updates[-1][1] == "completed"
    assert updates[-1][2]["progress"] == 1.0
    assert updates[-1][2]["result"]["bpm"] == 128.0
