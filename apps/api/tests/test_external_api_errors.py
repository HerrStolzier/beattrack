"""Tests for shared external music API error categories."""

import httpx
import pytest

from app.services.external_errors import (
    ExternalAPINotFound,
    ExternalAPIRateLimited,
    ExternalAPITemporaryUnavailable,
    raise_for_external_response,
)


def _response(status_code: int) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com")
    return httpx.Response(status_code, request=request)


def test_maps_not_found_response():
    with pytest.raises(ExternalAPINotFound) as exc_info:
        raise_for_external_response(_response(404), "YouTube")

    assert exc_info.value.code == "track_not_found"
    assert exc_info.value.http_status == 404


def test_maps_rate_limit_response():
    with pytest.raises(ExternalAPIRateLimited) as exc_info:
        raise_for_external_response(_response(429), "Spotify")

    assert exc_info.value.code == "rate_limited"
    assert exc_info.value.http_status == 429


def test_maps_5xx_response():
    with pytest.raises(ExternalAPITemporaryUnavailable) as exc_info:
        raise_for_external_response(_response(503), "Deezer")

    assert exc_info.value.code == "temporarily_unavailable"
    assert exc_info.value.http_status == 503
