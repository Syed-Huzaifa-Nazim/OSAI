"""The Alibaba scraper, piece by piece, with no network.

Extraction runs against real listing records captured from
wholesaler.alibaba.com in September 2026 (tests/fixtures/alibaba), sanitised of
contact routes, chat tokens and tracking links. Fetching is replaced with
fakes, so the orchestration -- robots checks, the requests-then-browser order,
stopping at a block -- is tested without touching Alibaba.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import requests

import app.scrapers.alibaba.robots as robots_module
import app.scrapers.alibaba.scraper as scraper_module
from app.core.config import settings
from app.models.ecommerce import ComparisonGroup
from app.scrapers import ScraperError, get_scraper
from app.scrapers.alibaba import metrics, selectors as S
from app.scrapers.alibaba.extract import TEXT_FIELD_TYPES, extract_offer, plural_unit, unit_key
from app.scrapers.alibaba.images import extract_images, normalise_image_url
from app.scrapers.alibaba.listing import detect_challenge, parse_listing
from app.scrapers.alibaba.robots import RobotsDisallowed, RobotsPolicy, RobotsRules
from app.scrapers.alibaba.scraper import ScrapeError, scrape_alibaba_product
from app.scrapers.alibaba.urls import (
    InvalidAlibabaUrl,
    absolute_url,
    listing_url,
    parse_product_link,
    search_slugs,
)

FIXTURES = Path(__file__).parent / "fixtures" / "alibaba"
OFFERS: dict[str, dict[str, Any]] = {
    str(offer["id"]): offer
    for offer in json.loads((FIXTURES / "listing_offers.json").read_text(encoding="utf-8"))["offers"]
}
CHALLENGE_HTML = (FIXTURES / "challenge.html").read_text(encoding="utf-8")

MOUSE_ID = "1601364965690"        # 3 tiers, Gold Supplier, sponsored, video
GAMING_ID = "1601688290824"       # MOQ 1, 4 tiers, verified supplier, no specs
CAMPAIGN_ID = "1601508426121"     # campaign badge, 500-unit MOQ, no dispatch label
PROMO_ID = "1601283982480"        # 11% promotion running

MOUSE_URL = (
    "https://www.alibaba.com/product-detail/Mini-Wireless-Mouse-Ergonomic-4-Buttons_1601364965690.html"
    "?spm=a2700.galleryofferlist.normal_offer.d_title.1b2c3d&s=p"
)
GAMING_URL = "https://www.alibaba.com/product-detail/MLOONG-MX302-Ultra-Lightweight-Wireless-Gaming_1601688290824.html"


def offer(product_id: str) -> dict[str, Any]:
    return copy.deepcopy(OFFERS[product_id])


def listing_page(*product_ids: str, extra_items: list[dict[str, Any]] | None = None) -> str:
    """A listing page shaped like the real one: the result set as embedded JSON."""
    items = [{"offer": offer(pid)} for pid in product_ids] + (extra_items or [])
    page_data = {"offerResultData": {"itemInfoList": items}, "pageInfo": {"keyword": "mouse"}}
    return (
        "<!DOCTYPE html><html><head><title>Wholesale mouse</title></head><body>"
        '<div id="root"></div>'
        f"<script>window._PAGE_DATA_ = {json.dumps(page_data)};</script>"
        "</body></html>"
    )


# ===================================================================== links


def test_desktop_link_gives_the_id_and_the_title_words() -> None:
    link = parse_product_link(MOUSE_URL)
    assert link.product_id == MOUSE_ID
    assert link.slug == "mini-wireless-mouse-ergonomic-4-buttons"
    # Tracking parameters are gone; the title keeps its capitalisation for display.
    assert link.canonical_url == (
        "https://www.alibaba.com/product-detail/Mini-Wireless-Mouse-Ergonomic-4-Buttons_1601364965690.html"
    )


@pytest.mark.parametrize(
    ("url", "slug"),
    [
        ("https://m.alibaba.com/product/1601364965690/Mini-Wireless-Mouse.html", "mini-wireless-mouse"),
        ("https://m.alibaba.com/product/1601364965690.html", ""),
        ("https://french.alibaba.com/product-detail/Souris-Sans-Fil_1601364965690.html", "souris-sans-fil"),
        ("https://www.alibaba.com/product-detail/Mini%20Wireless_Mouse_1601364965690.html#reviews", "mini-wireless-mouse"),
    ],
)
def test_mobile_regional_and_encoded_links_are_understood(url: str, slug: str) -> None:
    link = parse_product_link(url)
    assert link.product_id == MOUSE_ID
    assert link.slug == slug


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("", "empty"),
        ("ftp://www.alibaba.com/product-detail/Mouse_1601364965690.html", "http"),
        ("https://www.daraz.pk/products/hp-w10-i1957626953.html", "not an Alibaba domain"),
        # Lookalike hosts are not Alibaba.
        ("https://alibaba.com.evil.example/product-detail/Mouse_1601364965690.html", "not an Alibaba domain"),
        ("https://notalibaba.com/product-detail/Mouse_1601364965690.html", "not an Alibaba domain"),
        ("https://www.alibaba.com/showroom/wireless-mouse.html", "not a single product page"),
        ("https://wholesaler.alibaba.com/w/wholesale-mouse.html", "not a single product page"),
    ],
)
def test_anything_but_an_alibaba_product_link_is_refused(url: str, message: str) -> None:
    with pytest.raises(InvalidAlibabaUrl, match=message):
        parse_product_link(url)


def test_search_terms_go_from_the_full_title_to_its_core_words() -> None:
    assert search_slugs("mini-wireless-mouse-ergonomic-4-buttons-2-4ghz-optical-laptop-aa") == [
        "mini-wireless-mouse-ergonomic-4-buttons-2-4ghz",
        "mini-wireless-mouse-ergonomic-4",
        "mini-wireless-mouse",
    ]
    # Generic selling words are dropped from the shorter variants, never repeated.
    assert search_slugs("hot-sale-wireless-mouse-for-laptop") == [
        "hot-sale-wireless-mouse-for-laptop",
        "wireless-mouse-laptop",
    ]
    assert search_slugs("mouse") == ["mouse"]
    assert search_slugs("") == []


def test_listing_urls_never_carry_a_query_string() -> None:
    # robots.txt on the listing host disallows /*?
    url = listing_url("wireless-mouse")
    assert url == "https://wholesaler.alibaba.com/w/wholesale-wireless-mouse.html"
    assert "?" not in url


def test_protocol_relative_and_site_relative_urls_become_absolute() -> None:
    assert absolute_url("//s.alicdn.com/a.jpg") == "https://s.alicdn.com/a.jpg"
    assert absolute_url("/product-detail/x_1601364965690.html") == (
        "https://www.alibaba.com/product-detail/x_1601364965690.html"
    )
    for bad in (None, "", "javascript:void(0)", 42):
        assert absolute_url(bad) is None  # type: ignore[arg-type]


# ================================================================ robots.txt

WHOLESALER_ROBOTS = """User-agent: *
Disallow: /*?
Disallow: /manager/
Disallow: /shopcart/
Disallow: /store/
"""


def test_the_real_listing_policy_allows_listing_pages_but_not_queries() -> None:
    rules = RobotsRules.parse(WHOLESALER_ROBOTS)
    ua = S.USER_AGENT
    assert rules.can_fetch(ua, "https://wholesaler.alibaba.com/w/wholesale-wireless-mouse.html")
    # A prefix-only matcher (urllib.robotparser) gets this one wrong.
    assert not rules.can_fetch(ua, "https://wholesaler.alibaba.com/w/wholesale-wireless-mouse.html?page=2")
    assert not rules.can_fetch(ua, "https://wholesaler.alibaba.com/manager/orders")


def test_end_anchor_longest_match_and_allow_winning_ties() -> None:
    rules = RobotsRules.parse(
        "User-agent: *\n"
        "Disallow: /*.json$\n"
        "Disallow: /w/\n"
        "Allow: /w/wholesale-\n"
        "Disallow: /page\n"
        "Allow: /page\n"
    )
    ua = S.USER_AGENT
    assert not rules.can_fetch(ua, "https://x.alibaba.com/data.json")
    assert rules.can_fetch(ua, "https://x.alibaba.com/data.json.html")   # "$" anchors the end
    assert rules.can_fetch(ua, "https://x.alibaba.com/w/wholesale-mouse.html")  # longer Allow wins
    assert not rules.can_fetch(ua, "https://x.alibaba.com/w/other.html")
    assert rules.can_fetch(ua, "https://x.alibaba.com/page")               # tie goes to Allow


def test_the_most_specific_user_agent_group_applies() -> None:
    rules = RobotsRules.parse(
        "User-agent: *\nDisallow: /\n\n"
        "User-agent: OptiStratixAI-Scout\nAllow: /\nCrawl-delay: 4\n"
    )
    assert rules.can_fetch(S.USER_AGENT, "https://x.alibaba.com/anything")
    assert rules.crawl_delay(S.USER_AGENT) == 4.0
    assert not rules.can_fetch("SomeOtherBot/1.0", "https://x.alibaba.com/anything")
    assert rules.crawl_delay("SomeOtherBot/1.0") is None


def test_an_empty_disallow_restricts_nothing() -> None:
    assert RobotsRules.parse("User-agent: *\nDisallow:\n").can_fetch(S.USER_AGENT, "https://x.alibaba.com/a")


class _Response:
    def __init__(self, status_code: int = 200, text: str = "", url: str = "") -> None:
        self.status_code = status_code
        self.text = text
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_policy_fetches_robots_once_per_origin_and_enforces_it(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_get(url: str, **kwargs: Any) -> _Response:
        calls.append(url)
        return _Response(text=WHOLESALER_ROBOTS)

    monkeypatch.setattr(robots_module.requests, "get", fake_get)
    policy = RobotsPolicy(S.USER_AGENT)

    policy.require_allowed("https://wholesaler.alibaba.com/w/wholesale-mouse.html")
    policy.require_allowed("https://wholesaler.alibaba.com/w/wholesale-keyboard.html")
    with pytest.raises(RobotsDisallowed):
        policy.require_allowed("https://wholesaler.alibaba.com/w/wholesale-mouse.html?page=2")
    assert calls == ["https://wholesaler.alibaba.com/robots.txt"]


@pytest.mark.parametrize("failure", ["missing", "unreachable"])
def test_a_missing_or_unreachable_robots_file_imposes_no_rules(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    def fake_get(url: str, **kwargs: Any) -> _Response:
        if failure == "unreachable":
            raise requests.ConnectionError("down")
        return _Response(status_code=404)

    monkeypatch.setattr(robots_module.requests, "get", fake_get)
    RobotsPolicy(S.USER_AGENT).require_allowed("https://wholesaler.alibaba.com/w/wholesale-mouse.html")


# ==================================================================== images


def test_resized_thumbnails_resolve_to_the_original_upload() -> None:
    original = "https://s.alicdn.com/@sc04/kf/Hfdceac95980345cb81a69168a387e0b1b.jpg"
    assert normalise_image_url(original.replace("https:", "") + "_300x300.jpg") == original
    assert normalise_image_url(original + "_220x220.jpg_.webp") == original
    assert normalise_image_url(original + "_120x120q80.jpg") == original
    png = "https://s.alicdn.com/@sc04/kf/H26eee288553d45c5a325d281a8c7a18cx.png"
    assert normalise_image_url(png + "_200x200.png") == png


def test_non_images_are_rejected() -> None:
    for bad in (None, "", 42, "//www.alibaba.com/product-detail/Mouse_1601364965690.html", "not a url"):
        assert normalise_image_url(bad) is None


def test_the_same_photo_at_two_sizes_is_one_image_and_the_big_image_is_added_if_new() -> None:
    base = "//s.alicdn.com/@sc04/kf/"
    images = extract_images(
        [base + "Ha.jpg_300x300.jpg", base + "Hb.png_300x300.png", base + "Ha.jpg_220x220.jpg_.webp"],
        base + "Hc.jpg",
    )
    assert [image.url for image in images] == [
        "https://s.alicdn.com/@sc04/kf/Ha.jpg",
        "https://s.alicdn.com/@sc04/kf/Hb.png",
        "https://s.alicdn.com/@sc04/kf/Hc.jpg",
    ]
    assert extract_images("not a list", base + "Ha.jpg_300x300.jpg")[0].url.endswith("/Ha.jpg")


def test_a_gallery_is_capped() -> None:
    gallery = [f"//s.alicdn.com/@sc04/kf/H{index:032x}.jpg_300x300.jpg" for index in range(40)]
    assert len(extract_images(gallery, None)) == S.IMAGE_MAX_PER_PRODUCT


# =================================================================== listing


def test_listing_offers_are_read_from_the_embedded_json() -> None:
    html = listing_page(
        MOUSE_ID, GAMING_ID,
        extra_items=[
            {"banner": {"title": "Super September"}},                 # not a product
            {"offer": {"id": "999999999", "information": {}}},        # no product link: a promo tile
        ],
    )
    page = parse_listing(html)
    assert set(page.offers) == {MOUSE_ID, GAMING_ID}
    assert page.from_page_data is True
    assert page.challenged is False


def test_product_data_wins_over_words_that_look_like_a_block() -> None:
    # Real listing pages load captcha scripts too; with products present that is not a block.
    html = listing_page(MOUSE_ID).replace(
        "</body>", '<script src="//g.alicdn.com/sd/nocaptcha/nocaptcha.js"></script></body>'
    )
    page = parse_listing(html)
    assert page.challenged is False
    assert MOUSE_ID in page.offers


def test_an_anti_bot_page_is_recognised() -> None:
    page = parse_listing(CHALLENGE_HTML)
    assert page.challenged is True
    assert page.offers == {}
    assert detect_challenge(CHALLENGE_HTML)
    assert detect_challenge("") == "empty response body"


def test_product_cards_are_read_when_the_json_is_missing_or_broken() -> None:
    cards = """
      <div class="organic-list">
        <div class="fy23-search-card">
          <a href="//www.alibaba.com/product-detail/Mini-Wireless-Mouse_1601364965690.html?spm=x"
             title="Mini 3D LED Wireless Mouse Ergonomic 4 Buttons">Mini mouse</a>
          <img src="//s.alicdn.com/@sc04/kf/Hfdceac95980345cb81a69168a387e0b1b.jpg_300x300.jpg">
          <div class="search-card-e-price-main">US $0.75-0.77</div>
        </div>
        <div class="fy23-search-card">
          <a href="https://www.alibaba.com/product-detail/Gaming-Mouse_1601688290824.html">
            <h2 class="search-card-e-title">MLOONG MX302 Wireless Gaming Mouse</h2></a>
        </div>
      </div>"""
    broken = f'<html><body>{cards}<script>window._PAGE_DATA_ = {{"offerResultData": {{broken</script></body></html>'

    page = parse_listing(broken)
    assert page.from_page_data is False
    assert set(page.offers) == {MOUSE_ID, GAMING_ID}

    product = extract_offer(page.offers[MOUSE_ID], from_page_data=False)
    assert product.text_fields["title"] == "Mini 3D LED Wireless Mouse Ergonomic 4 Buttons"
    # "US $0.75-0.77": the hyphen separates the range, it is not a minus sign.
    assert (product.metadata["price"], product.metadata["max_price"]) == (0.75, 0.77)
    assert [image.url for image in product.images] == [
        "https://s.alicdn.com/@sc04/kf/Hfdceac95980345cb81a69168a387e0b1b.jpg"
    ]
    assert product.supplier is None
    assert any("page layout" in warning for warning in product.warnings)


# =================================================================== extract


def test_quantity_tiers_minimum_order_and_dispatch_time() -> None:
    product = extract_offer(offer(MOUSE_ID))
    meta = product.metadata

    assert product.price_tiers == [
        {"min_quantity": 100, "max_quantity": 499, "price": 0.77, "currency": "USD", "unit": "pieces"},
        {"min_quantity": 500, "max_quantity": 999, "price": 0.76, "currency": "USD", "unit": "pieces"},
        # quantityMax -1 is the open-ended "1,000+" tier.
        {"min_quantity": 1000, "max_quantity": None, "price": 0.75, "currency": "USD", "unit": "pieces"},
    ]
    assert (meta["currency"], meta["price"], meta["max_price"]) == ("USD", 0.75, 0.77)
    assert (meta["moq"], meta["moq_unit"], meta["moq_label"]) == (100, "pieces", "100 pieces")
    assert (meta["first_tier_price"], meta["best_tier_price"], meta["best_tier_min_quantity"]) == (0.77, 0.75, 1000)
    assert meta["bulk_discount_percent"] == 2.6
    assert (meta["lead_time_days"], meta["lead_time_label"]) == (5, "5-day dispatch")
    assert meta["buy_now_available"] is True
    assert meta["original_price"] is None and meta["discount_percent"] is None

    terms = product.text_fields["order_terms"]
    assert "Minimum order quantity: 100 pieces" in terms
    assert "- 1,000+ pieces: US$0.75" in terms


def test_supplier_credentials() -> None:
    product = extract_offer(offer(MOUSE_ID))
    assert product.supplier == {
        "name": "Guangzhou Kingmega Electronic Firm",
        "country_code": "CN",
        "country_name": "China",
        "years_on_platform": 2,
        "gold_supplier": True,
        "verified": False,
        "trade_assurance": True,
        "transaction_level": 5,
        "response_rate": 98.2,
        "historic_order_count": 207,
        "historic_gmv_label": "$70,000+",
        "historic_gmv_min": 70000.0,
        "main_products": "smart watch chargers,silicone straps,smart watch,smart band,watch charging cable",
    }
    meta = product.metadata
    assert meta["supplier_name"] == meta["seller_name"] == "Guangzhou Kingmega Electronic Firm"
    assert (meta["gold_supplier"], meta["verified_supplier"], meta["trade_assurance"]) == (True, False, True)
    assert "Gold Supplier, Trade Assurance" in product.text_fields["supplier"]


def test_images_specs_badges_reviews_and_placement() -> None:
    product = extract_offer(offer(MOUSE_ID))
    meta = product.metadata

    assert meta["image_count"] == len(product.images) == 6
    assert product.images[0].url == "https://s.alicdn.com/@sc04/kf/Hfdceac95980345cb81a69168a387e0b1b.jpg"
    assert not any("x300" in image.url for image in product.images)
    assert meta["has_video"] is True

    assert meta["spec_count"] == 5
    assert "- DPI: 1200" in product.text_fields["specs"]
    assert (meta["promo_tags"], meta["ready_to_ship"], meta["has_campaign_tag"]) == ("Ready to Ship", True, False)
    assert meta["sponsored"] is True
    assert (meta["review_count"], meta["rating"]) == (15, 4.9)
    assert meta["item_id"] == MOUSE_ID
    assert meta["content_completeness_score"] == 100.0
    assert set(product.text_fields) == set(TEXT_FIELD_TYPES)
    assert product.warnings == []


def test_a_listing_without_specifications_says_so() -> None:
    product = extract_offer(offer(GAMING_ID))
    assert product.metadata["spec_count"] == 0
    assert product.text_fields["specs"] == "No specification attributes are listed for this product."
    assert product.metadata["title_attribute_match"] == "unknown"
    assert (product.metadata["moq"], product.metadata["moq_unit"]) == (1, "piece")
    assert product.metadata["verified_supplier"] is True


def test_the_ladder_starts_at_the_minimum_order() -> None:
    """Real record: one placeholder tier "1+ units" next to "Min. order: 500 units"."""
    product = extract_offer(offer(CAMPAIGN_ID))
    assert product.price_tiers == [
        {"min_quantity": 500, "max_quantity": None, "price": 1.85, "currency": "USD", "unit": "unit"}
    ]
    assert product.metadata["best_tier_min_quantity"] == 500


def test_tiers_counted_in_another_unit_are_left_alone() -> None:
    data = offer(CAMPAIGN_ID)
    data["tradePrice"]["minOrder"] = "2 cartons"
    product = extract_offer(data)
    assert product.price_tiers[0]["min_quantity"] == 1


def test_a_campaign_badge_and_processing_time_without_a_dispatch_label() -> None:
    meta = extract_offer(offer(CAMPAIGN_ID)).metadata
    assert (meta["promo_tags"], meta["has_campaign_tag"], meta["ready_to_ship"]) == ("Super September", True, False)
    assert (meta["lead_time_days"], meta["lead_time_label"]) == (31, "31-day processing")
    assert meta["buy_now_available"] is False


def test_a_running_promotion_prices_at_the_live_range() -> None:
    """During a promotion the top-level price and originalPriceFrom are the LIST price."""
    product = extract_offer(offer(PROMO_ID))
    meta = product.metadata

    assert (meta["price"], meta["max_price"]) == (1.25, 1.42)
    assert (meta["original_price"], meta["discount_percent"]) == (1.4, 11.0)
    assert meta["price_range_label"] == "US$1.25 - US$1.42 on promotion (list US $1.40-$1.60)"
    # The ladder is stored as published; its ends are priced as they are today.
    assert [tier["price"] for tier in product.price_tiers] == [1.6, 1.55, 1.4]
    assert (meta["first_tier_price"], meta["best_tier_price"]) == (1.42, 1.25)
    assert meta["bulk_discount_percent"] == 12.5
    assert "11% off list prices" in product.text_fields["order_terms"]


def test_the_published_range_outranks_a_single_variant_ladder() -> None:
    data = offer(MOUSE_ID)
    data["promotionInfoVO"]["quantityPrices"] = [{"price": "0.77", "quantityMin": 100, "quantityMax": -1, "unit": "pieces"}]
    data["promotionInfoVO"]["originalPriceFrom"] = "0.70"
    data["promotionInfoVO"]["originalPriceTo"] = "0.80"
    meta = extract_offer(data).metadata
    assert (meta["price"], meta["max_price"]) == (0.7, 0.8)


def test_a_score_with_no_reviews_behind_it_is_not_a_rating() -> None:
    data = offer(MOUSE_ID)
    data["reviews"] = {"reviewCount": 0, "reviewScore": "5.0"}
    meta = extract_offer(data).metadata
    assert (meta["review_count"], meta["rating"]) == (0, None)


def test_brand_and_customisation_come_from_specifications_and_title() -> None:
    data = offer(MOUSE_ID)
    data["features"]["productAttribute"].append({"name": "Brand Name", "value": "Kingmega"})
    data["information"]["enPureTitle"] = "OEM Custom Logo Wireless Mouse"
    meta = extract_offer(data).metadata
    assert (meta["brand"], meta["is_branded"]) == ("Kingmega", True)
    assert meta["customizable"] is True
    assert "oem" in meta["customization_signals"] and "custom logo" in meta["customization_signals"]

    data["features"]["productAttribute"][-1]["value"] = "OEM"
    assert extract_offer(data).metadata["is_branded"] is False


def test_contact_routes_chat_tokens_and_tracking_never_reach_the_output() -> None:
    data = offer(MOUSE_ID)
    data["aliTalk"] = {"chatToken": "SECRET-CHAT-TOKEN", "url": "https://message.alibaba.com/msgsend/contact.htm?id=1"}
    data["trackInfo"] = {"click": "https://us-click.alibaba.com/ci_bb?a=1"}
    data["extra"] = {"encryptId": "ENCRYPTED-EXTRA"}
    data["information"]["eurl"] = "https://us-click.alibaba.com/ci_bb?eurl=abc"
    data["information"]["encryptId"] = "ENCRYPTED-PRODUCT"
    data["supplier"]["contactSupplier"] = "https://message.alibaba.com/msgsend/contact.htm?action=contact"
    data["supplier"]["encryptSupplierId"] = "ENCRYPTED-SUPPLIER"
    data["company"]["selectionHref"] = "https://selection.alibaba.com/abc"
    data["reviews"]["reviewLink"] = "//kingmega.en.alibaba.com/company_profile/feedback.html"

    product = extract_offer(data)
    output = json.dumps({
        "text": product.text_fields,
        "meta": product.metadata,
        "images": [image.url for image in product.images],
        "tiers": product.price_tiers,
        "supplier": product.supplier,
        "warnings": product.warnings,
    })
    for marker in [*S.PRIVATE_VALUE_HINTS, "SECRET-CHAT-TOKEN", "us-click", "ENCRYPTED", "company_profile"]:
        assert marker not in output, marker


def test_malformed_offers_do_not_raise() -> None:
    empty = extract_offer({})
    assert empty.text_fields["title"] == "Title not found"
    assert (empty.metadata["price"], empty.price_tiers, empty.supplier, empty.images) == (None, [], None, [])
    assert empty.metadata["price_range_label"] == "not stated"

    garbage = extract_offer({
        "promotionInfoVO": {"quantityPrices": [
            None, "tier", {"price": "n/a", "quantityMin": 1}, {"price": "1.0", "quantityMin": 0},
            {"price": "2", "quantityMin": "10", "quantityMax": "5"},
        ], "showPromotion": True, "promotionPriceFrom": "9"},
        "features": {"productAttribute": [None, 5, {"name": "Brand Name", "value": "Logitech"}]},
        "tag": {"promotionTag": "not a list"},
        "reviews": {"reviewCount": "n/a", "reviewScore": "abc"},
        "image": {"multiImage": {"not": "a list"}, "bigImage": 42},
        "supplier": {"supplierName": "Acme", "supplierYear": None},
        "company": {"record": {"responseRate": "250%"}},
    })
    assert garbage.price_tiers == [
        {"min_quantity": 10, "max_quantity": None, "price": 2.0, "currency": "USD", "unit": None}
    ]
    # A "promotion" priced above the list price is not a promotion.
    assert garbage.metadata["discount_percent"] is None
    assert garbage.metadata["brand"] == "Logitech"
    assert garbage.metadata["review_count"] == 0 and garbage.metadata["rating"] is None
    assert garbage.supplier is not None and garbage.supplier["response_rate"] is None


# ============================================================ orchestration


class FakeRobots:
    def __init__(self, disallowed: set[str] | None = None) -> None:
        self.checked: list[str] = []
        self.disallowed = disallowed or set()

    def require_allowed(self, url: str) -> None:
        self.checked.append(url)
        if url in self.disallowed:
            raise RobotsDisallowed(f"robots.txt disallows fetching {url}")

    def crawl_delay(self, url: str) -> float | None:
        return None


@pytest.fixture
def network(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Pages served by URL; every fetch recorded. No real request, no sleeping."""
    state: dict[str, Any] = {
        "robots": FakeRobots(),
        "pages": {},            # url -> html for requests
        "rendered": {},         # url -> html for the browser
        "requests": [],
        "browser": [],
    }

    def fake_requests(url: str) -> str:
        state["requests"].append(url)
        page = state["pages"].get(url, listing_page(GAMING_ID))
        if isinstance(page, BaseException):
            raise page
        return page

    def fake_browser(url: str) -> str:
        state["browser"].append(url)
        page = state["rendered"].get(url, listing_page(GAMING_ID))
        if isinstance(page, BaseException):
            raise page
        return page

    monkeypatch.setattr(scraper_module, "_robots", state["robots"])
    monkeypatch.setattr(scraper_module, "_pace", lambda url: None)
    monkeypatch.setattr(scraper_module, "_fetch_with_requests", fake_requests)
    monkeypatch.setattr(scraper_module, "_fetch_with_playwright", fake_browser)
    monkeypatch.setattr(settings, "scraper_enable_playwright", True)
    monkeypatch.setattr(settings, "alibaba_max_search_queries", 3)
    return state


def _candidates(url: str) -> list[str]:
    return [listing_url(slug) for slug in search_slugs(parse_product_link(url).slug)]


def test_the_product_is_matched_by_id_on_the_first_listing(network: dict[str, Any]) -> None:
    first = _candidates(MOUSE_URL)[0]
    network["pages"][first] = listing_page(GAMING_ID, MOUSE_ID)

    product = scrape_alibaba_product(MOUSE_URL, "own")

    assert product.metadata["item_id"] == MOUSE_ID
    assert product.metadata["product_id"] == "own"
    assert product.metadata["matched_search"] == "mini-wireless-mouse-ergonomic-4-buttons"
    assert product.url == product.metadata["product_url"] == (
        "https://www.alibaba.com/product-detail/Mini-Wireless-Mouse-Ergonomic-4-Buttons_1601364965690.html"
    )
    assert product.method == "bs4"
    assert len(product.price_tiers) == 3 and product.supplier and len(product.images) == 6
    assert network["requests"] == [first]
    assert network["robots"].checked == [first]
    assert network["browser"] == []


def test_a_shorter_wording_is_tried_when_the_first_listing_lacks_the_product(network: dict[str, Any]) -> None:
    first, second = _candidates(MOUSE_URL)[:2]
    network["pages"][second] = listing_page(MOUSE_ID)

    product = scrape_alibaba_product(MOUSE_URL, "own")

    assert product.metadata["matched_search"] == "mini-wireless-mouse-ergonomic-4"
    assert network["requests"] == [first, second]


def test_a_product_on_no_listing_is_reported_plainly(network: dict[str, Any]) -> None:
    with pytest.raises(ScrapeError, match="could not be found on Alibaba's public wholesale listings"):
        scrape_alibaba_product(MOUSE_URL, "own")
    assert network["requests"] == _candidates(MOUSE_URL)[:3]


def test_the_number_of_searches_is_capped(network: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "alibaba_max_search_queries", 1)
    with pytest.raises(ScrapeError):
        scrape_alibaba_product(MOUSE_URL, "own")
    assert len(network["requests"]) == 1


def test_a_block_stops_the_search_and_is_never_retried_in_a_browser(network: dict[str, Any]) -> None:
    network["pages"][_candidates(MOUSE_URL)[0]] = CHALLENGE_HTML

    with pytest.raises(ScrapeError, match="does not bypass these checks"):
        scrape_alibaba_product(MOUSE_URL, "own")

    assert len(network["requests"]) == 1
    assert network["browser"] == []


def test_a_disallowed_listing_is_never_fetched(network: dict[str, Any]) -> None:
    first = _candidates(MOUSE_URL)[0]
    network["robots"].disallowed.add(first)

    with pytest.raises(ScrapeError, match="robots.txt does not allow"):
        scrape_alibaba_product(MOUSE_URL, "own")
    assert network["requests"] == [] and network["browser"] == []


def test_a_failed_request_falls_back_to_a_browser_render(network: dict[str, Any]) -> None:
    first = _candidates(MOUSE_URL)[0]
    network["pages"][first] = requests.ConnectionError("reset")
    network["rendered"][first] = listing_page(MOUSE_ID)

    product = scrape_alibaba_product(MOUSE_URL, "own")

    assert product.method == "playwright"
    assert network["browser"] == [first]
    assert any("trying a browser render" in warning for warning in product.warnings)


def test_a_page_without_products_is_rendered_once_in_a_browser(network: dict[str, Any]) -> None:
    first = _candidates(MOUSE_URL)[0]
    network["pages"][first] = "<html><body><div id='root'>Loading...</div></body></html>"
    network["rendered"][first] = listing_page(MOUSE_ID)

    assert scrape_alibaba_product(MOUSE_URL, "own").method == "bs4+playwright"


def test_without_the_browser_fallback_a_failed_request_is_an_error(
    network: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "scraper_enable_playwright", False)
    network["pages"][_candidates(MOUSE_URL)[0]] = requests.Timeout("slow")

    with pytest.raises(ScrapeError, match="browser fallback is disabled"):
        scrape_alibaba_product(MOUSE_URL, "own")
    assert network["browser"] == []


def test_a_link_without_a_title_cannot_be_searched(network: dict[str, Any]) -> None:
    with pytest.raises(ScrapeError, match="no product title"):
        scrape_alibaba_product("https://m.alibaba.com/product/1601364965690.html", "own")
    assert network["requests"] == []


# ----------------------------------------------------------- one HTTP fetch


@pytest.fixture
def http(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"responses": [], "sleeps": [], "robots": FakeRobots()}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        assert kwargs["headers"]["User-Agent"] == S.USER_AGENT
        response = state["responses"].pop(0)
        response.url = response.url or url
        return response

    monkeypatch.setattr(scraper_module.requests, "get", fake_get)
    monkeypatch.setattr(scraper_module.time, "sleep", lambda seconds: state["sleeps"].append(seconds))
    monkeypatch.setattr(scraper_module, "_pace", lambda url: None)
    monkeypatch.setattr(scraper_module, "_robots", state["robots"])
    return state


LISTING = "https://wholesaler.alibaba.com/w/wholesale-mini-wireless-mouse.html"


def test_one_polite_retry_after_a_rate_limit(http: dict[str, Any]) -> None:
    http["responses"] = [_Response(429), _Response(200, "<html>ok</html>")]
    assert scraper_module._fetch_with_requests(LISTING) == "<html>ok</html>"
    assert http["sleeps"] == [S.RATE_LIMIT_BACKOFF_SECONDS]


def test_a_second_rate_limit_gives_up(http: dict[str, Any]) -> None:
    http["responses"] = [_Response(503), _Response(429)]
    with pytest.raises(ScrapeError, match="rate limiting"):
        scraper_module._fetch_with_requests(LISTING)
    assert http["sleeps"] == [S.RATE_LIMIT_BACKOFF_SECONDS]


def test_a_refusal_is_not_worked_around(http: dict[str, Any]) -> None:
    http["responses"] = [_Response(403)]
    with pytest.raises(ScrapeError, match="refused the request"):
        scraper_module._fetch_with_requests(LISTING)
    assert http["sleeps"] == []


def test_a_redirect_somewhere_disallowed_is_not_read_or_retried_in_a_browser(
    http: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    redirected = "https://wholesaler.alibaba.com/w/wholesale-mini-wireless-mouse.html?from=redirect"
    http["robots"].disallowed.add(redirected)
    http["responses"] = [_Response(200, listing_page(MOUSE_ID), url=redirected)]
    browser_calls: list[str] = []
    monkeypatch.setattr(scraper_module, "_fetch_with_playwright", lambda url: browser_calls.append(url) or "")

    with pytest.raises(ScrapeError, match="robots.txt does not allow"):
        scrape_alibaba_product(MOUSE_URL, "own")
    assert browser_calls == []


# ================================================================== adapter


def test_the_adapter_presents_the_platform_contract(network: dict[str, Any]) -> None:
    network["pages"][_candidates(MOUSE_URL)[0]] = listing_page(MOUSE_ID)
    record = get_scraper("alibaba").scrape(MOUSE_URL, "own")

    assert (record.platform, record.role) == ("alibaba", "own")
    assert record.product_name.startswith("Mini 3D LED Wireless Mouse")
    assert [image["position"] for image in record.images] == [1, 2, 3, 4, 5, 6]
    assert {image["source"] for image in record.images} == {"gallery"}
    assert [tier["min_quantity"] for tier in record.price_tiers] == [100, 500, 1000]
    assert record.supplier and record.supplier["name"] == "Guangzhou Kingmega Electronic Firm"


def test_scrape_errors_surface_as_scraper_errors(network: dict[str, Any]) -> None:
    with pytest.raises(ScraperError, match="could not be found"):
        get_scraper("alibaba").scrape(MOUSE_URL, "own")


def test_one_identity_per_product_whatever_the_link_looks_like() -> None:
    scraper = get_scraper("alibaba")
    same = {
        scraper.canonical_url(MOUSE_URL),
        scraper.canonical_url("https://m.alibaba.com/product/1601364965690/Mini-Mouse.html"),
        scraper.canonical_url("https://www.alibaba.com/product-detail/Reworded-Title_1601364965690.html?spm=9"),
    }
    assert len(same) == 1
    assert scraper.canonical_url(GAMING_URL) not in same


def test_intake_validation_is_a_shape_check() -> None:
    scraper = get_scraper("alibaba")
    scraper.validate_url(MOUSE_URL)
    with pytest.raises(ScraperError, match="not an Alibaba domain"):
        scraper.validate_url("https://www.daraz.pk/products/hp-w10-i1957626953-s14018071159.html")


# ================================================================== metrics


def _meta(product_id: str) -> dict[str, Any]:
    return extract_offer(offer(product_id)).metadata


def _row(groups: list[dict[str, Any]], key: str, field: str) -> dict[str, Any]:
    group = next(group for group in groups if group["key"] == key)
    return next(row for row in group["metrics"] if row["field"] == field)


def test_ten_parameter_groups_a_to_j() -> None:
    groups = metrics.compare_all(_meta(MOUSE_ID), _meta(GAMING_ID))
    assert [group["letter"] for group in groups] == list("ABCDEFGHIJ")
    assert [group["key"] for group in groups][-2:] == ["order_terms", "supplier_credibility"]
    for group in groups:
        # Every searched field is one the scraper actually produces...
        assert set(group["semantic_field_types"]) <= set(TEXT_FIELD_TYPES)
        # ...and every group fits the API's response model.
        ComparisonGroup.model_validate(group)


def test_a_lower_minimum_order_wins_and_units_are_normalised() -> None:
    groups = metrics.compare_all(_meta(MOUSE_ID), _meta(GAMING_ID))
    moq = _row(groups, "order_terms", "moq")
    # 100 pieces vs 1 piece: "pieces" and "piece" are one unit, and lower is better.
    assert (moq["own"], moq["competitor"], moq["winner"]) == (100, 1, "competitor")
    assert moq["unit"] == "pieces"
    insights = " ".join(next(g for g in groups if g["key"] == "order_terms")["insights"])
    assert "minimum order is 1 vs your 100" in insights

    price = _row(groups, "pricing", "price")
    assert (price["winner"], price["unit"]) == ("own", "USD")


def test_supplier_credibility_compares_badges_and_track_record() -> None:
    groups = metrics.compare_all(_meta(MOUSE_ID), _meta(GAMING_ID))
    assert _row(groups, "supplier_credibility", "verified_supplier")["winner"] == "competitor"
    assert _row(groups, "supplier_credibility", "supplier_years")["winner"] == "competitor"
    assert _row(groups, "supplier_credibility", "gold_supplier")["winner"] == "tie"
    insights = " ".join(next(g for g in groups if g["key"] == "supplier_credibility")["insights"])
    assert "Verified supplier" in insights


def test_different_currencies_or_units_are_not_compared() -> None:
    own, rival = _meta(MOUSE_ID), _meta(GAMING_ID)
    rival.update(currency="EUR", moq_unit="boxes")
    groups = metrics.compare_all(own, rival)

    price = _row(groups, "pricing", "price")
    assert (price["winner"], price["unit"]) == (None, "USD vs EUR")
    assert _row(groups, "order_terms", "moq")["winner"] is None
    assert "different currencies" in " ".join(groups[0]["insights"])


def test_unpublished_fields_have_no_winner_and_identical_listings_only_tie() -> None:
    meta = _meta(MOUSE_ID)
    assert _row(metrics.compare_all(meta, _meta(GAMING_ID)), "variants", "variant_count")["winner"] is None
    assert all(
        row["winner"] in (None, "tie")
        for group in metrics.compare_all(meta, copy.deepcopy(meta))
        for row in group["metrics"]
    )


def test_derived_figures() -> None:
    meta = _meta(MOUSE_ID)
    # Cheapest way in: 100 pieces at the first tier's US$0.77.
    assert metrics.derived_for("order_terms", meta)["entry_order_value"] == 77.0
    assert metrics.derived_for("supplier_credibility", meta)["trust_badges"] == 2


def test_unit_key() -> None:
    assert unit_key("Pieces") == unit_key("piece") == "piece"
    assert unit_key("boxes") == unit_key("box") == "box"
    assert unit_key("batteries") == "battery"
    assert unit_key("glass") == "glass"


def test_quantity_units_are_labelled_in_the_plural() -> None:
    assert [plural_unit(u) for u in ("piece", "Pieces", "box", "units", "battery", "day", "glass", "pair")] == [
        "pieces", "pieces", "boxes", "units", "batteries", "days", "glasses", "pairs",
    ]
    # One label serves both sides, so "1 piece" vs "100 pieces" still reads "pieces".
    own, rival = _meta(GAMING_ID), _meta(MOUSE_ID)   # MOQ "1 piece" vs "100 pieces"
    assert _row(metrics.compare_all(own, rival), "order_terms", "moq")["unit"] == "pieces"
