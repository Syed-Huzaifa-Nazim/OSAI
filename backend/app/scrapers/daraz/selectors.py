"""
ALL Daraz-specific extraction rules live in this file.

Daraz runs the Lazada PDP engine. The page ships a large JSON blob inside an
inline <script> tag; that blob is far more stable than the CSS class names
(which are hashed and change often). So extraction is layered:

    1. JSON blob  (JSON_BLOB_PATTERNS -> JSON_PATHS)
    2. CSS selectors on rendered DOM  (CSS)
    3. Regex over raw page text  (TEXT_PATTERNS)

When Daraz changes its markup, edit THIS FILE ONLY.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Inline-JSON blob discovery
# ---------------------------------------------------------------------------
# Each entry is a regex whose group(1) starts a JSON object literal. The brace
# matcher in daraz.py walks from that opening brace to its real closing brace,
# so the patterns intentionally stop at the first "{".
JSON_BLOB_PATTERNS = [
    r"var\s+__moduleData__\s*=\s*(\{)",
    r"window\.__moduleData__\s*=\s*(\{)",
    r"window\.__INITIAL_STATE__\s*=\s*(\{)",
    r"window\.pageData\s*=\s*(\{)",
    r"app\.run\(\s*(\{)",
]

# JSON-LD is a useful secondary source (schema.org/Product).
JSONLD_SELECTOR = 'script[type="application/ld+json"]'

# ---------------------------------------------------------------------------
# 2. Paths inside the module-data blob.
#    Each field maps to a list of candidate dotted paths, tried in order.
# ---------------------------------------------------------------------------
MODULE_DATA_ROOTS = [
    "data.root.fields",
    "data.root",
    "data",
    "root.fields",
    "root",
]

JSON_PATHS = {
    "title": [
        "product.title",
        "product.name",
        "skuInfos.0.0.title",
        "pdp.title",
    ],
    "brand": [
        "product.brand.name",
        "product.brand.title",
        "brand.name",
        "brand.title",
    ],
    "item_id": [
        "product.itemId",
        "product.id",
        "tracking.itemId",
        "pdp.itemId",
    ],
    "seller_id": [
        "seller.sellerId",
        "seller.id",
        "product.sellerId",
    ],
    "seller_name": [
        "seller.name",
        "seller.sellerName",
        "seller.title",
    ],
    "seller_rating_raw": [
        "seller.sellerRating",
        "seller.positiveRate",
        "seller.rating",
        "seller.sellerInfo.positiveRate",
    ],
    "seller_verified": [
        "seller.verified",
        "seller.isVerified",
        "seller.officialStore",
        "seller.badge",
    ],
    "price_now": [
        "skuInfos.0.0.price.salePrice.value",
        "skuInfos.0.0.price.salePrice.text",
        "price.salePrice.value",
        "price.salePrice.text",
        "product.price.salePrice.value",
    ],
    "price_was": [
        "skuInfos.0.0.price.originalPrice.value",
        "skuInfos.0.0.price.originalPrice.text",
        "price.originalPrice.value",
        "price.originalPrice.text",
    ],
    "discount_raw": [
        "skuInfos.0.0.price.discount",
        "skuInfos.0.0.price.discountText",
        "price.discount",
        "price.discountText",
    ],
    "stock_raw": [
        "skuInfos.0.0.stock",
        "skuInfos.0.0.quantity",
        "product.stock",
        "stock",
    ],
    "rating_raw": [
        "review.ratings.average",
        "review.averageRating",
        "reviews.ratings.average",
        "product.rating.average",
    ],
    "review_count_raw": [
        "review.ratings.total",
        "review.reviewCount",
        "reviews.ratings.total",
        "product.rating.reviewCount",
    ],
    "qa_count_raw": [
        "questionAndAnswer.total",
        "qa.total",
        "questions.total",
    ],
    "description_html": [
        "productDesc.html",
        "description.html",
        "product.desc",
        "product.description",
        "detail.description",
    ],
    "highlights_html": [
        "productDesc.highlights",
        "product.highlights",
        "highlights",
    ],
    "specs_raw": [
        "specifications",
        "productDesc.specifications",
        "product.specifications",
        "specification",
    ],
    "images_raw": [
        "skuInfos.0.0.images",
        "product.images",
        "gallery.images",
        "images",
    ],
    "video_raw": [
        "skuInfos.0.0.video",
        "product.video",
        "gallery.video",
        "video",
    ],
    "breadcrumb_raw": [
        "breadcrumb",
        "navigation.breadcrumb",
        "product.breadcrumb",
    ],
    "variants_raw": [
        "skuBase.props",
        "skuBase.skus",
        "product.variations",
        "variations",
    ],
    "delivery_raw": [
        "deliveryOptions",
        "delivery.deliveryOptions",
        "shipping.deliveryOptions",
        "delivery",
    ],
    "warranty_raw": [
        "warranty",
        "warrantyOptions",
        "service.warranty",
        "services",
    ],
    "promotions_raw": [
        "promotions",
        "voucher",
        "vouchers",
        "activity",
        "bundleDeals",
    ],
}

# ---------------------------------------------------------------------------
# 3. CSS selectors (rendered DOM / Playwright path). First match wins.
# ---------------------------------------------------------------------------
CSS = {
    "title": [
        "h1.pdp-mod-product-badge-title",
        ".pdp-product-title",
        'h1[class*="product-badge-title"]',
        "h1.pdp-title",
        "h1",
    ],
    "price_now": [
        ".pdp-price_type_normal",
        ".pdp-price_color_orange",
        'span[class*="pdp-price_type_normal"]',
        ".pdp-product-price .pdp-price",
    ],
    "price_was": [
        ".pdp-price_type_deleted",
        'span[class*="pdp-price_type_deleted"]',
        "del.pdp-price",
    ],
    "discount": [
        ".pdp-product-price__discount",
        'span[class*="product-price__discount"]',
    ],
    "brand": [
        ".pdp-product-brand__brand-link",
        'a[class*="brand-link"]',
        ".pdp-product-brand a",
    ],
    "rating": [
        ".score-average",
        'div[class*="score-average"]',
    ],
    "review_count": [
        ".pdp-review-summary__link",
        'a[class*="review-summary__link"]',
        ".count",
    ],
    "qa_count": [
        ".pdp-qa__header-count",
        'div[class*="qa"] [class*="count"]',
    ],
    "description": [
        ".html-content.pdp-product-highlights",
        "#module_product_detail .html-content",
        ".pdp-product-desc",
        'div[class*="product-detail"] .html-content',
        "#product-details",
    ],
    "specs": [
        ".pdp-general-features",
        ".specification-keys",
        "#module_product_specification",
        ".pdp-mod-specification",
    ],
    "images": [
        ".item-gallery__thumbnail-image",
        ".gallery-preview-panel__image",
        'img[class*="gallery"]',
        ".pdp-mod-common-image",
    ],
    "video": [
        "video",
        ".gallery-preview-panel__video",
        'div[class*="video-thumbnail"]',
    ],
    "breadcrumb": [
        ".breadcrumb_item_anchor",
        ".breadcrumb a",
        'ul[class*="breadcrumb"] a',
        'nav[aria-label="breadcrumb"] a',
    ],
    "stock": [
        ".quantity-content-default",
        'div[class*="stock"]',
    ],
    "delivery": [
        ".delivery-option-item__time",
        ".delivery__option",
        'div[class*="delivery-option"] [class*="time"]',
        'div[class*="delivery-option"]',
        "#module_seller_delivery",
        '[class*="delivery-detail"]',
    ],
    "shipping_fee": [
        ".delivery-option-item__shipping-fee",
        'span[class*="shipping-fee"]',
    ],
    "return_policy": [
        ".delivery-option-item__title",
        ".pdp-mod-return-policy",
        'div[class*="return"]',
    ],
    "warranty": [
        ".warranty-list",
        'div[class*="warranty"]',
        ".pdp-mod-warranty",
    ],
    "seller_name": [
        ".seller-name__detail-name",
        'a[class*="seller-name"]',
        ".pdp-mod-seller-name",
        "#module_seller_brief .seller-name__detail",
        '#module_seller_brief a[href*="/shop/"]',
        'a[href*="/shop/"]',
        '[class*="seller-container"] [class*="detail-name"]',
    ],
    "seller_rating": [
        ".seller-info-value.rating-positive",
        'div[class*="rating-positive"]',
        ".seller-info-value",
    ],
    "seller_badge": [
        ".pdp-seller-badge",
        'img[class*="seller-badge"]',
        ".seller-verified",
    ],
    "promo_tags": [
        ".pdp-product-price__promotion",
        ".voucher-tag",
        'div[class*="promotion"]',
        'span[class*="badge"]',
        ".pdp-mod-promotion",
    ],
    "variants": [
        ".sku-prop-content .sku-variable-img-wrap",
        ".sku-prop-content-header .sku-variable-name",
        ".sku-selector .sku-prop-content > span",
        'div[class*="sku-prop"] [class*="sku-variable"]',
    ],
    "variant_groups": [
        ".sku-prop",
        'div[class*="sku-prop-title"]',
    ],
    "size_chart": [
        ".pdp-size-chart",
        'a[class*="size-chart"]',
        'div[class*="size-guide"]',
    ],
    "reviews": [
        ".review-content .content",
        ".mod-reviews .item .content",
        'div[class*="review"] div[class*="content"]',
    ],
}

# ---------------------------------------------------------------------------
# 4. Regex fallbacks over raw text
# ---------------------------------------------------------------------------
TEXT_PATTERNS = {
    "price": r"(?:Rs\.?|PKR)\s*([\d,]+(?:\.\d+)?)",
    "discount": r"(-?\s*\d{1,3})\s*%\s*(?:OFF|off)",
    "rating": r"([0-5](?:\.\d)?)\s*(?:out of 5|/\s*5)",
    "review_count": r"([\d,]+)\s*(?:Ratings?|Reviews?)",
    "qa_count": r"(?:Questions about this product|Q.A)\D{0,20}(\d+)",
    "delivery_days": r"(\d+\s*-\s*\d+\s*(?:days?|working days?)|\d+\s*(?:days?|working days?))",
    "warranty": r"(\d+\s*(?:Year|Month|Day)s?\s*(?:Brand|Local|Seller|International|Manufacturer)?\s*Warranty|No Warranty|Warranty not available)",
    "item_id_query": r"[?&]itemId=(\d+)",
    "item_id_path": r"-i(\d+)(?:-s\d+)?\.html",
    "seller_id_query": r"[?&]sellerId=(\d+)",
    "seller_id_path": r"-s(\d+)\.html",
}

# ---------------------------------------------------------------------------
# 5. Keyword banks used for boolean / classification metadata
# ---------------------------------------------------------------------------
BESTSELLER_KEYWORDS = [
    "best seller", "bestseller", "top seller", "trending", "hot sale",
    "most popular", "top rated", "daraz choice",
]

BUNDLE_KEYWORDS = [
    "bundle", "combo", "pack of", "buy 1 get", "buy one get", "2 in 1",
    "3 in 1", "set of", "bogo", "value pack", "multipack",
]

FLASH_SALE_KEYWORDS = [
    "flash sale", "flash deal", "lightning deal", "mega sale", "daraz sale",
    "limited time", "deal of the day", "clearance",
]

COUPON_KEYWORDS = ["voucher", "coupon", "collect voucher", "promo code", "discount code"]

FREE_SHIPPING_KEYWORDS = ["free shipping", "free delivery", "shipping: free"]

OUT_OF_STOCK_KEYWORDS = ["out of stock", "sold out", "currently unavailable", "not available"]

LIMITED_STOCK_KEYWORDS = ["left in stock", "few left", "low stock", "almost gone", "pieces left"]

CUSTOMIZABLE_KEYWORDS = [
    "custom", "customiz", "customis", "personaliz", "personalis",
    "made to order", "engrav", "your name", "monogram",
]

SIZE_CHART_KEYWORDS = ["size chart", "size guide", "measurement", "sizing", "dimension chart"]

VERIFIED_SELLER_KEYWORDS = ["daraz mall", "official store", "verified", "authorized", "trusted"]

RETURN_POLICY_KEYWORDS = [
    "return", "refund", "money back", "7 days", "14 days", "warranty",
    "change of mind", "replacement",
]

POSITIVE_REVIEW_WORDS = [
    "good", "great", "excellent", "amazing", "perfect", "love", "best",
    "quality", "fast", "recommend", "satisfied", "worth", "genuine",
    "original", "nice", "happy", "awesome", "value",
]

NEGATIVE_REVIEW_WORDS = [
    "bad", "poor", "worst", "fake", "broken", "damaged", "late", "slow",
    "defective", "cheap", "waste", "disappointed", "wrong",
    "refund", "scam", "useless", "torn",
]

# Words ignored when computing title keyword density.
TITLE_STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "with", "of", "in", "on", "to",
    "by", "at", "is", "it", "this", "that", "from", "new", "pcs", "pc",
}

# Units used to detect quantity-based products for price-per-unit.
QUANTITY_PATTERNS = [
    r"pack\s*of\s*(\d+)",
    r"set\s*of\s*(\d+)",
    r"(\d+)\s*pcs?\b",
    r"(\d+)\s*pieces?\b",
    r"(\d+)\s*x\b",
]

# ---------------------------------------------------------------------------
# 6. Networking
# ---------------------------------------------------------------------------
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

# Daraz serves reviews from a JSON endpoint rather than in the PDP HTML.
REVIEW_API_TEMPLATE = (
    "https://my.daraz.pk/pdp/review/getReviewList"
    "?itemId={item_id}&pageSize=20&filter=0&sort=0&pageNo={page}"
)

# Playwright waits for one of these before reading the DOM.
PLAYWRIGHT_WAIT_SELECTORS = [
    ".pdp-mod-product-badge-title",
    ".pdp-price",
    "h1",
]

PLAYWRIGHT_SCROLL_STEPS = 6
PLAYWRIGHT_SETTLE_MS = 1200

# How long to wait for the price block to hydrate. The title is server-rendered
# and appears immediately; the price is the slow one and is what we require.
PLAYWRIGHT_PRICE_TIMEOUT_MS = 20000

# Lazy-loaded modules that only render once scrolled into view. Playwright
# nudges each of these into the viewport before reading the DOM.
PLAYWRIGHT_LAZY_MODULES = [
    "#module_product_detail",
    "#module_product_specification",
    ".mod-reviews",
    "#module_review",
    '[class*="pdp-mod-review"]',
    "#module_seller_brief",
]

ALLOWED_HOST_FRAGMENTS = ["daraz."]

# ---------------------------------------------------------------------------
# Product images
# ---------------------------------------------------------------------------
# Where the gallery lives in the inline module-data blob. Keyed by SKU id, plus
# "0" for the listing itself; each entry is {"type": "img"|"video", "src",
# "poster", "itemLevel"}. Present in the server HTML, so no browser is needed.
# (JSON_PATHS["images_raw"] above predates this layout and no longer matches.)
IMAGE_GALLERY_PATHS = [
    "skuGalleries",
]
IMAGE_GALLERY_ENTRY_KEYS = ["src", "poster", "image", "url"]
# Gallery entry types that are pictures. Videos are counted separately.
IMAGE_GALLERY_TYPES = {"img", "image"}

# Attributes a lazy-loading <img> keeps its real URL in, most specific first.
# A lazy image's plain `src` is often a spacer, so these win over it.
IMAGE_LAZY_ATTRIBUTES = [
    "data-src",
    "data-ks-lazyload",
    "data-lazy-src",
    "data-original",
    "data-lazyload",
]
IMAGE_SRCSET_ATTRIBUTES = ["data-srcset", "srcset"]

# Daraz serves resized copies by appending a size to the original filename:
#     .../abc.jpg_120x120q80.jpg_.webp   (thumbnail)
#     .../abc.jpg_720x720q80.jpg_.webp   (preview)
# Stripping the suffix gives the original, full-resolution file.
IMAGE_RESIZE_SUFFIX = r"(\.(?:jpe?g|png|webp|gif))_\d+x\d+(?:q\d+)?\.(?:jpe?g|png|webp)(?:_\.webp)?$"

# Anything whose URL contains one of these is a placeholder, not a product photo.
IMAGE_PLACEHOLDER_HINTS = [
    "data:image",
    "blank.gif",
    "spacer",
    "placeholder",
    "lazy.png",
    "1x1",
]

# Upper bound per listing. Real galleries run 1-9 images; the cap only stops a
# page whose markup changed from dumping every <img> it has.
IMAGE_MAX_PER_PRODUCT = 20
