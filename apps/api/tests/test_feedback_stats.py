from unittest.mock import MagicMock

from app.routes import feedback
from app.routes.feedback import FeedbackStatsItem


def _make_response(data):
    resp = MagicMock()
    resp.data = data
    return resp


def _make_supabase_mock():
    sb = MagicMock()
    builder = MagicMock()
    sb.table.return_value = builder
    for method in ("select", "order", "limit"):
        getattr(builder, method).return_value = builder
    return sb, builder


def test_feedback_stats_item_model():
    """FeedbackStatsItem model validates correctly."""
    item = FeedbackStatsItem(
        query_song_id="abc-123",
        result_song_id="def-456",
        total_up=5,
        total_down=2,
        net_score=3,
        total_votes=7,
    )
    assert item.net_score == 3
    assert item.total_votes == 7


def test_feedback_stats_requires_admin_secret_config(client, monkeypatch):
    monkeypatch.delenv("ADMIN_SECRET", raising=False)

    resp = client.get("/feedback/stats")

    assert resp.status_code == 503
    assert resp.json()["detail"] == "ADMIN_SECRET not configured"


def test_feedback_stats_rejects_missing_bearer_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "test-secret")

    resp = client.get("/feedback/stats")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Unauthorized"


def test_feedback_stats_requires_service_role_client(client, monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "test-secret")
    monkeypatch.setattr(
        feedback,
        "get_supabase_admin",
        lambda: (_ for _ in ()).throw(RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured")),
    )

    resp = client.get("/feedback/stats", headers={"Authorization": "Bearer test-secret"})

    assert resp.status_code == 503
    assert resp.json()["detail"] == "SUPABASE_SERVICE_ROLE_KEY not configured"


def test_feedback_stats_uses_admin_client(client, monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "test-secret")
    sb, builder = _make_supabase_mock()
    builder.execute.return_value = _make_response(
        [
            {
                "query_song_id": "abc-123",
                "result_song_id": "def-456",
                "total_up": 5,
                "total_down": 2,
                "net_score": 3,
                "total_votes": 7,
            }
        ]
    )
    monkeypatch.setattr(feedback, "get_supabase_admin", lambda: sb)

    resp = client.get("/feedback/stats", headers={"Authorization": "Bearer test-secret"})

    assert resp.status_code == 200
    assert resp.json()[0]["net_score"] == 3
    sb.table.assert_called_once_with("feedback_stats")
