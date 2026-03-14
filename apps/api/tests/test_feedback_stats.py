import pytest
from unittest.mock import MagicMock

from app.routes.feedback import FeedbackStatsItem


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
