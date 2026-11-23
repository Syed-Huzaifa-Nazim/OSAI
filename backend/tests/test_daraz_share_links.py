"""Daraz share links (s.daraz.pk/s.XXXX) lead to a bridge page; the scraper follows them to the product page."""
from __future__ import annotations

import pytest

from app.scrapers.daraz import scraper

PRODUCT = "https://www.daraz.pk/products/black-butterfly-set-i1976548279-s14088428806.html"


class FakeResponse:
    def __init__(self, url: str, text: str):
        self.url, self.text = url, text


def test_a_share_link_is_followed_to_the_product_link(monkeypatch):
    bridge = f'<html><script>var u = "{PRODUCT}?spm=a2a0e&amp;dsource=share";</script></html>'
    monkeypatch.setattr(scraper.requests, "get", lambda url, **kw: FakeResponse(url, bridge))
    assert scraper.canonical_url(scraper.resolve_share_link("https://s.daraz.pk/s.2hCjS")) == PRODUCT


def test_a_json_escaped_product_link_is_found(monkeypatch):
    bridge = '{"url":"' + PRODUCT.replace("/", "\\/") + '"}'
    monkeypatch.setattr(scraper.requests, "get", lambda url, **kw: FakeResponse(url, bridge))
    assert scraper.resolve_share_link("https://s.daraz.pk/s.2hCQb") == PRODUCT


def test_a_product_link_is_left_alone(monkeypatch):
    def no_network(*a, **k):
        raise AssertionError("a product link needs no extra request")
    monkeypatch.setattr(scraper.requests, "get", no_network)
    assert scraper.resolve_share_link(PRODUCT) == PRODUCT


def test_a_share_link_without_a_product_says_what_to_paste(monkeypatch):
    monkeypatch.setattr(scraper.requests, "get", lambda url, **kw: FakeResponse(url, "<html>expired</html>"))
    with pytest.raises(scraper.ScrapeError, match="daraz.pk/products"):
        scraper.resolve_share_link("https://s.daraz.pk/s.dead")
