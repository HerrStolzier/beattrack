"""Tests for allow-listed redirect resolution (CodeQL py/full-ssrf)."""
import httpx

from app.services.http_safe import follow_redirects_within, host_is_allowed

ALLOWED = frozenset({"soundcloud.com"})


# ---------------------------------------------------------------------------
# host_is_allowed
# ---------------------------------------------------------------------------

def test_exact_host_matches():
    assert host_is_allowed("https://soundcloud.com/artist/track", ALLOWED)


def test_subdomain_matches():
    assert host_is_allowed("https://on.soundcloud.com/abc", ALLOWED)


def test_uppercase_host_matches():
    assert host_is_allowed("https://SoundCloud.COM/artist/track", ALLOWED)


def test_suffix_spoof_is_rejected():
    """soundcloud.com.evil.test must not pass as soundcloud.com."""
    assert not host_is_allowed("https://soundcloud.com.evil.test/x", ALLOWED)


def test_userinfo_spoof_is_rejected():
    """The real host is evil.test — soundcloud.com is only userinfo here."""
    assert not host_is_allowed("https://soundcloud.com@evil.test/x", ALLOWED)


def test_prefix_spoof_is_rejected():
    assert not host_is_allowed("https://notsoundcloud.com/x", ALLOWED)


def test_non_http_scheme_is_rejected():
    assert not host_is_allowed("file:///etc/passwd", ALLOWED)
    assert not host_is_allowed("gopher://soundcloud.com/x", ALLOWED)


def test_missing_host_is_rejected():
    assert not host_is_allowed("https:///no-host", ALLOWED)


# ---------------------------------------------------------------------------
# follow_redirects_within
# ---------------------------------------------------------------------------

def _recording_client(routes: dict[str, httpx.Response]) -> tuple[httpx.AsyncClient, list[str]]:
    """Build a client backed by a fixed routing table, recording every request."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return routes.get(str(request.url), httpx.Response(200))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5)
    return client, seen


async def test_returns_url_when_no_redirect():
    client, seen = _recording_client({})
    async with client:
        result = await follow_redirects_within(client, "https://soundcloud.com/a/b", ALLOWED)
    assert result == "https://soundcloud.com/a/b"
    assert seen == ["https://soundcloud.com/a/b"]


async def test_follows_redirect_inside_allow_list():
    routes = {
        "https://on.soundcloud.com/xyz": httpx.Response(
            302, headers={"location": "https://soundcloud.com/artist/track"}
        ),
    }
    client, seen = _recording_client(routes)
    async with client:
        result = await follow_redirects_within(client, "https://on.soundcloud.com/xyz", ALLOWED)
    assert result == "https://soundcloud.com/artist/track"
    assert len(seen) == 2


async def test_refuses_redirect_leaving_allow_list():
    """The core property: the off-list target is never requested."""
    routes = {
        "https://on.soundcloud.com/xyz": httpx.Response(
            302, headers={"location": "http://169.254.169.254/latest/meta-data/"}
        ),
    }
    client, seen = _recording_client(routes)
    async with client:
        result = await follow_redirects_within(client, "https://on.soundcloud.com/xyz", ALLOWED)
    assert result is None
    assert seen == ["https://on.soundcloud.com/xyz"]
    assert not any("169.254.169.254" in url for url in seen)


async def test_start_url_outside_allow_list_is_never_requested():
    client, seen = _recording_client({})
    async with client:
        result = await follow_redirects_within(client, "http://127.0.0.1:8000/admin", ALLOWED)
    assert result is None
    assert seen == []


async def test_relative_location_is_resolved_against_current_url():
    routes = {
        "https://on.soundcloud.com/xyz": httpx.Response(302, headers={"location": "/artist/track"}),
    }
    client, seen = _recording_client(routes)
    async with client:
        result = await follow_redirects_within(client, "https://on.soundcloud.com/xyz", ALLOWED)
    assert result == "https://on.soundcloud.com/artist/track"


async def test_redirect_loop_gives_up():
    routes = {
        "https://soundcloud.com/a": httpx.Response(302, headers={"location": "https://soundcloud.com/b"}),
        "https://soundcloud.com/b": httpx.Response(302, headers={"location": "https://soundcloud.com/a"}),
    }
    client, seen = _recording_client(routes)
    async with client:
        result = await follow_redirects_within(client, "https://soundcloud.com/a", ALLOWED, max_hops=3)
    assert result is None
    assert len(seen) == 4  # max_hops + 1 probes, then give up


async def test_request_failure_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5) as client:
        result = await follow_redirects_within(client, "https://soundcloud.com/a", ALLOWED)
    assert result is None
