"""The website scraper, piece by piece, with no network.

Cleaning runs against markup shaped like a real marketing site: a nav, a cookie
banner, a footer, a main region, and the scripts and styles that surround them.
Fetching and crawling are exercised with the fetcher replaced, so the crawl
rules (same host, depth, budget, robots) are tested without contacting anyone.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.config import settings
from app.scrapers import ScraperError, get_source_scraper
from app.scrapers.website import WebsiteSourceScraper
from app.scrapers.website import crawler as crawler_module
from app.scrapers.website import safety
from app.scrapers.website.cleaner import clean_html, normalise_url, probable_javascript_shell
from app.scrapers.website.crawler import WebsiteCrawler
from app.scrapers.website.fetcher import Fetcher, FetchResult
from app.scrapers.website.safety import UnsafeUrl, require_public_address, require_public_host

PAGE = """
<!DOCTYPE html><html><head>
  <title>  Verdant Roast  |  Speciality coffee </title>
  <meta name="Description" content="Small-batch coffee, roasted weekly.">
  <link rel="canonical" href="https://verdantroast.test/">
  <style>.a{color:red}</style>
</head><body>
  <nav><a href="/shop">Shop</a><a href="/about">About</a></nav>
  <div class="cookie-banner">We use cookies. <a href="/privacy">Privacy</a></div>
  <main>
    <h1>Roasted weekly in small batches</h1>
    <p>Every bag is roasted to order and shipped within 24 hours.</p>
    <h2>Subscriptions</h2>
    <p>Choose a fortnightly or monthly delivery.</p>
    <a href="https://verdantroast.test/subscriptions?plan=monthly">Subscriptions</a>
    <a href="https://twitter.com/verdantroast">Twitter</a>
  </main>
  <footer><p>Company number 12345.</p><a href="/logout">Log out</a></footer>
  <script>var tracking = 1;</script>
</body></html>
"""


# ================================================================== cleaning


def test_a_page_is_reduced_to_what_is_worth_reading() -> None:
    page = clean_html("https://verdantroast.test/", PAGE)

    assert page.title == "Verdant Roast | Speciality coffee"
    assert page.meta_description == "Small-batch coffee, roasted weekly."
    assert page.canonical_url == "https://verdantroast.test/"
    assert [heading["text"] for heading in page.headings] == [
        "Roasted weekly in small batches",
        "Subscriptions",
    ]
    assert "roasted to order" in page.cleaned_text
    # Chrome that repeats on every page would otherwise dominate the text.
    assert "We use cookies" not in page.cleaned_text
    assert "Company number" not in page.cleaned_text
    assert "Shop" not in page.cleaned_text
    assert "var tracking" not in page.cleaned_text
    assert page.word_count > 5
    assert len(page.content_hash) == 64


def test_links_are_collected_before_the_page_is_stripped() -> None:
    """Navigation is not worth reading, but it is where the rest of the site is."""
    page = clean_html("https://verdantroast.test/", PAGE)
    urls = [link["url"] for link in page.links]

    assert "https://verdantroast.test/shop" in urls
    assert "https://verdantroast.test/about" in urls
    assert "https://twitter.com/verdantroast" in urls
    assert len(urls) == len(set(urls))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://Example.COM/Path/", "https://example.com/Path"),
        ("https://example.com:443/a//b", "https://example.com/a/b"),
        ("http://example.com:80/", "http://example.com/"),
        ("https://example.com/a?b=1#top", "https://example.com/a?b=1"),
        # The root keeps its slash; only deeper paths lose a trailing one.
        ("https://example.com/", "https://example.com/"),
    ],
)
def test_one_spelling_per_page(raw: str, expected: str) -> None:
    assert normalise_url(raw) == expected


def test_an_empty_frame_is_sent_to_the_browser_but_a_short_page_is_not() -> None:
    shell = '<html><body><div id="root"></div><script src="/app.js"></script></body></html>'
    assert probable_javascript_shell(shell, "", 500)
    # Short but real: no marker, few scripts. Rendering it would buy nothing.
    assert not probable_javascript_shell("<html><body><p>Hi</p></body></html>", "Hi", 500)
    # Long enough to stand on its own, marker or not.
    assert not probable_javascript_shell(shell, "x" * 500, 500)


def test_malformed_markup_does_not_raise() -> None:
    for html in ("", "<html><body><p>unclosed", "not html at all", "<html></html>"):
        page = clean_html("https://example.test/", html)
        assert page.page_url == "https://example.test/"


# ================================================================== crawling


class FakeFetcher:
    """Serves canned pages by URL and records what was asked for."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    def fetch(self, url: str, renderer: str = "auto") -> FetchResult:
        self.requested.append(url)
        html = self.pages.get(url)
        if html is None:
            return FetchResult(url, url, 404, "", "http", "HTTP 404")
        return FetchResult(url, url, 200, html, "http")


