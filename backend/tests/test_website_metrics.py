"""The signals a website gives away, and the A-F parameters built from them.

Two layers, tested apart because they fail differently: `signals.py` reads
facts out of markup and can only be wrong about the markup, while `metrics.py`
turns those facts into a score and can only be wrong about the judgement.

The fixture is shaped like a real marketing page: a nav, a hero with one call
to action, a pricing link, testimonials, a footer with the legal links, a
signup form, and the third-party scripts such a site loads.
"""

from __future__ import annotations

from typing import Any

import pytest
from bs4 import BeautifulSoup

from app.models.ecommerce import ComparisonGroup
from app.scrapers import get_source_scraper
from app.scrapers.website import metrics, signals

STRONG_PAGE = """
<!DOCTYPE html><html lang="en"><head>
  <title>Verdant Roast: speciality coffee, roasted weekly</title>
  <meta name="description" content="Small-batch speciality coffee roasted to order and shipped within 24 hours, for homes and independent cafes.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta property="og:title" content="Verdant Roast">
  <link rel="canonical" href="https://verdantroast.test/">
  <link rel="stylesheet" href="/style.css">
  <script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>
  <script src="https://widget.intercom.io/widget/abc"></script>
  <script src="https://js.stripe.com/v3"></script>
</head><body>
  <nav>
    <a href="/shop">Shop</a><a href="/pricing">Pricing</a><a href="/about">About us</a>
    <a href="/contact">Contact</a><a href="/blog">Blog</a>
  </nav>
  <main>
    <h1>Coffee roasted the week you drink it</h1>
    <p>We roast to order and ship within 24 hours, so what reaches you is days old, not months.</p>
    <a href="/signup">Start free trial</a>
    <h2>What our customers say</h2>
    <p>Trusted by 40 independent cafes. Read our case studies.</p>
    <img src="/a.jpg" alt="A bag of coffee" srcset="/a.jpg 1x">
    <img src="/b.jpg" alt="Our roastery">
    <h3>Certified</h3>
    <p>ISO 9001 certified and GDPR compliant. Secure checkout on every order.</p>
    <ul><li>Single origin</li><li>Subscriptions</li></ul>
    <form action="/signup">
      <input name="email"><input name="password"><button type="submit">Sign up</button>
    </form>
  </main>
  <footer>
    <a href="/privacy">Privacy policy</a><a href="/terms">Terms</a>
    <a href="mailto:hello@verdantroast.test">Email us</a><a href="tel:+123">Call us</a>
    <a href="https://twitter.com/verdantroast">Twitter</a>
    <p>We use cookies to improve your experience.</p>
  </footer>
</body></html>
"""

WEAK_PAGE = """
<!DOCTYPE html><html><head>
  <title>Home</title>
  <script src="/a.js"></script><script src="/b.js"></script>
</head><body>
  <div><h1>Welcome</h1><h1>Also welcome</h1><h3>Skipped a level</h3>
  <img src="/x.jpg">
  <a href="/Page_One.html?ref=1">More</a>
  </div>
</body></html>
"""


def collect(html: str, url: str = "https://verdantroast.test/") -> dict[str, Any]:
    return signals.collect(BeautifulSoup(html, "lxml"), url)


# =================================================================== signals


def test_a_marketing_page_gives_away_what_it_is_built_from() -> None:
    marks = collect(STRONG_PAGE)

    # B: SEO
    assert marks["title_length"] > 15 and marks["has_meta_description"]
    assert marks["h1_count"] == 1 and marks["heading_hierarchy_ok"]
    assert marks["has_canonical"] and marks["has_og_tags"]
    assert marks["internal_link_count"] >= 8 and marks["external_link_count"] == 1
    assert marks["url_is_clean"]

    # C: UX
    assert marks["has_viewport_meta"] and marks["has_lang_attribute"]
    assert marks["has_nav_landmark"] and marks["nav_link_count"] == 5
    assert marks["image_count"] == 2 and marks["images_with_alt"] == 2
    assert marks["responsive_image_count"] == 1

    # D: trust
    assert "what our customers" in marks["social_proof_hits"]
    assert any("iso 9001" == hit for hit in marks["certification_hits"])
    assert marks["has_about_link"] and marks["has_contact_link"]
    assert marks["has_email_link"] and marks["has_phone_link"]

    # E: conversion
    assert marks["cta_count"] >= 2               # "start free trial" and "sign up"
    assert marks["form_count"] == 1 and marks["form_field_count"] == 2
    assert marks["has_pricing_link"] and not marks["mentions_contact_for_pricing"]

    # F: technical
    assert marks["is_https"]
    assert marks["has_privacy_link"] and marks["has_terms_link"] and marks["has_cookie_notice"]
    assert marks["analytics_tools"] == ["Google Analytics"]
    assert marks["chat_tools"] == ["Intercom"]
    assert marks["payment_tools"] == ["Stripe"]


