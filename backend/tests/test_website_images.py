"""Which pictures a crawled page keeps, and which it throws away.

The collector runs on the markup *before* the cleaner strips it, so these tests
feed it the awkward parts of real pages: a header full of icons, a lazy-loading
srcset, a tracking pixel, an inline SVG logo and a data: URI.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.scrapers.website import selectors as S
from app.scrapers.website.cleaner import clean_html
from app.scrapers.website.images import collect

PAGE_URL = "https://verdantroast.test/shop"


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


RICH_PAGE = """
<html>
  <head>
    <meta property="og:image" content="/static/social-card.jpg">
  </head>
  <body>
    <header>
      <img src="/static/logo.svg" alt="Verdant Roast">
      <img src="/static/hero-beans.jpg" alt="Beans on a table" width="1200" height="600">
    </header>
    <main>
      <img src="/static/icons/cart.png" alt="">
      <img data-src="/static/roastery.jpg" alt="Our roastery">
      <img srcset="/static/bags-320.jpg 320w, /static/bags-1280.jpg 1280w" alt="Bags">
      <img src="data:image/gif;base64,R0lGOD" alt="">
      <img src="/static/pixel.gif" width="1" height="1" alt="">
      <img src="/static/team.jpg" style="width:400px;height:300px" alt="The team">
    </main>
  </body>
</html>
"""


def test_a_page_keeps_the_pictures_it_leads_with() -> None:
    images = collect(soup_of(RICH_PAGE), PAGE_URL)
    urls = [image["image_url"] for image in images]

    # The social card first: it is the image a site chose to represent itself.
    assert urls[0] == "https://verdantroast.test/static/social-card.jpg"
    assert images[0]["source"] == "og_image"
    assert images[0]["is_primary"] is True
    assert all(image["is_primary"] is False for image in images[1:])

    # Then the header's own picture, which the cleaner would otherwise discard.
    assert urls[1] == "https://verdantroast.test/static/hero-beans.jpg"
    assert images[1]["source"] == "hero"
    assert (images[1]["width"], images[1]["height"]) == (1200, 600)
    assert images[1]["alt_text"] == "Beans on a table"

    assert "https://verdantroast.test/static/roastery.jpg" in urls
    assert "https://verdantroast.test/static/team.jpg" in urls
    assert all(image["source"] in {"og_image", "hero", "content"} for image in images)


def test_chrome_is_not_a_picture_of_anything() -> None:
    urls = [image["image_url"] for image in collect(soup_of(RICH_PAGE), PAGE_URL)]

    assert not any("logo.svg" in url for url in urls)        # vector chrome
    assert not any("icons/cart" in url for url in urls)      # an icon
    assert not any(url.startswith("data:") for url in urls)  # inline data
    assert not any("pixel.gif" in url for url in urls)       # a 1x1 tracker


def test_a_responsive_image_is_stored_at_its_largest() -> None:
    urls = [image["image_url"] for image in collect(soup_of(RICH_PAGE), PAGE_URL)]
    assert "https://verdantroast.test/static/bags-1280.jpg" in urls
    assert "https://verdantroast.test/static/bags-320.jpg" not in urls


def test_the_same_picture_is_never_stored_twice() -> None:
    html = """
    <html><body>
      <header><img src="/a.jpg" alt="A"></header>
      <main><img src="/a.jpg" alt="A again"><img src="/b.jpg" alt="B"></main>
    </body></html>
    """
    images = collect(soup_of(html), PAGE_URL)
    assert [image["image_url"] for image in images] == [
        "https://verdantroast.test/a.jpg",
        "https://verdantroast.test/b.jpg",
    ]
    # The better label wins: it was found in the header first.
    assert images[0]["source"] == "hero"


def test_a_page_of_nothing_but_chrome_yields_nothing() -> None:
    html = "<html><body><img src='/logo.png'><img src='/icons/x.png'></body></html>"
    assert collect(soup_of(html), PAGE_URL) == []


def test_a_gallery_is_capped() -> None:
    tags = "".join(f"<img src='/photo-{index}.jpg' alt='{index}'>" for index in range(40))
    images = collect(soup_of(f"<html><body><main>{tags}</main></body></html>"), PAGE_URL)
    assert len(images) == S.MAX_IMAGES_PER_PAGE


def test_the_cleaner_hands_the_images_on_with_the_text() -> None:
    """The crawler reads a page once; images ride along with everything else."""
    page = clean_html(PAGE_URL, RICH_PAGE)

    assert page.images, "the page's pictures should survive the strip"
    assert page.images[0]["image_url"].endswith("social-card.jpg")
    # And the stripping still happened: the header is not in the text.
    assert "Verdant Roast" not in page.cleaned_text
