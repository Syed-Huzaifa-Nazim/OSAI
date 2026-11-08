"""Product image extraction for Daraz listings.

Built from markup shaped like real Daraz pages (captured September 2026): the
gallery in the inline module blob keyed by SKU, JSON-LD image arrays, resized
thumbnails in <img> tags, and lazy-loading attributes.
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from app.scrapers.daraz.images import (
    SOURCE_GALLERY,
    SOURCE_OG_IMAGE,
    SOURCE_PAGE,
    count_videos,
    extract_product_images,
    image_identity,
    normalise_image_url,
)
from app.scrapers.daraz.scraper import _parse_page

HP_1 = "https://static-01.daraz.pk/p/f339d9f6f5a0ccb8d90a48271c5de627.jpg"
HP_2 = "https://static-01.daraz.pk/p/fab471e49ed97872aca29120b1f9c2b8.jpg"
HP_3 = "https://static-01.daraz.pk/p/29ca569b80af4c2e6cb311dd007cdea3.jpg"


def _extract(html: str, module: dict | None = None, jsonld: dict | None = None):
    return extract_product_images(BeautifulSoup(html, "lxml"), module or {}, jsonld or {})


# --------------------------------------------------------------- normalising


def test_resize_suffix_is_stripped_to_the_original_file() -> None:
    thumb = "https://img.drz.lazcdn.com/static/pk/p/f339d9f6f5a0ccb8d90a48271c5de627.jpg_120x120q80.jpg_.webp"
    assert normalise_image_url(thumb) == (
        "https://img.drz.lazcdn.com/static/pk/p/f339d9f6f5a0ccb8d90a48271c5de627.jpg"
    )
    assert normalise_image_url(HP_1 + "_720x720q80.jpg_.webp") == HP_1
    assert normalise_image_url(HP_1 + "_2200x2200q80.jpg") == HP_1


def test_protocol_relative_links_get_a_scheme() -> None:
    assert normalise_image_url("//static-01.daraz.pk/p/abc.jpg") == "https://static-01.daraz.pk/p/abc.jpg"


def test_query_strings_are_dropped() -> None:
    assert normalise_image_url(HP_1 + "?x-oss-process=resize") == HP_1


def test_placeholders_and_non_images_are_rejected() -> None:
    for bad in (
        None,
        "",
        "data:image/gif;base64,R0lGODlhAQABAAAAACw=",
        "https://g.lazcdn.com/g/tps/blank.gif",
        "https://www.daraz.pk/products/x.html",
        "/relative/path.jpg",
        12345,
    ):
        assert normalise_image_url(bad) is None, bad


def test_the_same_photo_on_two_hosts_has_one_identity() -> None:
    assert image_identity(HP_1) == image_identity(
        "https://img.drz.lazcdn.com/static/pk/p/f339d9f6f5a0ccb8d90a48271c5de627.jpg"
    )


# ------------------------------------------------------------------ gallery


def test_gallery_across_skus_is_deduplicated_in_order() -> None:
    """Real shape: the listing gallery under "0", repeated under each SKU id."""
    gallery = [
        {"itemLevel": True, "type": "img", "src": HP_1, "poster": HP_1},
        {"itemLevel": True, "type": "img", "src": HP_2, "poster": HP_2},
        {"itemLevel": False, "type": "img", "src": HP_1, "poster": HP_1},
    ]
    module = {"skuGalleries": {"14018071159": gallery + [{"type": "img", "src": HP_3}], "0": gallery}}

    images = _extract("<html></html>", module)

    # "0" first, SKU photos after; the duplicate and the second SKU copy drop out.
    assert [image.url for image in images] == [HP_1, HP_2, HP_3]
    assert {image.source for image in images} == {SOURCE_GALLERY}


def test_videos_are_not_images() -> None:
    module = {"skuGalleries": {"0": [
        {"type": "video", "src": "https://cloud.video.daraz.pk/v.mp4", "poster": HP_2},
        {"type": "img", "src": HP_1},
    ]}}
    assert [image.url for image in _extract("", module)] == [HP_1]
    assert count_videos(module) == 1


def test_structured_data_adds_what_the_gallery_missed() -> None:
    module = {"skuGalleries": {"0": [{"type": "img", "src": HP_1}]}}
    jsonld = {"@type": "Product", "image": [HP_1, HP_2]}
    assert [image.url for image in _extract("", module, jsonld)] == [HP_1, HP_2]


def test_structured_data_image_can_be_a_single_string() -> None:
    assert [image.url for image in _extract("", {}, {"image": HP_1})] == [HP_1]


# --------------------------------------------------------- page <img> tags


def test_page_images_are_only_a_fallback() -> None:
    """With a known gallery, a stray thumbnail on the page is not added."""
    html = f'<img class="item-gallery__thumbnail-image" src="{HP_3}_120x120q80.jpg_.webp">'
    module = {"skuGalleries": {"0": [{"type": "img", "src": HP_1}]}}
    assert [image.url for image in _extract(html, module)] == [HP_1]


def test_page_thumbnails_resolve_to_full_resolution() -> None:
    html = f"""
      <img class="pdp-mod-common-image gallery-preview-panel__image" src="{HP_1}_720x720q80.jpg_.webp">
      <img class="pdp-mod-common-image item-gallery__thumbnail-image" src="{HP_1}_120x120q80.jpg_.webp">
      <img class="pdp-mod-common-image item-gallery__thumbnail-image" src="{HP_2}_120x120q80.jpg_.webp">
    """
    images = _extract(html)
    assert [image.url for image in images] == [HP_1, HP_2]
    assert {image.source for image in images} == {SOURCE_PAGE}


def test_lazy_loaded_image_uses_its_real_url_not_the_placeholder() -> None:
    html = f"""
      <img class="item-gallery__thumbnail-image"
           src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" data-src="{HP_1}_120x120q80.jpg_.webp">
      <img class="item-gallery__thumbnail-image"
           src="https://g.lazcdn.com/g/tps/blank.gif" data-ks-lazyload="//static-01.daraz.pk/p/fab471e49ed97872aca29120b1f9c2b8.jpg">
    """
    assert [image.url for image in _extract(html)] == [HP_1, HP_2]


def test_srcset_uses_the_largest_candidate() -> None:
    html = f"""<img class="item-gallery__thumbnail-image"
        srcset="{HP_1}_120x120q80.jpg_.webp 120w, {HP_2}_720x720q80.jpg_.webp 720w">"""
    assert [image.url for image in _extract(html)] == [HP_2]


def test_og_image_is_the_last_resort() -> None:
    html = f'<meta property="og:image" content="{HP_1}_720x720q80.jpg_.webp">'
    images = _extract(html)
    assert [(image.url, image.source) for image in images] == [(HP_1, SOURCE_OG_IMAGE)]


def test_a_page_without_images_yields_an_empty_list() -> None:
    assert _extract("<html><body><h1>No photos here</h1></body></html>") == []


def test_malformed_gallery_data_does_not_raise() -> None:
    for module in (
        {"skuGalleries": "not a dict"},
        {"skuGalleries": {"0": "not a list"}},
        {"skuGalleries": {"0": [None, 7, {"type": "img"}, {"type": "img", "src": 42}]}},
        {"skuGalleries": None},
    ):
        assert _extract("", module) == []


def test_a_gallery_is_capped() -> None:
    module = {"skuGalleries": {"0": [
        {"type": "img", "src": f"https://static-01.daraz.pk/p/{index:032x}.jpg"} for index in range(50)
    ]}}
    assert len(_extract("", module)) == 20


# ----------------------------------------------------- inside the scraper


def _page(module: dict, jsonld: dict | None = None, body: str = "") -> str:
    """A minimal product page with the inline blob the scraper parses."""
    jsonld_tag = (
        f'<script type="application/ld+json">{json.dumps(jsonld)}</script>' if jsonld else ""
    )
    # Real blobs carry several top-level modules; the scraper only accepts a
    # root with more than one key, so the fixture includes a second one.
    fields = {"product": {"title": "HP W10 Wireless Mouse"}, **module}
    return f"""<html><head>{jsonld_tag}</head><body>
      <h1>HP W10 Wireless Mouse</h1>{body}
      <script>var __moduleData__ = {json.dumps({"data": {"root": {"fields": fields}}})};</script>
    </body></html>"""


def test_the_scraper_collects_images_in_the_same_pass() -> None:
    module = {"skuGalleries": {"0": [
        {"type": "img", "src": HP_1},
        {"type": "img", "src": HP_2},
        {"type": "img", "src": HP_1},
    ]}}
    product = _parse_page(_page(module), "https://www.daraz.pk/products/hp-i1-s1.html", "own")

    assert [image.url for image in product.images] == [HP_1, HP_2]
    # Counted from the distinct photos, not the three gallery entries.
    assert product.metadata["image_count"] == 2


def test_extraction_failure_costs_the_images_not_the_listing(monkeypatch) -> None:
    import app.scrapers.daraz.scraper as scraper_module

    def explode(*args, **kwargs):
        raise RuntimeError("markup changed")

    monkeypatch.setattr(scraper_module, "extract_product_images", explode)
    product = _parse_page(_page({}), "https://www.daraz.pk/products/hp-i1-s1.html", "own")

    assert product.images == []
    assert product.text_fields["title"]  # everything else still extracted
    assert any("images could not be read" in warning for warning in product.warnings)
