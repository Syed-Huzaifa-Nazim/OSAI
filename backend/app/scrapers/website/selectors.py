"""
ALL website-extraction rules live in this file.

Ported verbatim from the standalone website scraper, so its cleaning behaviour
is unchanged: the same tags are stripped, the same boilerplate selectors are
dropped, the same file extensions are skipped while crawling, and the same
markers decide that a page is a JavaScript shell worth re-rendering.

When a site's markup defeats the cleaner, edit THIS FILE ONLY.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Cleaning
# ---------------------------------------------------------------------------
#: Removed outright: they carry no reading content, only behaviour or styling.
REMOVE_TAGS = {"script", "style", "noscript", "svg", "canvas", "template", "iframe", "form"}

#: Chrome that repeats on every page and would otherwise dominate the text.
BOILERPLATE_SELECTORS = [
    "nav",
    "footer",
    "aside",
    "[role='navigation']",
    "[role='banner']",
    "[role='contentinfo']",
    ".cookie",
    ".cookies",
    ".cookie-banner",
    ".modal",
    ".popup",
    ".newsletter",
    ".advertisement",
    ".ads",
]

#: Headings kept as their own field, in document order.
HEADING_TAGS = ["h1", "h2", "h3"]

#: Anchor text longer than this is truncated in the stored link list.
MAX_LINK_TEXT = 500

# ---------------------------------------------------------------------------
# 2. Crawling
# ---------------------------------------------------------------------------
#: Not pages: following these wastes the page budget on binaries.
SKIP_EXTENSIONS = (
    ".7z", ".avi", ".bmp", ".css", ".csv", ".doc", ".docx", ".gif", ".gz", ".ico",
    ".jpeg", ".jpg", ".js", ".json", ".mov", ".mp3", ".mp4", ".pdf", ".png", ".ppt",
    ".pptx", ".rar", ".rss", ".svg", ".tar", ".txt", ".wav", ".webm", ".webp",
    ".xls", ".xlsx", ".xml", ".zip",
)

#: Never followed: a crawler must not press a site's destructive buttons.
SKIP_PATH_FRAGMENTS = ("/logout", "/signout", "/delete")

# ---------------------------------------------------------------------------
# 3. Rendering
# ---------------------------------------------------------------------------
#: A page with little text and one of these is a shell the browser must fill in.
JAVASCRIPT_SHELL_MARKERS = (
    'id="root"',
    "id='root'",
    'id="app"',
    "id='app'",
    "__next_data__",
    "__nuxt__",
)
#: ...or simply a page that is almost entirely script tags.
JAVASCRIPT_SHELL_SCRIPT_COUNT = 5

#: How the browser fallback coaxes lazy-loaded content into the DOM.
PLAYWRIGHT_SCROLL_STEPS = 5
PLAYWRIGHT_SCROLL_DELAY_MS = 600
PLAYWRIGHT_NETWORK_IDLE_MS = 10_000

# ---------------------------------------------------------------------------
# 4. Requests
# ---------------------------------------------------------------------------
USER_AGENT = "OptiStratixAI-Scout/1.0 (+https://github.com/OptiStratix-AI/Development)"
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8",
}
#: Retried automatically by the HTTP adapter.
RETRY_STATUS_CODES = (408, 425, 429, 500, 502, 503, 504)
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.8

#: Only markup is read; anything else is skipped with a clear reason.
HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")

# ---------------------------------------------------------------------------
# 5. Signals the comparison parameters are built from
# ---------------------------------------------------------------------------
# Every keyword list below is matched case-insensitively against link text,
# button text or page text. They are deliberately plain words rather than
# selectors: a site can call its pricing page anything, but it almost always
# says "pricing" somewhere in the link.

#: Words that make a link or button a call to action.
CTA_KEYWORDS = (
    "get started", "start free", "free trial", "try free", "try it", "sign up", "signup",
    "register", "book a demo", "request a demo", "get a demo", "book a call", "contact sales",
    "talk to us", "get in touch", "buy now", "shop now", "order now", "add to cart",
    "subscribe", "join now", "learn more", "see pricing", "get quote", "request a quote",
    "download", "apply now", "enquire", "inquire",
)

#: Testimonials, case studies and client proof.
SOCIAL_PROOF_KEYWORDS = (
    "testimonial", "what our clients", "what our customers", "case study", "case studies",
    "success story", "trusted by", "our clients", "our customers", "reviews", "rated",
    "customer stories", "loved by",
)

#: Certifications, security seals and compliance marks.
CERTIFICATION_KEYWORDS = (
    "iso 9001", "iso 27001", "iso certified", "gdpr", "hipaa", "pci dss", "soc 2",
    "ssl secured", "secure checkout", "verified by", "certified", "accredited", "licensed",
)

#: Newsletter / lead capture.
NEWSLETTER_KEYWORDS = (
    "newsletter", "subscribe to our", "join our mailing", "email updates", "stay updated",
    "sign up for updates",
)

#: Pricing, and the "no price until you ask" pattern.
PRICING_LINK_KEYWORDS = ("pricing", "prices", "plans", "packages", "tariff", "rates")
PRICING_WALL_KEYWORDS = (
    "contact us for pricing", "contact for pricing", "request a quote", "get a quote",
    "pricing on request", "call for pricing", "custom pricing",
)

#: Company transparency and reachability.
ABOUT_LINK_KEYWORDS = ("about", "our story", "who we are", "team", "leadership", "careers")
CONTACT_LINK_KEYWORDS = ("contact", "support", "help", "get in touch", "reach us")
PRIVACY_LINK_KEYWORDS = ("privacy", "privacy policy", "data protection")
TERMS_LINK_KEYWORDS = ("terms", "terms of service", "terms and conditions", "legal")

#: Cookie/consent notices, which is also a weak GDPR signal.
COOKIE_KEYWORDS = ("cookie", "consent", "we use cookies")

#: Third-party services, fingerprinted by what their script URLs contain.
ANALYTICS_FINGERPRINTS = {
    "Google Analytics": ("google-analytics.com", "gtag/js", "googletagmanager.com"),
    "Meta Pixel": ("connect.facebook.net",),
    "Hotjar": ("hotjar.com",),
    "Plausible": ("plausible.io",),
    "Matomo": ("matomo.", "piwik."),
    "Mixpanel": ("mixpanel.com",),
    "Segment": ("segment.com/analytics.js", "cdn.segment.com"),
    "Clarity": ("clarity.ms",),
}
CHAT_FINGERPRINTS = {
    "Intercom": ("intercom.io", "intercomcdn"),
    "Drift": ("drift.com",),
    "Tawk.to": ("tawk.to",),
    "Crisp": ("crisp.chat",),
    "Zendesk": ("zdassets.com", "zendesk.com"),
    "HubSpot": ("hs-scripts.com", "hubspot.com"),
    "WhatsApp": ("wa.me", "api.whatsapp.com"),
    "Tidio": ("tidio.co",),
}
PAYMENT_FINGERPRINTS = {
    "Stripe": ("js.stripe.com",),
    "PayPal": ("paypal.com/sdk", "paypalobjects.com"),
    "Razorpay": ("checkout.razorpay.com",),
    "Shopify": ("cdn.shopify.com",),
    "Paddle": ("paddle.com",),
}

#: Paths that mark a page as editorial, for the freshness signal.
EDITORIAL_PATH_HINTS = ("/blog", "/news", "/article", "/insights", "/resources", "/press", "/updates")

#: Where a published date hides.
DATE_META_PROPERTIES = (
    "article:published_time", "article:modified_time", "og:updated_time",
    "datepublished", "datemodified",
)

#: Roughly the first screenful of reading, used for the above-the-fold signal.
ABOVE_FOLD_CHARS = 1500

#: A URL is "clean" when it stays under these.
MAX_CLEAN_URL_DEPTH = 4
MAX_CLEAN_URL_LENGTH = 100

# ---------------------------------------------------------------------------
# 6. Images
# ---------------------------------------------------------------------------
# What a site looks like is part of what a comparison is judging, so the
# marketing images are kept alongside the text. Nothing is downloaded: the
# page's own URLs are stored, exactly as a marketplace listing's photos are.

#: Stored per page. Enough to show what a site looks like, not its icon set.
MAX_IMAGES_PER_PAGE = 10

#: Where a lazy-loading site hides the real source, in the order to try.
IMAGE_SRC_ATTRIBUTES = (
    "src", "data-src", "data-original", "data-lazy-src", "data-image", "srcset", "data-srcset",
)

#: A hero/banner image is the first image inside one of these. `main` is
#: deliberately absent: an image in the body is content, not the hero.
HERO_CONTAINERS = (
    "header", "[role='banner']", ".hero", "#hero", ".banner", ".jumbotron", ".masthead",
)

#: Chrome rather than content: icons, logos, sprites, flags and spacers.
IMAGE_SKIP_URL_FRAGMENTS = (
    "/icon", "icon-", "-icon", "/icons/", "/logo", "logo-", "-logo", "/logos/",
    "/sprite", "sprite-", "/avatar", "avatar-", "/badge", "badge-", "/flag", "/flags/",
    "/emoji", "1x1", "pixel.", "spacer.", "blank.", "transparent.", "placeholder", "favicon",
)
#: Vector icons and favicons, which are never the picture of a product or team.
IMAGE_SKIP_EXTENSIONS = (".svg", ".ico")
#: A declared dimension under this is a spacer, a bullet or an icon.
MIN_IMAGE_DIMENSION = 80

#: Site-level probes, fetched once per site.
SITEMAP_PATHS = ("/sitemap.xml", "/sitemap_index.xml")
ROBOTS_PATH = "/robots.txt"
#: Cap on how much of a sitemap is read when counting its URLs.
SITEMAP_MAX_BYTES = 2_000_000