def test_a_thin_page_is_read_as_thin() -> None:
    marks = collect(WEAK_PAGE, "https://verdantroast.test/Page_One.html?ref=1")

    assert marks["h1_count"] == 2 and not marks["heading_hierarchy_ok"]
    assert not marks["has_meta_description"] and not marks["has_viewport_meta"]
    assert not marks["has_lang_attribute"] and not marks["has_nav_landmark"]
    assert marks["images_with_alt"] == 0
    assert marks["cta_count"] == 0 and marks["form_count"] == 0
    assert not marks["has_privacy_link"] and not marks["url_is_clean"]
    assert marks["analytics_tools"] == [] and marks["payment_tools"] == []


def test_signals_survive_markup_that_is_barely_html() -> None:
    for html in ("", "<html>", "<p>hello", "not markup at all"):
        marks = collect(html)
        assert marks["h1_count"] == 0
        assert marks["cta_count"] == 0


def test_a_pricing_wall_is_told_apart_from_published_pricing() -> None:
    walled = collect(
        "<html><body><a href='/pricing'>Pricing</a>"
        "<p>Contact us for pricing that fits your team.</p></body></html>"
    )
    assert walled["has_pricing_link"] and walled["mentions_contact_for_pricing"]


# ================================================================ aggregate


def _page(url: str, words: int, marks: dict[str, Any], depth: int = 0, **extra: Any) -> dict[str, Any]:
    return {
        "submitted_url": "https://verdantroast.test/",
        "page_url": url,
        "title": extra.get("title", "Verdant Roast: speciality coffee"),
        "meta_description": extra.get("meta_description", "Small-batch coffee."),
        "word_count": words,
        "heading_count": 3,
        "link_count": 10,
        "depth": depth,
        "is_root": depth == 0,
        "renderer": extra.get("renderer", "http"),
        "signals": marks,
    }


def strong_site() -> list[dict[str, Any]]:
    home = collect(STRONG_PAGE)
    home.update({"has_robots_txt": True, "has_sitemap": True, "sitemap_url_count": 42})
    inner = collect(STRONG_PAGE, "https://verdantroast.test/shop")
    return [
        _page("https://verdantroast.test/", 900, home),
        _page("https://verdantroast.test/shop", 700, inner, depth=1),
        _page("https://verdantroast.test/blog/roasting", 800, {**inner, "is_editorial": True,
              "published_at": "2026-09-01T00:00:00Z"}, depth=1),
    ]


def weak_site() -> list[dict[str, Any]]:
    # Served over plain http, which is itself one of the things F measures.
    home = collect(WEAK_PAGE, "http://northbrew.test/")
    return [
        _page("http://northbrew.test/", 80, home, title="Home", meta_description=""),
        _page("http://northbrew.test/Page_One.html", 60, home, depth=1, title="Home"),
    ]


def test_a_site_is_summarised_into_the_figures_the_parameters_compare() -> None:
    meta = metrics.aggregate(strong_site())

    assert meta["pages_crawled"] == 3
    assert meta["value_proposition"] == "Clear" and meta["value_proposition_score"] >= 75
    assert "PASS" in meta["value_proposition_checks"]
    assert meta["content_depth"] == "Substantial" and meta["thin_page_share"] == 0.0
    assert meta["editorial_page_count"] == 1
    assert meta["content_freshness"] == "Dated content published"
    assert meta["title_quality_score"] == 100.0
    assert meta["heading_structure_score"] == 100.0
    assert meta["mobile_ready_share"] == 100.0
    assert meta["alt_text_coverage"] == 100.0
    assert meta["navigation_clarity"] == "Clear"
    assert meta["trust_score"] == 100.0
    assert meta["pricing_transparency"] == "Published"
    assert meta["friction_label"] == "Short form"
    assert meta["lead_capture"] == "Form only"
    assert meta["has_sitemap"] and meta["sitemap_url_count"] == 42
    assert meta["security_score"] == 100.0
    assert "Google Analytics" in meta["analytics_tools"]
    assert meta["integration_count"] == 3
    assert "coffee" in meta["primary_keywords"]


