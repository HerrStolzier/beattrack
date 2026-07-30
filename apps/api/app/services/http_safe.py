"""Redirect resolution that never leaves an allow-listed set of hosts.

Platform share links (``on.soundcloud.com``, ``link.deezer.com``) only
reveal the real track URL after following redirects. Doing that with
``follow_redirects=True`` hands the decision to the remote server: every
hop is fetched blindly, so a redirect pointing at an internal address is
requested before anything gets to inspect it. That is the SSRF CodeQL
reports as ``py/full-ssrf`` — checking the *final* URL is too late,
because the requests already went out.

The helpers here follow redirects one hop at a time and verify the target
host *before* each request instead.
"""

import logging
from collections.abc import Iterable
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

_MAX_REDIRECT_HOPS = 5


def host_is_allowed(url: str, allowed_hosts: Iterable[str]) -> bool:
    """Check that *url* is http(s) and its host is in *allowed_hosts*.

    A host matches either exactly or as a subdomain, so ``soundcloud.com``
    also covers ``on.soundcloud.com``. Matching happens on the parsed
    hostname, never on a substring of the URL — ``deezer.com.evil.test``
    does not match ``deezer.com``.

    Args:
        url: Absolute URL to check.
        allowed_hosts: Registrable hostnames, lower-case, without scheme.

    Returns:
        True if the URL may be requested.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False

    host = parsed.hostname
    if not host:
        return False

    host = host.lower()
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


async def follow_redirects_within(
    client: httpx.AsyncClient,
    url: str,
    allowed_hosts: Iterable[str],
    *,
    method: str = "HEAD",
    max_hops: int = _MAX_REDIRECT_HOPS,
) -> str | None:
    """Resolve *url* by following redirects without leaving *allowed_hosts*.

    Every hop is host-checked before it is requested, so a redirect out of
    the allow-list is refused rather than fetched.

    Args:
        client: Client to use. Its ``follow_redirects`` setting is
            overridden per request — this function does the following.
        url: Starting URL.
        allowed_hosts: Hosts the chain may stay within.
        method: HTTP method for the probe requests. Some endpoints do not
            answer HEAD with a redirect, hence the GET retry at call sites.
        max_hops: Redirect chain limit before giving up.

    Returns:
        The final URL, or None if a hop left the allow-list, the chain was
        too long, or a request failed.
    """
    current = url
    for _ in range(max_hops + 1):
        if not host_is_allowed(current, allowed_hosts):
            logger.warning("Refusing to request URL outside the allow-list: %s", current)
            return None

        try:
            resp = await client.request(method, current, follow_redirects=False)
        except Exception as exc:
            logger.debug("Redirect resolution failed for %s: %s", current, exc)
            return None

        location = resp.headers.get("location")
        if not resp.is_redirect or not location:
            return current

        # Relative Location headers are legal, so resolve against the current URL.
        current = urljoin(current, location)

    logger.warning("Redirect chain longer than %d hops, giving up: %s", max_hops, url)
    return None
