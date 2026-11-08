"""
ALL Alibaba-specific extraction rules live in this file.

How Alibaba data is collected, and why (measured 2026-09-11):

  * www.alibaba.com/product-detail/... pages -- the links users paste -- answer
    both plain HTTP and a headless browser with a CAPTCHA verification page.
    Getting past that would mean defeating the protection, which this scraper
    never does. Detail pages are therefore not fetched at all.
  * wholesaler.alibaba.com/w/wholesale-<keyword>.html listing pages are allowed
    by robots.txt, need no browser, answer an honestly identified client, and
    embed every listed product as JSON in `window._PAGE_DATA_`.

So a pasted product link is resolved to its listing record: the product id and
title words are read from the link, the permitted listing is searched with
those words, and the record whose id matches is used.

When Alibaba changes its markup or JSON shape, edit THIS FILE ONLY.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Where products live
# ---------------------------------------------------------------------------
LISTING_HOST = "wholesaler.alibaba.com"
# robots.txt on this host has `Disallow: /*?`, so listing URLs must never carry
# a query string. There is no permitted pagination: page 2+ lives only under
# retired /showroom/ paths (HTTP 410), so every search reads page 1.
LISTING_URL_TEMPLATE = "https://wholesaler.alibaba.com/w/wholesale-{slug}.html"

CANONICAL_PRODUCT_URL = "https://www.alibaba.com/product-detail/{slug}_{product_id}.html"

# Hosts a product link may be on.
ALLOWED_HOST_SUFFIX = "alibaba.com"

# Product link shapes. Desktop: /product-detail/<Title-Slug>_<id>.html
# Mobile:  /product/<id>/<Title-Slug>.html  (slug optional)
PRODUCT_URL_PATTERNS = [
    r"^/product-detail/(?P<slug>[^/]*?)_(?P<id>\d{6,})\.html$",
    r"^/product/(?P<id>\d{6,})(?:/(?P<slug>[^/]+?))?(?:\.html)?/?$",
]

# ---------------------------------------------------------------------------
# 2. Searching the listing for one product
# ---------------------------------------------------------------------------
# Different wordings of the title surface different page-1 result sets. Tried
# in order until the product id turns up. Word counts are upper bounds; a
# shorter title simply yields fewer variants.
SEARCH_WORD_LIMITS = [8, 5, 3]
# Title words too generic to help a search, dropped when shortening.
SEARCH_STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "of", "in", "on", "to", "by", "new",
    "hot", "sale", "selling", "best", "high", "quality", "factory", "wholesale",
    "cheap", "price", "custom", "customized", "oem", "odm", "logo", "2024", "2025",
    "2026",
}

# ---------------------------------------------------------------------------
# 3. The embedded JSON
# ---------------------------------------------------------------------------
PAGE_DATA_MARKER = "window._PAGE_DATA_"
# page_data["offerResultData"]["itemInfoList"][i]["offer"]
OFFER_LIST_PATH = ("offerResultData", "itemInfoList")
OFFER_KEY = "offer"

# Dotted paths inside one offer object. First non-empty wins.
OFFER_PATHS = {
    "id": ["id", "information.id"],
    "title": ["information.enPureTitle", "information.puretitle", "information.title"],
    "product_url": ["information.productUrl"],
    "currency": ["information.productTransferModel.moneyCurrency"],
    "price_min": ["promotionInfoVO.originalPriceFrom", "price", "lowerPrice"],
    "price_max": ["promotionInfoVO.originalPriceTo", "upperPrice"],
    "price_label": ["tradePrice.price", "promotionInfoVO.localOriginalPriceRangeStr"],
    "price_unit": ["tradePrice.unit"],
    # The published quantity ladder, at list (pre-promotion) prices.
    "quantity_prices": ["promotionInfoVO.quantityPrices"],
    # During a promotion the list range stays in originalPriceFrom/To (and in
    # the top-level `price`), and the live range is promotionPriceFrom/To.
    "promotion_active": ["promotionInfoVO.showPromotion"],
    "promotion_price_min": ["promotionInfoVO.promotionPriceFrom"],
    "promotion_price_max": ["promotionInfoVO.promotionPriceTo"],
    "promotion_discount": ["promotionInfoVO.promotionDiscount"],
    "list_price_min": ["promotionInfoVO.originalPriceFrom"],
    "list_price_max": ["promotionInfoVO.originalPriceTo"],
    "moq_label": ["tradePrice.minOrder"],
    "moq_number": ["information.productTransferModel.minOrderQuality"],
    "dispatch_label": ["freightInfo.dispatchLabel"],
    "process_days": ["information.minProcessPeriod", "information.productTransferModel.moqDispatchPeroid"],
    "buy_now": ["information.productTransferModel.buyNowValid"],
    "sponsored": ["information.p4p"],
    "item_type": ["information.itemType"],
    "category_id": ["information.postCategoryId"],
    "images": ["image.multiImage"],
    "big_image": ["image.bigImage", "image.productImage", "image.mainImage"],
    "has_video": ["image.video"],
    "review_count": ["reviews.reviewCount"],
    "review_score": ["reviews.reviewScore", "reviews.productScore"],
    "attributes": ["features.productAttribute"],
    "promotion_tags": ["tag.promotionTag"],
    "supplier_name": ["supplier.supplierName"],
    "supplier_country": ["supplier.supplierCountry.name"],
    "supplier_country_code": ["supplier.supplierCountry.id"],
    "supplier_years": ["supplier.supplierYear"],
    "gold_supplier": ["supplier.goldSupplier"],
    "verified_supplier": ["supplier.assessedSupplier"],
    "main_products": ["supplier.provideProducts"],
    "trade_assurance": ["company.tradeAssurance"],
    "transaction_level": ["company.transactionLevel"],
    "response_rate": ["company.record.responseRate"],
    "historic_order_count": ["company.supplierHistoryOrderCount"],
    "historic_gmv": ["company.supplierHistoryGmv"],
}

# Never read, never stored: supplier contact routes, chat tokens, click-tracking
# and encrypted identifiers. A test asserts none of these reach the output.
PRIVATE_OFFER_KEYS = {"aliTalk", "trackInfo", "extra"}
PRIVATE_VALUE_HINTS = [
    "message.alibaba.com", "contactSupplier", "chatToken", "us-click.alibaba.com",
    "encryptId", "encryptSupplierId", "selection.alibaba.com",
]

# Attribute names that carry a brand.
BRAND_ATTRIBUTE_NAMES = {"brand name", "brand"}
GENERIC_BRANDS = {"", "no brand", "nobrand", "generic", "oem", "odm", "customized", "custom"}

PROMOTION_TAG_READY_TO_SHIP = "ready to ship"

# Customisation offered to a buyer: OEM/ODM production, own logo, own packaging.
CUSTOMIZATION_KEYWORDS = [
    "oem", "odm", "custom logo", "customized logo", "customised logo", "private label",
    "customizable", "customized", "customised", "custom packaging", "own logo", "your logo",
]

TITLE_STOPWORDS = {
    "the", "and", "for", "with", "of", "in", "on", "to", "a", "an", "by", "from", "at",
    "new", "hot", "sale", "best", "high", "quality", "piece", "pieces", "pcs", "set",
}

# ---------------------------------------------------------------------------
# 4. Images
# ---------------------------------------------------------------------------
# Alibaba serves resized copies by suffixing the original filename:
#     .../Hfdceac...b1b.jpg_300x300.jpg
#     .../Hfdceac...b1b.jpg_220x220.jpg_.webp
# Stripping the suffix gives the original upload.
IMAGE_RESIZE_SUFFIX = r"(\.(?:jpe?g|png|webp|gif))_\d+x\d+(?:q\d+)?\.(?:jpe?g|png|webp)(?:_\.webp)?$"
IMAGE_MAX_PER_PRODUCT = 20

# ---------------------------------------------------------------------------
# 5. Detecting an anti-bot page (never solved -- only recognised)
# ---------------------------------------------------------------------------
# Only consulted when a page has no product JSON: normal listing pages mention
# "captcha" in their scripts, so a marker alone is not proof of a block.
CHALLENGE_PATTERNS = [
    r"/punish[/?]",
    r"punish_(?:page|config)",
    r"\bx5secdata\b",
    r"\bnocaptcha\b",
    r"\bslide\s+to\s+verify\b",
    r"\bverify\s+to\s+continue\b",
    r"captcha[_-]?(?:container|widget|challenge)",
    r"baxia[_-]?dialog",
    r"<title>\s*captcha verification\s*</title>",
]
BLOCKED_STATUS_CODES = {403, 405, 511}
RATE_LIMIT_STATUS_CODES = {429, 503}

# ---------------------------------------------------------------------------
# 6. Requests
# ---------------------------------------------------------------------------
# Identifies the client honestly; verified to receive full listing data.
USER_AGENT = "OptiStratixAI-Scout/1.0 (+https://github.com/OptiStratix-AI/Development)"
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
# The browser fallback waits this long for the embedded JSON to appear.
PLAYWRIGHT_PAGE_DATA_TIMEOUT_MS = 20000
# One polite retry after a rate-limit answer, then stop.
RATE_LIMIT_BACKOFF_SECONDS = 8.0
