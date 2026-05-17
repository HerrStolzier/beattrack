"""Tests for shared external music API error categories."""

import httpx
import pytest

from app.services.external_errors import (
    ExternalAPINotFound,
    ExternalAPIRateLimited,
    ExternalAPITemporaryUnavailable,
    request_with_retries,
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


@pytest.mark.asyncio
async def test_request_with_retries_retries_temporary_5xx(monkeypatch):
    calls = []

    async def fake_sleep(_seconds):
        return None

    async def request_call():
        calls.append(1)
        if len(calls) == 1:
            return _response(503)
        return _response(200)

    monkeypatch.setattr("app.services.external_errors.asyncio.sleep", fake_sleep)

    response = await request_with_retries(request_call, "YouTube")

    assert response.status_code == 200
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_request_with_retries_does_not_retry_rate_limit(monkeypatch):
    calls = []

    async def fake_sleep(_seconds):
        raise AssertionError("rate limits should not sleep and retry")

    async def request_call():
        calls.append(1)
        return _response(429)

    monkeypatch.setattr("app.services.external_errors.asyncio.sleep", fake_sleep)

    with pytest.raises(ExternalAPIRateLimited):
        await request_with_retries(request_call, "Spotify")

    assert len(calls) == 1