def _page(body: str) -> str:
    return f"<html><head><title>Page</title></head><body><main>{body}</main></body></html>"


SITE = {
    "https://verdantroast.test/": _page(
        "<p>Home page with enough words to be worth storing.</p>"
        "<a href='/shop'>Shop</a><a href='/about'>About</a>"
        "<a href='/brochure.pdf'>Brochure</a><a href='/logout'>Log out</a>"
        "<a href='https://northbrew.test/'>A competitor</a>"
    ),
    "https://verdantroast.test/shop": _page("<p>Shop page, also worth storing here.</p>"),
    "https://verdantroast.test/about": _page("<p>About page, also worth storing here.</p>"),
}


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> FakeFetcher:
    """No robots.txt lookup, no network, no delay."""
    fetcher = FakeFetcher(SITE)
    monkeypatch.setattr(crawler_module, "Fetcher", lambda: fetcher)
    monkeypatch.setattr(WebsiteCrawler, "_robots", staticmethod(lambda root: None))
    return fetcher


def test_a_crawl_follows_the_site_and_stops_at_its_own_edges(offline: FakeFetcher) -> None:
    result = WebsiteCrawler().crawl("https://verdantroast.test/")

    assert [page.page.page_url for page in result.pages] == [
        "https://verdantroast.test/",
        "https://verdantroast.test/shop",
        "https://verdantroast.test/about",
    ]
    assert result.pages[0].is_root and result.pages[0].depth == 0
    assert result.pages[1].depth == 1
    # Another host, a PDF and a destructive link are never fetched.
    assert not any("northbrew" in url or ".pdf" in url or "logout" in url for url in offline.requested)


def test_the_page_budget_is_honoured(offline: FakeFetcher) -> None:
    result = WebsiteCrawler(max_pages=2).crawl("https://verdantroast.test/")
    assert len(result.pages) == 2


def test_depth_zero_reads_only_the_submitted_page(offline: FakeFetcher) -> None:
    result = WebsiteCrawler(max_depth=0).crawl("https://verdantroast.test/")
    assert len(result.pages) == 1


def test_an_unreadable_page_is_recorded_and_the_crawl_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = dict(SITE)
    pages["https://verdantroast.test/shop"] = _page("")          # no readable text
    fetcher = FakeFetcher(pages)
    monkeypatch.setattr(crawler_module, "Fetcher", lambda: fetcher)
    monkeypatch.setattr(WebsiteCrawler, "_robots", staticmethod(lambda root: None))

    result = WebsiteCrawler().crawl("https://verdantroast.test/")

    assert [page.page.page_url for page in result.pages] == [
        "https://verdantroast.test/",
        "https://verdantroast.test/about",
    ]
    assert any("No readable text" in failure["error"] for failure in result.failures)