def test_a_weak_site_scores_low_for_stated_reasons() -> None:
    meta = metrics.aggregate(weak_site())

    assert meta["value_proposition"] == "Unclear"
    assert "FAIL  Description written for search" in meta["value_proposition_checks"]
    assert meta["content_depth"] == "Thin" and meta["thin_page_share"] == 100.0
    assert meta["navigation_clarity"] == "No navigation landmark"
    assert meta["mobile_ready_share"] == 0.0
    assert meta["pricing_transparency"] == "No pricing anywhere"
    assert meta["lead_capture"] == "None found"
    assert meta["content_freshness"] == "No blog or updates found"
    assert meta["security_score"] < 50


def test_a_site_with_no_pages_does_not_raise() -> None:
    assert metrics.aggregate([]) == {"pages_crawled": 0}


# =============================================================== comparison


def test_six_parameter_groups_a_to_f() -> None:
    groups = metrics.compare_all(metrics.aggregate(strong_site()), metrics.aggregate(weak_site()))

    assert [group["letter"] for group in groups] == list("ABCDEF")
    assert [group["key"] for group in groups] == [
        "content_strategy", "seo_signals", "ux_design", "trust_credibility",
        "conversion", "technical",
    ]
    for group in groups:
        # Every searched field is one the scraper actually produces...
        assert set(group["semantic_field_types"]) <= {"page_text", "headings", "meta"}
        # ...and every group fits the API's response model.
        ComparisonGroup.model_validate(group)


def test_the_stronger_site_wins_the_rows_it_should() -> None:
    groups = {
        group["key"]: group
        for group in metrics.compare_all(
            metrics.aggregate(strong_site()), metrics.aggregate(weak_site())
        )
    }

    def row(key: str, field: str) -> dict[str, Any]:
        return next(item for item in groups[key]["metrics"] if item["field"] == field)

    assert row("content_strategy", "value_proposition_score")["winner"] == "own"
    assert row("seo_signals", "pages_missing_h1")["winner"] == "tie"
    assert row("ux_design", "mobile_ready_share")["winner"] == "own"
    assert row("trust_credibility", "trust_score")["winner"] == "own"
    assert row("conversion", "home_cta_count")["winner"] == "own"
    assert row("technical", "is_https")["winner"] == "own"
    # A descriptive row is never given a winner.
    assert row("content_strategy", "content_depth")["winner"] is None


def test_the_weaker_side_is_told_what_is_missing() -> None:
    groups = {
        group["key"]: group
        for group in metrics.compare_all(
            metrics.aggregate(weak_site()), metrics.aggregate(strong_site())
        )
    }
    said = " ".join(groups["technical"]["insights"] + groups["trust_credibility"]["insights"])

    assert "sitemap" in said.lower()
    assert "privacy policy" in said.lower()
    assert "social proof" in said.lower() or "certifications" in said.lower()


def test_two_identical_sites_only_tie() -> None:
    meta = metrics.aggregate(strong_site())
    assert all(
        row["winner"] in (None, "tie")
        for group in metrics.compare_all(meta, dict(meta))
        for row in group["metrics"]
    )


def test_the_scraper_exposes_the_parameters_through_the_contract() -> None:
    scraper = get_source_scraper("website")
    assert [param["letter"] for param in scraper.comparison_parameters()] == list("ABCDEF")
    assert scraper.aggregate([]) == {"pages_crawled": 0}
    assert scraper.build_metrics(
        metrics.aggregate(strong_site()), metrics.aggregate(weak_site())
    )[0]["key"] == "content_strategy"


def test_instagram_has_no_parameters_yet() -> None:
    """Only the website comparison is scored; a profile is shown, not judged."""
    assert get_source_scraper("instagram").comparison_parameters() == []
