"""Fetching one page: a normal HTTP request first, a browser only if needed.

The standalone scraper's two-step strategy, unchanged. Plain requests handle
almost everything; when a page comes back as a JavaScript shell, Chromium opens
it, scrolls to trigger lazy loading, and the rendered DOM is used instead.

Timeouts and the browser budget come from the project's own settings, so this
scraper is paced by the same configuration as the others.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings
from . import selectors as S
from .cleaner import clean_html, probable_javascript_shell
from .safety import UnsafeUrl, require_public_address

log = logging.getLogger(__name__)

#: One headless browser at a time across the whole process, as with the other
#: scrapers: two Chromium instances on a laptop starve each other.
_playwright_lock = threading.Lock()

_BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int | None
    html: str
    renderer: str                    # "http" | "playwright"
    error: str | None = None


class Fetcher:
    """Fetches pages for one crawl. Holds a session, so connections are reused."""

    def __init__(self) -> None:
        self.session = requests.Session()
        retry = Retry(
            total=S.MAX_RETRIES,
            connect=S.MAX_RETRIES,
            read=S.MAX_RETRIES,
            status=S.MAX_RETRIES,
            backoff_factor=S.RETRY_BACKOFF_FACTOR,
            status_forcelist=S.RETRY_STATUS_CODES,
            allowed_methods=("GET", "HEAD"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(S.REQUEST_HEADERS)

    def fetch(self, url: str, renderer: str = "auto") -> FetchResult:
        """``auto`` tries HTTP and falls back to the browser for a JS shell."""
        if renderer == "playwright":
            return self.fetch_playwright(url)

        result = self.fetch_http(url)
        if renderer == "http" or result.error:
            return result

        page = clean_html(result.final_url, result.html)
        if probable_javascript_shell(
            result.html, page.cleaned_text, settings.website_min_http_text_length
        ):
            if not settings.scraper_enable_playwright:
                return result
            rendered = self.fetch_playwright(url)
            if not rendered.error:
                return rendered
        return result

    def fetch_http(self, url: str) -> FetchResult:
        try:
            # Checked here rather than in the crawler, so every real request
            # goes through it however it was reached.
            require_public_address(url)
        except UnsafeUrl as exc:
            return FetchResult(url, url, None, "", "http", str(exc))

        try:
            time.sleep(settings.website_request_delay_seconds)
            response = self.session.get(
                url, timeout=settings.scraper_timeout, allow_redirects=True
            )
            if response.url and response.url != url:
                # A redirect is a fetch the user never typed.
                require_public_address(response.url)
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            if not any(kind in content_type for kind in S.HTML_CONTENT_TYPES):
                return FetchResult(
                    url, response.url, response.status_code, "", "http",
                    f"Not a web page (content type: {content_type or 'unknown'})",
                )
            return FetchResult(url, response.url, response.status_code, response.text, "http")
        except UnsafeUrl as exc:
            return FetchResult(url, url, None, "", "http", str(exc))
        except requests.RequestException as exc:
            return FetchResult(url, url, None, "", "http", str(exc))

    def fetch_playwright(self, url: str) -> FetchResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - Playwright is a hard dependency
            return FetchResult(url, url, None, "", "playwright", f"Playwright is not installed ({exc})")

        try:
            require_public_address(url)
        except UnsafeUrl as exc:
            return FetchResult(url, url, None, "", "playwright", str(exc))

        lock = _playwright_lock if settings.playwright_serialize else contextlib.nullcontext()
        try:
            with lock:
                return self._render(sync_playwright, url)
        except Exception as exc:  # noqa: BLE001 - a failed render is a failed page, not a failed crawl
            log.warning("Browser render failed for %s: %s", url, exc)
            return FetchResult(url, url, None, "", "playwright", str(exc))

    def _render(self, sync_playwright, url: str) -> FetchResult:
        timeout_ms = settings.playwright_timeout * 1000
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                context = browser.new_context(user_agent=S.USER_AGENT, locale="en-US")
                if settings.playwright_block_media:
                    context.route(
                        "**/*",
                        lambda route: (
                            route.abort()
                            if route.request.resource_type in _BLOCKED_RESOURCE_TYPES
                            else route.continue_()
                        ),
                    )
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                if page.url and page.url != url:
                    # The browser follows redirects on its own; where it landed
                    # has to be permitted too.
                    require_public_address(page.url)

                with contextlib.suppress(Exception):
                    page.wait_for_load_state(
                        "networkidle", timeout=min(timeout_ms, S.PLAYWRIGHT_NETWORK_IDLE_MS)
                    )
                # Scrolling is what pulls lazy-loaded sections into the DOM.
                for _ in range(S.PLAYWRIGHT_SCROLL_STEPS):
                    page.mouse.wheel(0, 1200)
                    page.wait_for_timeout(S.PLAYWRIGHT_SCROLL_DELAY_MS)

                html, final_url = page.content(), page.url
                status = response.status if response else None
                return FetchResult(url, final_url, status, html, "playwright")
            finally:
                browser.close()