def test_the_same_page_under_two_urls_is_stored_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real sites serve one page at several URLs (/ and /index.html). Storing
    both spends the page budget twice and doubles the text in the vector store."""
    body = "<p>Home page with enough words to be worth storing.</p><a href='/index.html'>Home</a>"
    pages = {
        "https://verdantroast.test/": _page(body),
        "https://verdantroast.test/index.html": _page(body),
    }
    fetcher = FakeFetcher(pages)
    monkeypatch.setattr(crawler_module, "Fetcher", lambda: fetcher)
    monkeypatch.setattr(WebsiteCrawler, "_robots", staticmethod(lambda root: None))

    result = WebsiteCrawler().crawl("https://verdantroast.test/")

    assert [page.page.page_url for page in result.pages] == ["https://verdantroast.test/"]
    assert result.duplicates == 1
    # A duplicate is a skip, not something to warn the user about.
    assert result.failures == []


def test_robots_txt_is_obeyed(monkeypatch: pytest.MonkeyPatch) -> None:
    class RobotsBlockingShop:
        @staticmethod
        def can_fetch(agent: str, url: str) -> bool:
            return not url.endswith("/shop")

    fetcher = FakeFetcher(SITE)
    monkeypatch.setattr(crawler_module, "Fetcher", lambda: fetcher)
    monkeypatch.setattr(WebsiteCrawler, "_robots", staticmethod(lambda root: RobotsBlockingShop()))

    result = WebsiteCrawler().crawl("https://verdantroast.test/")

    assert "https://verdantroast.test/shop" not in [page.page.page_url for page in result.pages]
    assert any("robots.txt" in failure["error"] for failure in result.failures)
    assert "https://verdantroast.test/shop" not in fetcher.requested


# =================================================================== adapter


def test_the_adapter_presents_the_source_contract(offline: FakeFetcher) -> None:
    record = get_source_scraper("website").scrape("https://verdantroast.test/", "own")

    assert (record.kind, record.role) == ("website", "own")
    assert record.title == "Page"
    assert record.method == "http"
    assert len(record.documents) == 3

    root = record.documents[0]
    assert root.url == "https://verdantroast.test/"
    assert set(root.text_fields) == {"page_text", "headings", "meta"}
    assert root.metadata["is_root"] is True
    assert root.metadata["depth"] == 0
    assert root.metadata["renderer"] == "http"
    assert root.metadata["word_count"] > 0
    assert root.metadata["link_count"] >= 1
    assert "cleaned_text" in root.metadata


def test_a_site_that_cannot_be_read_is_reported_plainly(monkeypatch: pytest.MonkeyPatch) -> None:
    fetcher = FakeFetcher({})
    monkeypatch.setattr(crawler_module, "Fetcher", lambda: fetcher)
    monkeypatch.setattr(WebsiteCrawler, "_robots", staticmethod(lambda root: None))

    with pytest.raises(ScraperError, match="Nothing could be read"):
        get_source_scraper("website").scrape("https://verdantroast.test/", "own")


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("", "empty"),
        ("ftp://verdantroast.test/", "http"),
        ("verdantroast.test", "http"),
        ("https://localhost/", "not a website address"),
    ],
)
def test_a_link_that_is_not_a_web_page_is_refused(url: str, message: str) -> None:
    with pytest.raises(ScraperError, match=message):
        WebsiteSourceScraper().validate_url(url)


def test_the_same_site_written_two_ways_is_one_key() -> None:
    scraper = WebsiteSourceScraper()
    assert scraper.canonical_url("https://Verdant.test/Home/") == scraper.canonical_url(
        "https://verdant.test/Home"
    )


def test_defaults_keep_a_comparison_to_a_few_minutes() -> None:
    # Two sites are crawled per comparison, each page paced by a delay.
    assert settings.website_max_pages <= 20
    assert settings.website_max_depth <= 3


# ==================================================================== safety
#
# This scraper fetches URLs a user typed, from a server that can reach things
# the user cannot. See docs/security.md, gap 3.


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/",                     # this very API
        "http://169.254.169.254/latest/meta-data/",   # cloud metadata
        "http://192.168.1.10/",                       # somebody's router
        "http://10.0.0.5/admin",                      # internal network
        "http://[::1]/",                              # loopback, v6
        "http://localhost/",                          # named, never resolved
    ],
)
def test_internal_addresses_are_refused(url: str) -> None:
    with pytest.raises(UnsafeUrl):
        require_public_host(url)


def test_a_public_address_is_allowed_and_needs_no_dns() -> None:
    require_public_host("https://93.184.216.34/")
    require_public_address("https://93.184.216.34/")


def test_a_hostname_that_resolves_internally_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """An ordinary looking name is what makes this worth checking at all."""
    monkeypatch.setattr(
        safety.socket, "getaddrinfo", lambda host, port: [(2, 1, 6, "", ("127.0.0.1", 0))]
    )
    with pytest.raises(UnsafeUrl, match="internal address"):
        require_public_address("https://intranet.example.com/")


def test_every_resolved_address_is_checked_not_just_the_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        safety.socket,
        "getaddrinfo",
        lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 0)), (2, 1, 6, "", ("10.0.0.5", 0))],
    )
    with pytest.raises(UnsafeUrl, match="internal address"):
        require_public_address("https://mixed.example.com/")


def test_an_internal_link_is_refused_on_the_form_too() -> None:
    with pytest.raises(ScraperError, match="private or internal"):
        WebsiteSourceScraper().validate_url("https://192.168.0.1/")


def test_an_internal_url_fails_its_fetch_rather_than_crashing_the_crawl() -> None:
    """A blocked URL has to look like any other unreadable page to the crawler."""
    result = Fetcher().fetch_http("http://127.0.0.1:8000/")

    assert result.html == ""
    assert result.error and "private or internal" in result.error
