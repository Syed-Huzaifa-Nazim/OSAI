"""The A-F comparison parameters for a scraped website.

Two steps, kept apart on purpose:

    aggregate()   the crawled pages of one site  ->  one dict of figures
    compare_all() two of those dicts             ->  the parameter groups

Everything here is arithmetic over the facts in ``signals.py``. Nothing calls a
model. Where a parameter needs judgement rather than a count -- "is the value
proposition clear?", "is there visual hierarchy?" -- it is scored from named,
checkable conditions and the conditions are listed in the row itself, so a
reader can disagree with the score and see exactly why it came out that way.

Structure and output shape match the Daraz and Alibaba metrics modules, so the
comparison page, the parameter grid and the gap triage screen handle a website
exactly as they handle a product listing.

    A. Content Strategy     value proposition, depth, freshness, breadth
    B. SEO Signals          titles, headings, internal links, URLs, keywords
    C. UX / Design          navigation, hierarchy, mobile, weight, accessibility
    D. Trust & Credibility  social proof, certifications, transparency, contact
    E. Conversion           calls to action, lead capture, pricing, friction
    F. Technical Signals    structure, integrations, security
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

#: Words too common to describe what a site is about.
_STOPWORDS = {
    "the", "and", "for", "with", "our", "your", "you", "are", "from", "that", "this", "all",
    "home", "page", "welcome", "best", "new", "get", "more", "about", "one", "can", "will",
    "have", "has", "was", "were", "its", "into", "out", "how", "why", "what", "who", "when",
    "buy", "shop", "online", "official", "site", "website", "inc", "ltd", "llc", "pvt",
}
_WORD_RE = re.compile(r"[a-z][a-z0-9'-]{2,}")

#: A page shorter than this reads as a stub rather than an answer.
THIN_PAGE_WORDS = 300
#: Above-the-fold wording that is neither a bare slogan nor a wall of text.
CLEAR_HERO_WORDS = (12, 160)
#: Title and meta description lengths search results do not truncate.
GOOD_TITLE = (15, 65)
GOOD_DESCRIPTION = (50, 160)


# =============================================================== aggregate ===


def aggregate(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One site's figures, from the pages that were crawled.

    Accepts the stored ``website_pages`` rows or the scraper's own documents:
    both carry the same keys, so a comparison can be recomputed from storage
    without a re-crawl.
    """
    if not pages:
        return {"pages_crawled": 0}

    ordered = sorted(pages, key=lambda page: (not page.get("is_root"), page.get("depth", 0)))
    home = ordered[0]
    home_signals = _signals(home)
    every = [_signals(page) for page in ordered]

    words = [_int(page.get("word_count")) for page in ordered]
    total_words = sum(words)
    thin = sum(1 for count in words if count < THIN_PAGE_WORDS)

    meta: Dict[str, Any] = {
        # --- the crawl itself ------------------------------------------
        "site_url": home.get("submitted_url") or home.get("page_url") or "",
        "home_url": home.get("page_url") or "",
        "pages_crawled": len(ordered),
        "max_depth": max((_int(page.get("depth")) for page in ordered), default=0),
        "renderers": ", ".join(sorted({str(page.get("renderer") or "http") for page in ordered})),
    }

    # --- A. Content Strategy --------------------------------------------
    hero_words = _int(home_signals.get("above_fold_words"))
    value_checks = {
        "Headline present": _int(home_signals.get("h1_count")) >= 1,
        "Opening screen says it in a sentence or two": CLEAR_HERO_WORDS[0] <= hero_words <= CLEAR_HERO_WORDS[1],
        "Call to action on the opening screen": _int(home_signals.get("cta_count")) >= 1,
        "Description written for search": bool(home_signals.get("has_meta_description")),
        "Home page is not a stub": _int(home.get("word_count")) >= THIN_PAGE_WORDS,
    }
    editorial = [page for page, marks in zip(ordered, every) if marks.get("is_editorial")]
    dated = [marks.get("published_at") for marks in every if marks.get("published_at")]

    meta.update({
        "value_proposition_score": _score(value_checks),
        "value_proposition": _band(_score(value_checks), ("Unclear", "Partly clear", "Clear")),
        "value_proposition_checks": _checklist(value_checks),
        "hero_word_count": hero_words,
        "avg_words_per_page": round(total_words / len(ordered), 1),
        "total_words": total_words,
        "thin_page_share": _percent(thin, len(ordered)),
        "content_depth": _band(
            100 - _percent(thin, len(ordered)), ("Thin", "Mixed", "Substantial")
        ),
        "editorial_page_count": len(editorial),
        "latest_published_at": max(dated) if dated else None,
        "content_freshness": (
            "Dated content published" if dated else
            "Editorial section, no dates found" if editorial else
            "No blog or updates found"
        ),
        "topic_breadth": _topic_breadth(ordered),
        "primary_keywords": _keywords(ordered),
    })

    # --- B. SEO Signals ---------------------------------------------------
    good_titles = sum(
        1 for marks in every if GOOD_TITLE[0] <= _int(marks.get("title_length")) <= GOOD_TITLE[1]
    )
    good_descriptions = sum(
        1 for marks in every
        if GOOD_DESCRIPTION[0] <= _int(marks.get("meta_description_length")) <= GOOD_DESCRIPTION[1]
    )
    internal_links = [_int(marks.get("internal_link_count")) for marks in every]

    meta.update({
        "title_quality_score": _percent(good_titles, len(every)),
        "meta_description_score": _percent(good_descriptions, len(every)),
        "heading_structure_score": _percent(
            sum(1 for marks in every if marks.get("heading_hierarchy_ok")), len(every)
        ),
        "pages_missing_h1": sum(1 for marks in every if _int(marks.get("h1_count")) == 0),
        "internal_links_per_page": round(sum(internal_links) / len(every), 1),
        "external_links_per_page": round(
            sum(_int(marks.get("external_link_count")) for marks in every) / len(every), 1
        ),
        "clean_url_share": _percent(sum(1 for marks in every if marks.get("url_is_clean")), len(every)),
        "canonical_share": _percent(sum(1 for marks in every if marks.get("has_canonical")), len(every)),
        "open_graph_share": _percent(sum(1 for marks in every if marks.get("has_og_tags")), len(every)),
    })

    # --- C. UX / Design ---------------------------------------------------
    images = sum(_int(marks.get("image_count")) for marks in every)
    with_alt = sum(_int(marks.get("images_with_alt")) for marks in every)
    hierarchy_checks = {
        "One heading per page, in order": meta["heading_structure_score"] >= 60,
        "Headings used throughout": sum(_int(marks.get("h1_count")) for marks in every) >= len(every),
        "Text broken into paragraphs": sum(_int(marks.get("paragraph_count")) for marks in every) >= len(every) * 3,
        "Lists or media, not one block": sum(
            _int(marks.get("list_count")) + _int(marks.get("media_embed_count")) for marks in every
        ) >= len(every),
    }
    accessibility_checks = {
        "Page language declared": bool(home_signals.get("has_lang_attribute")),
        "Navigation landmark present": bool(home_signals.get("has_nav_landmark")),
        "Most images have alt text": _percent(with_alt, images) >= 80 if images else False,
        "Responsive images used": _int(home_signals.get("responsive_image_count")) > 0,
    }

    meta.update({
        "navigation_links": _int(home_signals.get("nav_link_count")),
        "navigation_clarity": (
            "No navigation landmark" if not home_signals.get("has_nav_landmark") else
            _band_words(_int(home_signals.get("nav_link_count")), (4, 12),
                        ("Sparse", "Clear", "Crowded"))
        ),
        "visual_hierarchy_score": _score(hierarchy_checks),
        "visual_hierarchy_checks": _checklist(hierarchy_checks),
        "mobile_ready_share": _percent(
            sum(1 for marks in every if marks.get("has_viewport_meta")), len(every)
        ),
        "alt_text_coverage": _percent(with_alt, images),
        "image_count": images,
        "accessibility_score": _score(accessibility_checks),
        "accessibility_checks": _checklist(accessibility_checks),
        "scripts_per_page": round(sum(_int(marks.get("script_count")) for marks in every) / len(every), 1),
        "stylesheets_per_page": round(
            sum(_int(marks.get("stylesheet_count")) for marks in every) / len(every), 1
        ),
        "needed_a_browser": "playwright" in meta["renderers"],
    })
    meta["load_perception"] = _band_words(
        meta["scripts_per_page"], (8, 20), ("Light", "Typical", "Heavy")
    )

    # --- D. Trust & Credibility -------------------------------------------
    social_proof = _union(every, "social_proof_hits")
    certifications = _union(every, "certification_hits")
    contact_channels = sum([
        1 if any(marks.get("has_contact_link") for marks in every) else 0,
        1 if any(marks.get("has_email_link") for marks in every) else 0,
        1 if any(marks.get("has_phone_link") for marks in every) else 0,
    ])
    trust_checks = {
        "Social proof on the site": bool(social_proof),
        "Certifications or seals": bool(certifications),
        "About or team page": any(marks.get("has_about_link") for marks in every),
        "Contact route": contact_channels > 0,
        "Privacy policy": any(marks.get("has_privacy_link") for marks in every),
    }

    meta.update({
        "social_proof_signals": ", ".join(social_proof[:5]) or "none found",
        "social_proof_count": len(social_proof),
        "certification_signals": ", ".join(certifications[:5]) or "none found",
        "certification_count": len(certifications),
        "has_about_page": any(marks.get("has_about_link") for marks in every),
        "contact_channels": contact_channels,
        "contact_accessibility": _band_words(
            contact_channels, (1, 2), ("Hard to reach", "Reachable", "Easy to reach")
        ),
        "trust_score": _score(trust_checks),
        "trust_checks": _checklist(trust_checks),
    })

    # --- E. Conversion Optimization ---------------------------------------
    cta_total = sum(_int(marks.get("cta_count")) for marks in every)
    forms = sum(_int(marks.get("form_count")) for marks in every)
    form_fields = [
        _int(marks.get("form_field_count")) for marks in every if _int(marks.get("form_count"))
    ]
    pricing_published = any(marks.get("has_pricing_link") for marks in every)
    pricing_wall = any(marks.get("mentions_contact_for_pricing") for marks in every)

    meta.update({
        "cta_total": cta_total,
        "cta_per_page": round(cta_total / len(every), 1),
        "home_cta_count": _int(home_signals.get("cta_count")),
        "cta_examples": ", ".join(home_signals.get("cta_labels") or [])[:200] or "none found",
        "form_count": forms,
        "newsletter_signup": any(marks.get("has_newsletter_signup") for marks in every),
        "lead_capture": (
            "Form and newsletter" if forms and any(marks.get("has_newsletter_signup") for marks in every)
            else "Form only" if forms
            else "Newsletter only" if any(marks.get("has_newsletter_signup") for marks in every)
            else "None found"
        ),
        "pricing_transparency": (
            "Published" if pricing_published and not pricing_wall
            else "On request" if pricing_wall
            else "Pricing page found" if pricing_published
            else "No pricing anywhere"
        ),
        "signup_form_fields": min(form_fields) if form_fields else 0,
        "friction_label": (
            "No form found" if not form_fields
            else _band_words(min(form_fields), (4, 8), ("Short form", "Moderate form", "Long form"))
        ),
    })

    # --- F. Technical Signals ---------------------------------------------
    analytics = _union(every, "analytics_tools")
    chat = _union(every, "chat_tools")
    payments = _union(every, "payment_tools")

    meta.update({
        "is_https": bool(home_signals.get("is_https")),
        "has_privacy_policy": any(marks.get("has_privacy_link") for marks in every),
        "has_terms": any(marks.get("has_terms_link") for marks in every),
        "has_cookie_notice": any(marks.get("has_cookie_notice") for marks in every),
        "has_robots_txt": bool(home_signals.get("has_robots_txt")),
        "has_sitemap": bool(home_signals.get("has_sitemap")),
        "sitemap_url_count": _int(home_signals.get("sitemap_url_count")),
        "analytics_tools": ", ".join(analytics) or "none detected",
        "chat_tools": ", ".join(chat) or "none detected",
        "payment_tools": ", ".join(payments) or "none detected",
        "integration_count": len(analytics) + len(chat) + len(payments),
        "security_score": _score({
            "HTTPS": bool(home_signals.get("is_https")),
            "Privacy policy": any(marks.get("has_privacy_link") for marks in every),
            "Terms published": any(marks.get("has_terms_link") for marks in every),
            "Cookie notice": any(marks.get("has_cookie_notice") for marks in every),
        }),
    })

    return meta


