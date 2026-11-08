"""Relaying a post's media, and refusing to relay anything else.

Instagram's CDN blocks cross-origin rendering, so the API fetches the bytes
instead. That makes this endpoint a URL the internet can hand to the server,
which is the shape of an open proxy and of SSRF, so most of what is covered
here is what it *refuses*.
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient
from requests.structures import CaseInsensitiveDict

from app.scrapers import ScraperError
from app.scrapers.instagram import media
from app.scrapers.instagram import selectors as S

IMAGE_URL = "https://scontent.cdninstagram.com/v/t51.29350-15/photo.jpg?stp=dst-jpg"
FNA_URL = "https://instagram.fkhi8-1.fna.fbcdn.net/v/t51.82787-15/photo.webp"


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        chunks: tuple[bytes, ...] = (b"\xff\xd8jpeg-bytes",),
    ) -> None:
        self.status_code = status_code
        # Real responses carry case-insensitive headers, and the code under
        # test reads them in whatever case reads best at the call site.
        self.headers = CaseInsensitiveDict(
            headers if headers is not None else {"content-type": "image/jpeg"}
        )
        self._chunks = chunks
        self.closed = False

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        yield from self._chunks

    def close(self) -> None:
        self.closed = True


class FakeSession:
    """Hands back the queued responses, recording what was asked for."""

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state
        self.headers: dict[str, str] = {}

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self._state["asked"].append(url)
        self._state["sent"].append(kwargs.get("headers") or {})
        return self._state["responses"].pop(0)


@pytest.fixture
def cdn(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stands in for Instagram's CDN. No network, and no DNS either."""
    state: dict[str, Any] = {"responses": [FakeResponse()], "asked": [], "sent": []}

    monkeypatch.setattr(media.requests, "Session", lambda: FakeSession(state))
    # The SSRF guard resolves hosts for real; the rule it enforces has its own
    # tests, and a unit test must not depend on DNS.
    monkeypatch.setattr(media, "require_public_address", lambda url: None)
    return state


# ------------------------------------------------------------ what it allows


def test_an_instagram_image_is_handed_on(client: TestClient, cdn: dict) -> None:
    response = client.get("/api/v1/scrapers/media", params={"url": IMAGE_URL})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.content == b"\xff\xd8jpeg-bytes"
    assert "max-age" in response.headers["cache-control"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert cdn["asked"] == [IMAGE_URL]


def test_both_instagram_cdn_shapes_are_recognised() -> None:
    assert media.is_media_url(IMAGE_URL)
    assert media.is_media_url(FNA_URL)
    assert media.is_media_url("https://scontent-lhr8-1.cdninstagram.com/v/photo.jpg")


def test_a_video_is_relayed_too(client: TestClient, cdn: dict) -> None:
    cdn["responses"] = [FakeResponse(headers={"content-type": "video/mp4"}, chunks=(b"mp4",))]
    response = client.get("/api/v1/scrapers/media", params={"url": FNA_URL})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")


def test_a_players_range_request_is_passed_through_both_ways(
    client: TestClient, cdn: dict
) -> None:
    """Without this a video plays from the start and cannot be scrubbed."""
    cdn["responses"] = [
        FakeResponse(
            206,
            {
                "content-type": "video/mp4",
                "content-range": "bytes 0-99/52428",
                "content-length": "100",
                "accept-ranges": "bytes",
            },
            chunks=(b"m" * 100,),
        )
    ]

    response = client.get(
        "/api/v1/scrapers/media", params={"url": FNA_URL}, headers={"Range": "bytes=0-99"}
    )

    assert response.status_code == 206
    assert cdn["sent"][0]["Range"] == "bytes=0-99"
    assert response.headers["content-range"] == "bytes 0-99/52428"
    assert response.headers["accept-ranges"] == "bytes"


def test_a_request_without_a_range_asks_for_none(client: TestClient, cdn: dict) -> None:
    client.get("/api/v1/scrapers/media", params={"url": IMAGE_URL})
    assert cdn["sent"] == [{}]


def test_one_redirect_is_followed_when_it_stays_inside_the_allowlist(
    client: TestClient, cdn: dict
) -> None:
    cdn["responses"] = [
        FakeResponse(302, {"location": FNA_URL}),
        FakeResponse(),
    ]
    response = client.get("/api/v1/scrapers/media", params={"url": IMAGE_URL})

    assert response.status_code == 200
    assert cdn["asked"] == [IMAGE_URL, FNA_URL]


# ------------------------------------------------------------ what it refuses


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/photo.jpg",
        # The suffix check is on labels, not on "contains".
        "https://cdninstagram.com.evil.example/photo.jpg",
        "https://notcdninstagram.com/photo.jpg",
        "http://127.0.0.1:8000/api/v1/projects",
        "file:///etc/passwd",
        "https://169.254.169.254/latest/meta-data/",
    ],
)
def test_anything_but_instagram_media_is_refused(
    client: TestClient, cdn: dict, url: str
) -> None:
    response = client.get("/api/v1/scrapers/media", params={"url": url})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "media_not_relayed"
    assert cdn["asked"] == [], "a refused URL must never be fetched"


