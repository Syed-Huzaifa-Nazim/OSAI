"""Serving a post's media, because a browser refuses to.

Instagram's CDN answers every image and video with
``Cross-Origin-Resource-Policy: same-origin``. That is a browser rule, not an
access rule: the bytes are public and unauthenticated, but no page on another
origin may render them. Storing the URL and pointing an ``<img>`` at it -- what
works for Daraz and Alibaba, whose CDNs allow cross-origin use -- therefore
shows nothing at all here.

So the bytes are fetched server-side and handed on. CORP does not apply,
because the fetch is not a browser's.

What keeps this from being an open proxy, in order:

  * the host must end in one of :data:`selectors.MEDIA_HOST_SUFFIXES`;
  * every hop of a redirect is checked again, host and address both, through
    the same SSRF guard the website crawler uses;
  * only image and video content types are passed through;
  * the response is capped, and streamed rather than buffered.

Nothing is stored. An expired link fails like any other broken image and comes
back on the next scrape.
"""

from __future__ import annotations

import logging
from typing import Iterator
from urllib.parse import urlsplit

import requests

from app.scrapers.base import ScraperError
from app.scrapers.website.safety import UnsafeUrl, require_public_address
from . import selectors as S

logger = logging.getLogger("optistratix.scrapers.instagram.media")


def is_media_url(url: str) -> bool:
    """True for a URL this proxy is allowed to fetch at all."""
    parts = urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https"):
        return False
    host = (parts.hostname or "").lower()
    return any(
        host == suffix or host.endswith("." + suffix) for suffix in S.MEDIA_HOST_SUFFIXES
    )


def open_stream(
    url: str, *, range_header: str | None = None
) -> tuple[int, str, dict[str, str], Iterator[bytes]]:
    """The media at ``url`` as ``(status, content_type, headers, chunks)``.

    ``range_header`` is the caller's own ``Range``, passed straight through.
    Instagram's CDN honours it, and a video that cannot be ranged cannot be
    scrubbed: the player would be stuck playing from the start.

    Raises :class:`ScraperError` with a user-facing message for anything that
    is not an allowed, public, reasonably sized image or video.
    """
    if not is_media_url(url):
        raise ScraperError("That link is not an Instagram media address.")

    session = requests.Session()
    session.headers.update({"User-Agent": S.MEDIA_USER_AGENT, "Accept": "image/*,video/*;q=0.9"})
    hop_headers = {"Range": range_header} if range_header else None

    current = url
    response: requests.Response | None = None
    try:
        # Redirects are followed by hand so every hop is checked before it is
        # fetched. Following them automatically would mean the first unchecked
        # request had already gone out.
        for _ in range(S.MEDIA_MAX_REDIRECTS + 1):
            if not is_media_url(current):
                raise ScraperError("That link redirected somewhere this server will not follow.")
            try:
                require_public_address(current)
            except UnsafeUrl as exc:
                raise ScraperError(str(exc)) from exc

            response = session.get(
                current,
                stream=True,
                timeout=S.MEDIA_TIMEOUT_SECONDS,
                allow_redirects=False,
                headers=hop_headers,
            )
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location") or ""
                response.close()
                if not location:
                    raise ScraperError("Instagram's CDN redirected to nowhere.")
                current = requests.compat.urljoin(current, location)  # type: ignore[attr-defined]
                continue
            break
        else:
            raise ScraperError("Instagram's CDN redirected too many times.")

        assert response is not None
        # 206 is the answer to a Range the player asked for, and is passed on
        # as a 206: turning it into a 200 would claim a partial body was whole.
        if response.status_code not in (200, 206):
            response.close()
            raise ScraperError(
                f"Instagram's CDN answered {response.status_code} for that media. "
                "The link may have expired; scrape again to refresh it."
            )

        content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
        if not content_type.startswith(("image/", "video/")):
            response.close()
            raise ScraperError("That link is not an image or a video.")

        length = _length(response.headers.get("content-length"))
        if length is not None and length > S.MEDIA_MAX_BYTES:
            response.close()
            raise ScraperError("That media is larger than this server will relay.")

        # What the player needs to seek, and nothing else: the CDN's own
        # caching, cookie and tracking headers are not passed on.
        headers = {}
        for name in ("Content-Length", "Content-Range", "Accept-Ranges"):
            value = response.headers.get(name)
            if value:
                headers[name] = value

        return response.status_code, content_type, headers, _chunks(response)
    except requests.RequestException as exc:
        if response is not None:
            response.close()
        raise ScraperError(f"Instagram's CDN could not be reached ({exc.__class__.__name__}).") from exc


def _length(raw: str | None) -> int | None:
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def _chunks(response: requests.Response) -> Iterator[bytes]:
    """Streams the body, stopping if it outgrows the cap mid-flight.

    A truncated image is a broken image, which the UI already handles. An
    unbounded one is a memory problem, which it does not.
    """
    sent = 0
    try:
        for chunk in response.iter_content(chunk_size=S.MEDIA_CHUNK_BYTES):
            if not chunk:
                continue
            sent += len(chunk)
            if sent > S.MEDIA_MAX_BYTES:
                logger.warning("Media exceeded %d bytes; truncating", S.MEDIA_MAX_BYTES)
                return
            yield chunk
    finally:
        response.close()


__all__ = ["is_media_url", "open_stream"]
