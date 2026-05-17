# External API Error Categories

Beattrack identifies tracks through YouTube, Spotify, SoundCloud, Apple Music, and Deezer.

Those services can fail in different ways. The backend now maps them to shared categories instead of treating every problem as a generic metadata failure.

★ ʕ ᵔᴥᵔ ʔ Erklaerbaer
In simple words: if a door is locked, broken, or the address is wrong, the app should say which one happened. That helps users retry only when retrying makes sense.

## Categories

- `track_not_found`: the external service answered, but the track or metadata does not exist.
- `rate_limited`: the service is asking us to slow down.
- `temporarily_unavailable`: the service or network is temporarily failing.

## HTTP Mapping

- `track_not_found` -> `404`
- `rate_limited` -> `429`
- `temporarily_unavailable` -> `503`
- invalid platform URL -> `400`
- legacy unknown metadata failure -> `502`

## Code

Shared classes live in:

```text
apps/api/app/services/external_errors.py
```

Identify routes catch `ExternalAPIError` and expose the matching HTTP status.

The individual platform services should use `raise_for_external_response()` for HTTP responses and raise `ExternalAPITemporaryUnavailable` for network-level request errors.

## Retries

Platform metadata requests use a small bounded retry helper:

```text
request_with_retries()
```

It retries temporary network and `5xx` failures. It does not retry `404` or `429`, because those are clear answers: the track is missing, or the service asked us to slow down.
