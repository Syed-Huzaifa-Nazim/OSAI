"""Refusing to fetch anything that is not a public web address.

This scraper fetches URLs a user typed, which is the textbook setup for
server-side request forgery: ``http://169.254.169.254/`` reaches cloud
metadata, ``http://127.0.0.1:8000/`` reaches this very API, and an ordinary
looking hostname can resolve to either. Listed as gap 3 in docs/security.md
while nothing scraped for real; now that the website scraper does, it is closed
here.

Two checks, deliberately split:

* :func:`require_public_host` reads the URL only. It runs at intake, where
  validation has to be instant and must not depend on DNS being reachable.
* :func:`require_public_address` resolves the host and inspects every address
  it answers with. It runs immediately before each request, and again on the
  URL a redirect lands on, because a redirect is a fetch the user never typed.

What remains open is DNS rebinding: a host that resolves to a public address
when checked and a private one when connected. Closing that needs the
connection pinned to the address that was checked.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

ALLOWED_SCHEMES = ("http", "https")

#: Hostnames that mean "this machine" without ever reaching a resolver.
LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}


class UnsafeUrl(ValueError):
    """The URL points somewhere a scraper must not go. Message is user-facing."""


def _is_public(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Public routable address. Everything else is somebody's internal network."""
    return address.is_global and not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    )


def _as_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """The host as an IP literal, or None when it is a name."""
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return None


def require_public_host(url: str) -> None:
    """Shape check: the scheme, and an address literal if the host is one.

    No DNS, so it is safe to run on a form submission.
    """
    parts = urlsplit((url or "").strip())
    if parts.scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrl(f"Invalid URL '{(url or '')[:80]}': must start with http:// or https://")

    host = (parts.hostname or "").lower()
    if not host:
        raise UnsafeUrl(f"Invalid URL '{(url or '')[:80]}': no host found.")
    if host in LOCAL_HOSTNAMES:
        raise UnsafeUrl(f"'{host}' is this machine, not a public website.")

    address = _as_ip(host)
    if address is not None and not _is_public(address):
        raise UnsafeUrl(
            f"'{host}' is a private or internal address. Only public websites can be scraped."
        )


def require_public_address(url: str) -> None:
    """Resolve the host and refuse it if any address it answers with is internal.

    Every address is checked, not just the first: a host that answers with one
    public and one private address is exactly the trick this is here to stop.
    """
    require_public_host(url)
    host = (urlsplit(url).hostname or "").lower()

    literal = _as_ip(host)
    if literal is not None:
        return  # already checked, and there is nothing to resolve

    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as exc:
        raise UnsafeUrl(f"'{host}' could not be resolved ({exc.__class__.__name__}).") from exc

    addresses = []
    for info in infos:
        raw = str(info[4][0]).split("%")[0]
        address = _as_ip(raw)
        if address is not None:
            addresses.append(address)

    if not addresses:
        raise UnsafeUrl(f"'{host}' did not resolve to any usable address.")
    for address in addresses:
        if not _is_public(address):
            raise UnsafeUrl(
                f"'{host}' resolves to the internal address {address}. Only public websites "
                "can be scraped."
            )