def test_a_redirect_out_of_the_allowlist_is_not_followed(
    client: TestClient, cdn: dict
) -> None:
    """The reason redirects are followed by hand: an automatic follow would
    have made the request before anything could check it."""
    cdn["responses"] = [FakeResponse(302, {"location": "https://evil.example/x.jpg"})]
    response = client.get("/api/v1/scrapers/media", params={"url": IMAGE_URL})

    assert response.status_code == 400
    assert cdn["asked"] == [IMAGE_URL]


def test_an_internal_address_is_refused_even_on_an_allowed_host(
    client: TestClient, cdn: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host inside the allowlist that resolves somewhere internal is exactly
    what the DNS-level guard is for."""
    from app.scrapers.website.safety import UnsafeUrl

    def internal(url: str) -> None:
        raise UnsafeUrl("'scontent.cdninstagram.com' resolves to the internal address 127.0.0.1.")

    monkeypatch.setattr(media, "require_public_address", internal)
    response = client.get("/api/v1/scrapers/media", params={"url": IMAGE_URL})

    assert response.status_code == 400
    assert "internal address" in response.json()["error"]["message"]
    assert cdn["asked"] == []


def test_a_page_of_html_is_not_media(client: TestClient, cdn: dict) -> None:
    cdn["responses"] = [FakeResponse(headers={"content-type": "text/html; charset=utf-8"})]
    response = client.get("/api/v1/scrapers/media", params={"url": IMAGE_URL})

    assert response.status_code == 400
    assert "not an image or a video" in response.json()["error"]["message"]


def test_an_expired_link_says_so(client: TestClient, cdn: dict) -> None:
    cdn["responses"] = [FakeResponse(410, {"content-type": "text/plain"})]
    response = client.get("/api/v1/scrapers/media", params={"url": IMAGE_URL})

    assert response.status_code == 400
    assert "scrape again" in response.json()["error"]["message"]


def test_media_larger_than_the_cap_is_refused(client: TestClient, cdn: dict) -> None:
    cdn["responses"] = [
        FakeResponse(headers={"content-type": "video/mp4", "content-length": str(S.MEDIA_MAX_BYTES + 1)})
    ]
    response = client.get("/api/v1/scrapers/media", params={"url": IMAGE_URL})

    assert response.status_code == 400
    assert "larger than" in response.json()["error"]["message"]


def test_a_body_that_outgrows_the_cap_mid_flight_is_cut_off(
    cdn: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing promised a length, so the only defence is counting as it goes."""
    monkeypatch.setattr(S, "MEDIA_MAX_BYTES", 8)
    cdn["responses"] = [FakeResponse(chunks=(b"1234", b"5678", b"9012"))]

    _status, _type, _headers, chunks = media.open_stream(IMAGE_URL)

    assert b"".join(chunks) == b"12345678"


def test_a_cdn_that_cannot_be_reached_is_reported_plainly(
    cdn: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Failing(FakeSession):
        def get(self, url: str, **kwargs: Any) -> FakeResponse:
            raise media.requests.ConnectionError("connection reset")

    monkeypatch.setattr(media.requests, "Session", lambda: Failing(cdn))
    with pytest.raises(ScraperError, match="could not be reached"):
        media.open_stream(IMAGE_URL)
