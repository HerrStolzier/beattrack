from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _mock_supabase():
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    builder.select.return_value = builder
    builder.limit.return_value = builder
    builder.execute.return_value = MagicMock(data=[])
    return sb


def test_health_returns_ok(monkeypatch):
    monkeypatch.setattr("app.main.get_supabase", lambda: _mock_supabase())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


def test_health_returns_degraded_when_db_fails(monkeypatch):
    def _raise():
        raise RuntimeError("supabase offline")

    monkeypatch.setattr("app.main.get_supabase", _raise)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["db"] == "error"
