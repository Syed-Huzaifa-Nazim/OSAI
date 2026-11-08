"""The raw, checkable facts a page gives away about how it is built.

This is the layer underneath the comparison parameters: every value here is
something the markup either has or does not have -- a viewport tag, an alt
attribute, a pricing link, a Stripe script -- with no judgement applied.
``metrics.py`` is where those facts are turned into a score a reader can argue
with.

Kept apart from cleaner.py for one reason: the cleaner's job is to throw the
chrome away, and most of these signals live in exactly the parts it throws away
(scripts, nav, footer, forms). So the signals are read from the untouched
document first, before anything is stripped.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from . import selectors as S
from .safety import UnsafeUrl, require_public_address

log = logging.getLogger(__name__)

_WS_RE = re.compile(r"\s+")
_SITEMAP_URL_RE = re.compile(r"<loc>", re.I)


def _text(value: Any) -> str:
    return _WS_RE.sub(" ", str(value or "")).strip().lower()


def _matches(haystack: str, keywords: tuple[str, ...]) -> list[str]:
    """Which of ``keywords`` appear in ``haystack``. Order follows the list."""
    return [keyword for keyword in keywords if keyword in haystack]


def _fingerprints(sources: list[str], table: dict[str, tuple[str, ...]]) -> list[str]:
    """Named third-party services whose script URLs appear on the page."""
    blob = " ".join(sources).lower()
    return sorted(name for name, marks in table.items() if any(mark in blob for mark in marks))


def collect(soup: BeautifulSoup, page_url: str) -> dict[str, Any]:
    """Every per-page signal, read from the document before it is stripped."""
    parts = urlsplit(page_url)
    path = (parts.path or "/").lower()

    # --- what the page links to ------------------------------------------
    host = (parts.hostname or "").lower()
    internal = external = 0
    link_text_blob: list[str] = []
    cta_labels: list[str] = []
    has_about = has_contact = has_pricing = has_privacy = has_terms = False
    has_email = has_phone = False

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        label = _text(anchor.get_text(" ", strip=True)) or _text(anchor.get("aria-label"))
        link_text_blob.append(label)
        target = f"{label} {href.lower()}"

        if href.startswith("mailto:"):
            has_email = True
        elif href.startswith("tel:"):
            has_phone = True

        link_host = (urlsplit(href).hostname or "").lower()
        if not link_host or link_host == host:
            internal += 1
        elif href.startswith(("http://", "https://")):
            external += 1

        if _matches(target, S.ABOUT_LINK_KEYWORDS):
            has_about = True
        if _matches(target, S.CONTACT_LINK_KEYWORDS):
            has_contact = True
        if _matches(target, S.PRICING_LINK_KEYWORDS):
            has_pricing = True
        if _matches(target, S.PRIVACY_LINK_KEYWORDS):
            has_privacy = True
        if _matches(target, S.TERMS_LINK_KEYWORDS):
            has_terms = True
        if label and _matches(label, S.CTA_KEYWORDS):
            cta_labels.append(label[:60])

    # Buttons are calls to action too, and they are not anchors.
    for button in soup.find_all(["button", "input"]):
        label = _text(button.get_text(" ", strip=True)) or _text(button.get("value"))
        if label and _matches(label, S.CTA_KEYWORDS):
            cta_labels.append(label[:60])

    # --- head, headings, media -------------------------------------------
    title = _text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = _text(description_tag.get("content")) if description_tag else ""

    heading_levels = [int(tag.name[1]) for tag in soup.find_all(["h1", "h2", "h3", "h4"])]
    h1_count = sum(1 for level in heading_levels if level == 1)

    images = soup.find_all("img")
    with_alt = sum(1 for image in images if (image.get("alt") or "").strip())
    responsive_images = sum(1 for image in images if image.get("srcset")) + len(
        soup.find_all("picture")
    )

    scripts = soup.find_all("script")
    script_sources = [script.get("src", "") for script in scripts if script.get("src")]
    # Inline scripts carry fingerprints too (gtag snippets, chat widgets).
    inline_scripts = " ".join(
        (script.string or "")[:400] for script in scripts if not script.get("src")
    )

    forms = soup.find_all("form")
    form_fields = sum(
        len(form.find_all(["input", "select", "textarea"]))
        for form in forms
    )

    page_text = _text(soup.get_text(" ", strip=True))
    above_fold = page_text[: S.ABOVE_FOLD_CHARS]

    published = None
    for property_name in S.DATE_META_PROPERTIES:
        tag = soup.find("meta", attrs={"property": re.compile(f"^{property_name}$", re.I)}) or soup.find(
            "meta", attrs={"itemprop": re.compile(f"^{property_name}$", re.I)}
        )
        if tag and tag.get("content"):
            published = str(tag["content"])[:40]
            break
    if published is None:
        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            published = str(time_tag["datetime"])[:40]

    return {
        # --- A. content -------------------------------------------------
        "paragraph_count": len(soup.find_all("p")),
        "list_count": len(soup.find_all(["ul", "ol"])),
        "media_embed_count": len(soup.find_all(["video", "iframe"])),
        "above_fold_words": len(above_fold.split()),
        "published_at": published,
        "is_editorial": any(hint in path for hint in S.EDITORIAL_PATH_HINTS),
        # --- B. SEO -----------------------------------------------------
        "title_length": len(title),
        "has_meta_description": bool(description),
        "meta_description_length": len(description),
        "h1_count": h1_count,
        "heading_levels": heading_levels[:40],
        "heading_hierarchy_ok": _hierarchy_ok(heading_levels, h1_count),
        "internal_link_count": internal,
        "external_link_count": external,
        "has_canonical": bool(soup.find("link", rel=lambda value: value and "canonical" in value)),
        "has_og_tags": bool(soup.find("meta", attrs={"property": re.compile("^og:", re.I)})),
        "url_depth": len([segment for segment in path.split("/") if segment]),
        "url_has_query": bool(parts.query),
        "url_is_clean": _url_is_clean(page_url, parts, path),
        # --- C. UX ------------------------------------------------------
        "has_viewport_meta": bool(soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})),
        "has_lang_attribute": bool((soup.find("html") or {}).get("lang") if soup.find("html") else False),
        "has_nav_landmark": bool(soup.find("nav") or soup.find(attrs={"role": "navigation"})),
        "nav_link_count": _nav_link_count(soup),
        "image_count": len(images),
        "images_with_alt": with_alt,
        "responsive_image_count": responsive_images,
        "script_count": len(scripts),
        "stylesheet_count": len(soup.find_all("link", rel=lambda value: value and "stylesheet" in value)),
        # --- D. trust ---------------------------------------------------
        "social_proof_hits": _matches(page_text, S.SOCIAL_PROOF_KEYWORDS)[:6],
        "certification_hits": _matches(page_text, S.CERTIFICATION_KEYWORDS)[:6],
        "has_about_link": has_about,
        "has_contact_link": has_contact,
        "has_email_link": has_email,
        "has_phone_link": has_phone,
        # --- E. conversion ----------------------------------------------
        "cta_count": len(cta_labels),
        "cta_labels": sorted(set(cta_labels))[:8],
        "form_count": len(forms),
        "form_field_count": form_fields,
        "has_newsletter_signup": bool(_matches(page_text, S.NEWSLETTER_KEYWORDS)),
        "has_pricing_link": has_pricing,
        "mentions_contact_for_pricing": bool(_matches(page_text, S.PRICING_WALL_KEYWORDS)),
        # --- F. technical -------------------------------------------------
        "is_https": parts.scheme == "https",
        "has_privacy_link": has_privacy,
        "has_terms_link": has_terms,
        "has_cookie_notice": bool(_matches(page_text, S.COOKIE_KEYWORDS)),
        "analytics_tools": _fingerprints(script_sources + [inline_scripts], S.ANALYTICS_FINGERPRINTS),
        "chat_tools": _fingerprints(script_sources + [inline_scripts], S.CHAT_FINGERPRINTS),
        "payment_tools": _fingerprints(script_sources + [inline_scripts], S.PAYMENT_FINGERPRINTS),
    }


def _hierarchy_ok(levels: list[int], h1_count: int) -> bool:
    """One h1, and no level skipped on the way down."""
    if h1_count != 1 or not levels:
        return False
    previous = levels[0]
    for level in levels[1:]:
        if level > previous + 1:
            return False
        previous = level
    return True


def _url_is_clean(page_url: str, parts: Any, path: str) -> bool:
    return (
        not parts.query
        and "_" not in path
        and len(page_url) <= S.MAX_CLEAN_URL_LENGTH
        and len([segment for segment in path.split("/") if segment]) <= S.MAX_CLEAN_URL_DEPTH
        and path == path.lower()
    )


def _nav_link_count(soup: BeautifulSoup) -> int:
    navs = soup.find_all("nav") or soup.find_all(attrs={"role": "navigation"})
    return sum(len(nav.find_all("a", href=True)) for nav in navs)


def site_probes(root_url: str) -> dict[str, Any]:
    """Site-level facts that are not on any page: robots.txt and the sitemap.

    One or two extra requests per site, run once. A failure is not an error:
    the absence of a sitemap is itself the signal.
    """
    parts = urlsplit(root_url)
    origin = f"{parts.scheme}://{parts.netloc}"
    result: dict[str, Any] = {
        "has_robots_txt": False,
        "has_sitemap": False,
        "sitemap_url_count": 0,
    }

    session = requests.Session()
    session.headers.update(S.REQUEST_HEADERS)

    def get(path: str) -> requests.Response | None:
        url = f"{origin}{path}"
        try:
            require_public_address(url)
            response = session.get(url, timeout=settings.scraper_timeout, allow_redirects=True)
        except (UnsafeUrl, requests.RequestException) as exc:
            log.info("Site probe %s failed: %s", url, exc)
            return None
        return response if response.status_code == 200 else None

    robots = get(S.ROBOTS_PATH)
    if robots is not None and robots.text.strip():
        result["has_robots_txt"] = True
        for line in robots.text.splitlines():
            if line.lower().startswith("sitemap:"):
                result["has_sitemap"] = True

    for path in S.SITEMAP_PATHS:
        sitemap = get(path)
        if sitemap is None:
            continue
        body = sitemap.text[: S.SITEMAP_MAX_BYTES]
        if "<urlset" in body.lower() or "<sitemapindex" in body.lower():
            result["has_sitemap"] = True
            result["sitemap_url_count"] = len(_SITEMAP_URL_RE.findall(body))
            break

    session.close()
    return result