# ------------------------------------------------------------- helpers -----


def _signals(page: Dict[str, Any]) -> Dict[str, Any]:
    value = page.get("signals")
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value).strip())
    except ValueError:
        return 0


def _percent(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def _score(checks: Dict[str, bool]) -> float:
    return _percent(sum(1 for passed in checks.values() if passed), len(checks))


def _checklist(checks: Dict[str, bool]) -> str:
    """The conditions behind a score, so the number can be argued with."""
    return "\n".join(f"{'PASS' if passed else 'FAIL'}  {name}" for name, passed in checks.items())


def _band(score: float, labels: Tuple[str, str, str]) -> str:
    if score >= 75:
        return labels[2]
    return labels[1] if score >= 40 else labels[0]


def _band_words(value: float, bounds: Tuple[float, float], labels: Tuple[str, str, str]) -> str:
    """Below the first bound, between the two, or above the second.

    The labels carry the judgement, so "few" can read as good (a short form) or
    bad (sparse navigation) without this needing to know which.
    """
    if value < bounds[0]:
        return labels[0]
    if value <= bounds[1]:
        return labels[1]
    return labels[2]


def _union(every: List[Dict[str, Any]], key: str) -> List[str]:
    found: List[str] = []
    for marks in every:
        for item in marks.get(key) or []:
            if item not in found:
                found.append(str(item))
    return found


def _topic_breadth(pages: List[Dict[str, Any]]) -> int:
    """Distinct top-level sections the crawl reached."""
    sections = set()
    for page in pages:
        path = str(page.get("page_url") or "").split("://")[-1]
        segments = [segment for segment in path.split("/")[1:] if segment]
        if segments:
            sections.add(segments[0].lower())
    return len(sections)


def _keywords(pages: List[Dict[str, Any]]) -> str:
    """What the titles and descriptions keep saying."""
    counter: Counter = Counter()
    for page in pages:
        blob = f"{page.get('title') or ''} {page.get('meta_description') or ''}".lower()
        counter.update(
            word for word in _WORD_RE.findall(blob) if word not in _STOPWORDS
        )
    return ", ".join(word for word, _ in counter.most_common(6)) or "none found"


# ============================================================ parameters ===

#: field -> (label, kind, unit, higher_is_better)
FIELD_SPECS: Dict[str, Tuple[str, str, Optional[str], Optional[bool]]] = {
    # A. Content Strategy
    "value_proposition": ("Value proposition clarity", "text", None, None),
    "value_proposition_score": ("Value proposition score", "percent", "/100", True),
    "hero_word_count": ("Words on the opening screen", "number", "words", None),
    "content_depth": ("Content depth", "text", None, None),
    "avg_words_per_page": ("Words per page", "number", "words", True),
    "thin_page_share": ("Pages under 300 words", "percent", "%", False),
    "content_freshness": ("Content freshness", "text", None, None),
    "editorial_page_count": ("Blog or news pages found", "number", None, True),
    "topic_breadth": ("Distinct sections covered", "number", None, True),

    # B. SEO Signals
    "title_quality_score": ("Titles at a usable length", "percent", "%", True),
    "meta_description_score": ("Descriptions at a usable length", "percent", "%", True),
    "heading_structure_score": ("Pages with a clean heading order", "percent", "%", True),
    "pages_missing_h1": ("Pages with no H1", "number", None, False),
    "internal_links_per_page": ("Internal links per page", "number", None, True),
    "external_links_per_page": ("External links per page", "number", None, None),
    "clean_url_share": ("Clean, readable URLs", "percent", "%", True),
    "canonical_share": ("Pages with a canonical link", "percent", "%", True),
    "open_graph_share": ("Pages with share tags", "percent", "%", True),
    "primary_keywords": ("What the titles target", "text", None, None),

    # C. UX / Design
    "navigation_clarity": ("Navigation clarity", "text", None, None),
    "navigation_links": ("Links in the main navigation", "number", None, None),
    "visual_hierarchy_score": ("Visual hierarchy", "percent", "/100", True),
    "mobile_ready_share": ("Pages declaring a mobile viewport", "percent", "%", True),
    "load_perception": ("Page weight", "text", None, None),
    "scripts_per_page": ("Scripts per page", "number", None, False),
    "accessibility_score": ("Accessibility basics", "percent", "/100", True),
    "alt_text_coverage": ("Images with alt text", "percent", "%", True),

    # D. Trust & Credibility
    "trust_score": ("Trust signals present", "percent", "/100", True),
    "social_proof_count": ("Social proof signals", "number", None, True),
    "social_proof_signals": ("Social proof found", "text", None, None),
    "certification_count": ("Certifications or seals", "number", None, True),
    "certification_signals": ("Certifications found", "text", None, None),
    "has_about_page": ("About or team page", "bool", None, True),
    "contact_accessibility": ("Contact accessibility", "text", None, None),
    "contact_channels": ("Ways to make contact", "number", None, True),

    # E. Conversion Optimization
    "home_cta_count": ("Calls to action on the home page", "number", None, True),
    "cta_per_page": ("Calls to action per page", "number", None, True),
    "cta_examples": ("Calls to action found", "text", None, None),
    "lead_capture": ("Lead capture", "text", None, None),
    "form_count": ("Forms found", "number", None, True),
    "pricing_transparency": ("Pricing transparency", "text", None, None),
    "signup_form_fields": ("Fields in the shortest form", "number", "fields", False),
    "friction_label": ("Form friction", "text", None, None),

    # F. Technical Signals
    "pages_crawled": ("Pages read", "number", None, None),
    "max_depth": ("Clicks deep the crawl reached", "number", None, None),
    "sitemap_url_count": ("URLs listed in the sitemap", "number", None, True),
    "has_sitemap": ("Sitemap published", "bool", None, True),
    "has_robots_txt": ("robots.txt published", "bool", None, True),
    "is_https": ("Served over HTTPS", "bool", None, True),
    "security_score": ("Security and policy basics", "percent", "/100", True),
    "has_privacy_policy": ("Privacy policy", "bool", None, True),
    "integration_count": ("Third-party tools detected", "number", None, None),
    "analytics_tools": ("Analytics", "text", None, None),
    "chat_tools": ("Chat and support", "text", None, None),
    "payment_tools": ("Payments", "text", None, None),
}


PARAMETERS: List[Dict[str, Any]] = [
    {
        "key": "content_strategy",
        "letter": "A",
        "label": "Content Strategy",
        "description": "How clearly the site says what it offers, how substantial its pages are, and how much ground it covers.",
        "gap_category": "content",
        "semantic_field_types": ["page_text", "meta"],
        "metadata_fields": [
            "value_proposition", "value_proposition_score", "hero_word_count", "content_depth",
            "avg_words_per_page", "thin_page_share", "content_freshness", "editorial_page_count",
            "topic_breadth",
        ],
        "query": "what this company offers, who it is for, and what makes it different",
    },
    {
        "key": "seo_signals",
        "letter": "B",
        "label": "SEO Signals",
        "description": "Titles, descriptions, heading order, internal linking and URL shape: what a search engine reads first.",
        "gap_category": "seo",
        "semantic_field_types": ["meta", "headings"],
        "metadata_fields": [
            "title_quality_score", "meta_description_score", "heading_structure_score",
            "pages_missing_h1", "internal_links_per_page", "external_links_per_page",
            "clean_url_share", "canonical_share", "open_graph_share", "primary_keywords",
        ],
        "query": "page titles, descriptions and headings, and the search terms they target",
    },
    {
        "key": "ux_design",
        "letter": "C",
        "label": "UX / Design",
        "description": "Navigation, visual hierarchy, mobile readiness, page weight and the accessibility basics.",
        "gap_category": "content",
        "semantic_field_types": ["headings"],
        "metadata_fields": [
            "navigation_clarity", "navigation_links", "visual_hierarchy_score",
            "mobile_ready_share", "load_perception", "scripts_per_page", "accessibility_score",
            "alt_text_coverage",
        ],
        "query": "how the site is structured and sign-posted for a first-time visitor",
    },
    {
        "key": "trust_credibility",
        "letter": "D",
        "label": "Trust & Credibility",
        "description": "Social proof, certifications, how visible the company is, and how easily it can be contacted.",
        "gap_category": "positioning",
        "semantic_field_types": ["page_text"],
        "metadata_fields": [
            "trust_score", "social_proof_count", "social_proof_signals", "certification_count",
            "certification_signals", "has_about_page", "contact_accessibility", "contact_channels",
        ],
        "query": "testimonials, case studies, client names, certifications, team and contact details",
    },
    {
        "key": "conversion",
        "letter": "E",
        "label": "Conversion Optimization",
        "description": "Calls to action, lead capture, whether pricing is published, and how much a form asks for.",
        "gap_category": "conversion",
        "semantic_field_types": ["page_text"],
        "metadata_fields": [
            "home_cta_count", "cta_per_page", "cta_examples", "lead_capture", "form_count",
            "pricing_transparency", "signup_form_fields", "friction_label",
        ],
        "query": "calls to action, sign-up steps, pricing and what a visitor is asked to do next",
    },
    {
        "key": "technical",
        "letter": "F",
        "label": "Technical Signals",
        "description": "Site structure, the third-party tools in use, and the security and policy basics.",
        "gap_category": "content",
        "semantic_field_types": [],
        "metadata_fields": [
            "pages_crawled", "max_depth", "has_sitemap", "sitemap_url_count", "has_robots_txt",
            "is_https", "security_score", "has_privacy_policy", "integration_count",
            "analytics_tools", "chat_tools", "payment_tools",
        ],
        "query": None,
    },
]

PARAMETERS_BY_KEY: Dict[str, Dict[str, Any]] = {param["key"]: param for param in PARAMETERS}


# ========================================================== metric rows ===


def _numeric(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _judge(
    own: Any, competitor: Any, higher_is_better: Optional[bool]
) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    """(winner, delta, delta_label). Descriptive rows have no winner."""
    if higher_is_better is None:
        return None, None, None
    own_num, competitor_num = _numeric(own), _numeric(competitor)
    if own_num is None or competitor_num is None:
        return None, None, None

    delta = round(own_num - competitor_num, 4)
    if abs(delta) < 1e-9:
        return "tie", 0.0, "Level"

    own_wins = (delta > 0) if higher_is_better else (delta < 0)
    if competitor_num:
        magnitude = f"{abs(delta):,.2f} ({abs(delta) / abs(competitor_num) * 100:,.0f}%)"
    else:
        magnitude = f"{abs(delta):,.2f}"
    return ("own" if own_wins else "competitor"), delta, f"You are {magnitude} {'ahead' if own_wins else 'behind'}"


def build_metric_rows(
    fields: List[str], own: Dict[str, Any], competitor: Dict[str, Any]
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for field in fields:
        label, kind, unit, higher_is_better = FIELD_SPECS.get(
            field, (field.replace("_", " ").capitalize(), "text", None, None)
        )
        own_value, competitor_value = own.get(field), competitor.get(field)
        winner, delta, delta_label = _judge(own_value, competitor_value, higher_is_better)
        rows.append({
            "field": field,
            "label": label,
            "own": own_value,
            "competitor": competitor_value,
            "unit": unit,
            "kind": kind,
            "higher_is_better": higher_is_better,
            "winner": winner,
            "delta": delta,
            "delta_label": delta_label,
        })
    return rows


def derived_for(param_key: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    if param_key == "content_strategy":
        return {
            "pages_read": meta.get("pages_crawled") or 0,
            "substantial_pages": round(
                (meta.get("pages_crawled") or 0) * (100 - (meta.get("thin_page_share") or 0)) / 100
            ),
        }
    if param_key == "seo_signals":
        return {"internal_links_per_page": meta.get("internal_links_per_page") or 0}
    if param_key == "ux_design":
        return {"mobile_ready": (meta.get("mobile_ready_share") or 0) >= 100}
    if param_key == "trust_credibility":
        return {"trust_signals": (meta.get("social_proof_count") or 0) + (meta.get("certification_count") or 0)}
    if param_key == "conversion":
        return {"calls_to_action": meta.get("cta_total") or 0}
    if param_key == "technical":
        return {"third_party_tools": meta.get("integration_count") or 0}
    return {}


# ============================================================== insights ===


def build_insights(
    key: str, rows: List[Dict[str, Any]], own: Dict[str, Any], competitor: Dict[str, Any]
) -> List[str]:
    insights: List[str] = []
    wins = [row for row in rows if row["winner"] == "own"]
    losses = [row for row in rows if row["winner"] == "competitor"]
    if wins or losses:
        insights.append(
            f"You lead on {len(wins)} of {len(wins) + len(losses)} comparable metrics in this group."
        )

    if key == "content_strategy":
        if (own.get("value_proposition_score") or 0) < (competitor.get("value_proposition_score") or 0):
            insights.append(
                "Their opening screen explains the offer more completely than yours: "
                f"{competitor.get('value_proposition')} against your {own.get('value_proposition')}."
            )
        if (own.get("thin_page_share") or 0) > (competitor.get("thin_page_share") or 0) + 20:
            insights.append(
                f"{own.get('thin_page_share')}% of your pages are under 300 words, against "
                f"{competitor.get('thin_page_share')}% of theirs."
            )
        if competitor.get("editorial_page_count") and not own.get("editorial_page_count"):
            insights.append("They publish a blog or news section and you do not.")

    elif key == "seo_signals":
        if (own.get("pages_missing_h1") or 0) > 0:
            insights.append(f"{own.get('pages_missing_h1')} of your pages have no H1 at all.")
        if (own.get("internal_links_per_page") or 0) + 5 < (competitor.get("internal_links_per_page") or 0):
            insights.append("Their pages link to each other far more, which spreads ranking signal.")
        if (own.get("meta_description_score") or 0) < 50:
            insights.append("Most of your pages have no usable description for search results.")

    elif key == "ux_design":
        if (own.get("mobile_ready_share") or 0) < 100:
            insights.append("Not every page of yours declares a mobile viewport.")
        if (own.get("alt_text_coverage") or 0) + 20 < (competitor.get("alt_text_coverage") or 0):
            insights.append("Their images carry alt text far more consistently than yours.")
        if (own.get("scripts_per_page") or 0) > (competitor.get("scripts_per_page") or 0) * 1.5:
            insights.append("Your pages load noticeably more scripts, which shows up as a slower first paint.")

    elif key == "trust_credibility":
        missing = [
            label for field, label in (
                ("social_proof_count", "social proof"),
                ("certification_count", "certifications"),
            ) if (competitor.get(field) or 0) and not (own.get(field) or 0)
        ]
        if missing:
            insights.append("They show " + " and ".join(missing) + "; your site shows none.")
        if competitor.get("has_about_page") and not own.get("has_about_page"):
            insights.append("They have an about or team page and you do not.")
        if (own.get("contact_channels") or 0) < (competitor.get("contact_channels") or 0):
            insights.append("They are easier to contact: more ways to reach them are published.")

    elif key == "conversion":
        if (own.get("home_cta_count") or 0) < (competitor.get("home_cta_count") or 0):
            insights.append(
                f"Their home page carries {competitor.get('home_cta_count')} calls to action against your "
                f"{own.get('home_cta_count')}."
            )
        if own.get("pricing_transparency") != competitor.get("pricing_transparency"):
            insights.append(
                f"Pricing: yours is {str(own.get('pricing_transparency')).lower()}, theirs is "
                f"{str(competitor.get('pricing_transparency')).lower()}."
            )
        if own.get("lead_capture") == "None found" and competitor.get("lead_capture") != "None found":
            insights.append("They capture leads on the site; you have no form or signup at all.")

    elif key == "technical":
        if not own.get("has_sitemap") and competitor.get("has_sitemap"):
            insights.append("They publish a sitemap and you do not, so their pages are found faster.")
        if not own.get("is_https"):
            insights.append("Your site is not served over HTTPS, which browsers mark as not secure.")
        if not own.get("has_privacy_policy") and competitor.get("has_privacy_policy"):
            insights.append("They publish a privacy policy and you do not.")

    if not insights:
        insights.append("No material difference detected between the two sites on this parameter.")
    return insights


def compare_all(
    own_meta: Dict[str, Any], competitor_meta: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Every parameter group compared at once; same shape as the other modules."""
    groups: List[Dict[str, Any]] = []
    for param in PARAMETERS:
        rows = build_metric_rows(param["metadata_fields"], own_meta, competitor_meta)
        groups.append({
            "key": param["key"],
            "letter": param["letter"],
            "label": param["label"],
            "description": param["description"],
            "gap_category": param["gap_category"],
            "semantic_field_types": list(param["semantic_field_types"]),
            "query": param["query"],
            "metrics": rows,
            "own_derived": derived_for(param["key"], own_meta),
            "competitor_derived": derived_for(param["key"], competitor_meta),
            "insights": build_insights(param["key"], rows, own_meta, competitor_meta),
            "own_wins": sum(1 for row in rows if row["winner"] == "own"),
            "competitor_wins": sum(1 for row in rows if row["winner"] == "competitor"),
        })
    return groups
