"""Tests for similarity pipeline logic: weights, dedup, MMR, genre resolution.

Tests pure functions without DB mocking — the refactored helpers are
designed to be testable in isolation.
"""

import pytest

from app.routes.similar import (
    _FusionWeights,
    _base_title,
    _compute_hc_similarity,
    _cosine_similarity,
    _deduplicate_versions,
    _determine_weights,
    _parse_vector,
)
from app.services.genre import DEEZER_GENRE_MAP, map_deezer_genre


# ---------------------------------------------------------------------------
# _determine_weights
# ---------------------------------------------------------------------------

class TestDetermineWeights:
    def test_default_no_mert(self):
        w = _determine_weights(focus=None, has_mert=False, genre_weights=None)
        assert w.learned == pytest.approx(0.80)
        assert w.mert == pytest.approx(0.0)
        assert w.hc == pytest.approx(0.20)

    def test_default_with_mert(self):
        w = _determine_weights(focus=None, has_mert=True, genre_weights=None)
        assert w.learned == pytest.approx(0.65)
        assert w.mert == pytest.approx(0.15)
        assert w.hc == pytest.approx(0.20)

    def test_focus_no_mert(self):
        w = _determine_weights(focus="timbre", has_mert=False, genre_weights=None)
        assert w.learned == pytest.approx(0.60)
        assert w.hc == pytest.approx(0.40)

    def test_focus_with_mert(self):
        w = _determine_weights(focus="timbre", has_mert=True, genre_weights=None)
        assert w.learned == pytest.approx(0.55)
        assert w.mert == pytest.approx(0.15)
        assert w.hc == pytest.approx(0.30)

    def test_genre_weights_no_mert(self):
        gw = {"timbre": 0.3, "rhythm": 0.2}
        w = _determine_weights(focus=None, has_mert=False, genre_weights=gw)
        assert w.mert == pytest.approx(0.0)
        assert w.learned + w.hc == pytest.approx(1.0)

    def test_genre_weights_with_mert(self):
        gw = {"timbre": 0.3, "rhythm": 0.2}
        w = _determine_weights(focus=None, has_mert=True, genre_weights=gw)
        assert w.mert == pytest.approx(0.15)
        assert w.learned + w.mert + w.hc == pytest.approx(1.0)

    def test_weights_always_sum_to_one(self):
        """All strategy combinations should produce weights summing to 1.0."""
        configs = [
            (None, False, None),
            (None, True, None),
            ("timbre", False, None),
            ("harmony", True, None),
            (None, False, {"timbre": 0.5}),
            (None, True, {"timbre": 0.3, "rhythm": 0.2, "harmony": 0.1}),
        ]
        for focus, has_mert, gw in configs:
            w = _determine_weights(focus, has_mert, gw)
            assert w.learned + w.mert + w.hc == pytest.approx(1.0), f"Failed for {focus=}, {has_mert=}"

    def test_invalid_focus_falls_through(self):
        """Unknown focus category should use default strategy."""
        w = _determine_weights(focus="nonexistent", has_mert=False, genre_weights=None)
        assert w.learned == pytest.approx(0.80)


# ---------------------------------------------------------------------------
# _base_title + _deduplicate_versions
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_base_title_strips_parentheses(self):
        assert _base_title("Café Del Mar (Deadmau5 Remix)") == "café del mar"

    def test_base_title_strips_brackets(self):
        assert _base_title("Children [Mix Cut]") == "children"

    def test_base_title_strips_multiple(self):
        assert _base_title("Silence (ASOT 1170) (Tiësto Remix)") == "silence"

    def test_base_title_preserves_clean_title(self):
        assert _base_title("Never Gonna Give You Up") == "never gonna give you up"

    def test_deduplicate_keeps_first(self):
        results = [
            {"id": "1", "artist": "Raze", "title": "Break 4 Love (Extended)", "similarity": 0.95},
            {"id": "2", "artist": "Raze", "title": "Break 4 Love (Radio Edit)", "similarity": 0.90},
            {"id": "3", "artist": "Other", "title": "Different Song", "similarity": 0.88},
        ]
        deduped = _deduplicate_versions(results)
        assert len(deduped) == 2
        assert deduped[0]["id"] == "1"  # Highest score kept
        assert deduped[1]["id"] == "3"

    def test_deduplicate_different_artists_not_collapsed(self):
        results = [
            {"id": "1", "artist": "Artist A", "title": "Love", "similarity": 0.9},
            {"id": "2", "artist": "Artist B", "title": "Love", "similarity": 0.8},
        ]
        deduped = _deduplicate_versions(results)
        assert len(deduped) == 2

    def test_deduplicate_empty(self):
        assert _deduplicate_versions([]) == []


# ---------------------------------------------------------------------------
# _compute_hc_similarity
# ---------------------------------------------------------------------------

class TestHcSimilarity:
    def test_flat_cosine(self):
        vec = [1.0, 0.0, 0.0]
        sim = _compute_hc_similarity(vec, vec, focus_dims=None, genre_weights=None)
        assert sim == pytest.approx(1.0)

    def test_focus_dims(self):
        q = [1.0, 0.0, 0.5, 0.0]
        r = [1.0, 0.0, 0.5, 0.0]
        sim = _compute_hc_similarity(q, r, focus_dims=[0, 2], genre_weights=None)
        assert sim == pytest.approx(1.0)

    def test_genre_weights_normalized(self):
        """Genre weights should be normalized so partial weights don't inflate score."""
        q = [0.5] * 44
        r = [0.5] * 44
        gw = {"timbre": 0.5}  # Only 1 of 5 categories has weight
        sim = _compute_hc_similarity(q, r, focus_dims=None, genre_weights=gw)
        # Identical vectors → similarity should be ~1.0 regardless of weight distribution
        assert sim == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical(self):
        assert _cosine_similarity([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)

    def test_orthogonal(self):
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite(self):
        assert _cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_zero_vector(self):
        assert _cosine_similarity([0, 0], [1, 2]) == 0.0


# ---------------------------------------------------------------------------
# _parse_vector
# ---------------------------------------------------------------------------

class TestParseVector:
    def test_none(self):
        assert _parse_vector(None) is None

    def test_list_passthrough(self):
        assert _parse_vector([1.0, 2.0]) == [1.0, 2.0]

    def test_string_json(self):
        assert _parse_vector("[1.0, 2.0, 3.0]") == [1.0, 2.0, 3.0]


# ---------------------------------------------------------------------------
# Genre mapping
# ---------------------------------------------------------------------------

class TestGenreMapping:
    def test_known_genres(self):
        assert map_deezer_genre(106) == "Electro"
        assert map_deezer_genre(113) == "Dance"
        assert map_deezer_genre(116) == "Hip Hop"

    def test_unknown_falls_back(self):
        assert map_deezer_genre(99999) == "Electronic"
        assert map_deezer_genre(None) == "Electronic"

    def test_map_has_expected_entries(self):
        assert len(DEEZER_GENRE_MAP) >= 10
