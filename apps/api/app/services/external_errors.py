"""Shared error categories for external music metadata APIs."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx


@dataclass
class ExternalAPIError(Exception):
    """Base error for external API failures with a stable category."""

    code: str
    public_message: str
    http_status: int = 503


class ExternalAPINotFound(ExternalAPIError):
    def __init__(self, platform: str):
        super().__init__(
            code="track_not_found",
            public_message=f"{platform} track not found",
            http_status=404,
        )


class ExternalAPIRateLimited(ExternalAPIError):
    def __init__(self, platform: str):
        super().__init__(
            code="rate_limited",
            public_message=f"{platform} rate limit reached",
            http_status=429,
        )


class ExternalAPITemporaryUnavailable(ExternalAPIError):
    def __init__(self, platform: str):
        super().__init__(
            code="temporarily_unavailable",
            public_message=f"{platform} temporarily unavailable",
            http_status=503,
        )


def raise_for_external_response(response: httpx.Response, platform: str) -> None:
    """Map HTTP response codes into Beattrack's shared external API categories."""
    if response.status_code == 404:
        raise ExternalAPINotFound(platform)
    if response.status_code == 429:
        raise ExternalAPIRateLimited(platform)
    if response.status_code >= 500:
        raise ExternalAPITemporaryUnavailable(platform)
    response.raise_for_status()


async def request_with_retries(
    request_call: Callable[[], Awaitable[httpx.Response]],
    platform: str,
    *,
    attempts: int = 2,
    backoff_sec: float = 0.25,
) -> httpx.Response:
    """Run a small retry loop for temporary external API failures."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = await request_call()
            raise_for_external_response(response, platform)
            return response
        except ExternalAPITemporaryUnavailable as exc:
            last_error = exc
        except httpx.RequestError as exc:
            last_error = exc

        if attempt < attempts - 1:
            await asyncio.sleep(backoff_sec * (2 ** attempt))

    if isinstance(last_error, ExternalAPITemporaryUnavailable):
        raise last_error
    raise ExternalAPITemporaryUnavailable(platform) from last_error
