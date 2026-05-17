"""Shared error categories for external music metadata APIs."""

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
