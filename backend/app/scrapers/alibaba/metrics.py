"""The A-J comparison parameters for Alibaba listings.

A-H are the same eight lenses the Daraz comparison uses, filled with the
closest data an Alibaba listing publishes. Where Alibaba publishes nothing
equivalent (variant counts, stock levels) the row stays in the table and reads
"not available" -- an unmeasured field is never given a winner.

I and J exist only for Alibaba, because they compare what B2B buyers decide on
and a consumer marketplace does not show:

    I. Order Terms & Bulk Pricing   MOQ, quantity price breaks, dispatch time
    J. Supplier Credibility         years, Gold / Verified / Trade Assurance, track record

Structure, scoring and output shape match the Daraz metrics module, so the
comparison page, the Insight Agent and the gap triage screen handle both alike.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .extract import plural_unit, unit_key

#: field -> (label, kind, unit, higher_is_better)
#: A unit of "{currency}" or "{moq_unit}" is filled from the listings.
FIELD_SPECS: Dict[str, Tuple[str, str, Optional[str], Optional[bool]]] = {
    # A. Pricing
    "price": ("Lowest unit price", "currency", "{currency}", False),
    "max_price": ("Highest unit price", "currency", "{currency}", False),
    "original_price": ("Price before promotion", "currency", "{currency}", None),
    "discount_percent": ("Promotion discount", "percent", "%", True),
    "price_range_label": ("Listed price range", "text", None, None),
    "price_unit": ("Priced per", "text", None, None),

    # B. Positioning
    "brand": ("Brand", "text", None, None),
    "is_branded": ("Branded (not generic)", "bool", None, True),
    "title_word_count": ("Title length (words)", "number", "words", None),
    "title_keyword_count": ("Distinct keywords in title", "number", None, True),

    # C. Content quality
    "image_count": ("Images", "number", None, True),
    "has_video": ("Video present", "bool", None, True),
    "spec_count": ("Specification attributes", "number", None, True),
    "content_completeness_score": ("Listing completeness", "percent", "/100", True),

    # D. Social proof
    "rating": ("Rating", "rating", "/5", True),
    "review_count": ("Number of reviews", "number", None, True),

    # E. Availability
    "ready_to_ship": ("Ready to ship", "bool", None, True),
    "buy_now_available": ("Can be ordered online", "bool", None, True),
    "lead_time_days": ("Dispatch time", "number", "days", False),
    "lead_time_label": ("Dispatch terms", "text", None, None),

    # F. Promotional signals
    "promo_tag_count": ("Promotional badges", "number", None, True),
    "has_campaign_tag": ("In a sales campaign", "bool", None, True),
    "promo_tags": ("Badges shown", "text", None, None),
    "sponsored": ("Sponsored (paid) placement", "bool", None, None),

    # G. Variants
    "variant_count": ("Variant options", "number", None, True),
    "customizable": ("Customisation offered (OEM/ODM, logo)", "bool", None, True),
    "customization_signals": ("Customisation signals", "text", None, None),

    # H. Searchability
    "title_length": ("Title size (characters)", "number", "chars", None),
    "title_keyword_density": ("Keyword density in title", "percent", "%", True),
    "title_top_keywords": ("Leading title keywords", "text", None, None),
    "title_attribute_match": ("Title/specification relevance", "text", None, None),
    "title_attribute_match_score": ("Title/specification keyword overlap", "percent", "%", True),

    # I. Order terms & bulk pricing
    "moq": ("Minimum order quantity", "number", "{moq_unit}", False),
    "moq_label": ("Minimum order", "text", None, None),
    "price_tier_count": ("Quantity price breaks", "number", None, True),
    "first_tier_price": ("Price at minimum order", "currency", "{currency}", False),
    "best_tier_price": ("Best bulk price", "currency", "{currency}", False),
    "best_tier_min_quantity": ("Quantity for best price", "number", "{moq_unit}", False),
    "bulk_discount_percent": ("Bulk discount (best vs minimum order)", "percent", "%", True),

    # J. Supplier credibility
    "supplier_name": ("Supplier", "text", None, None),
    "supplier_country": ("Supplier country", "text", None, None),
    "supplier_years": ("Years on Alibaba", "number", "years", True),
    "gold_supplier": ("Gold Supplier", "bool", None, True),
    "verified_supplier": ("Verified supplier", "bool", None, True),
    "trade_assurance": ("Trade Assurance", "bool", None, True),
    "transaction_level": ("Transaction level", "number", None, True),
    "response_rate_percent": ("Response rate", "percent", "%", True),
    "historic_order_count": ("Past orders", "number", None, True),
    "historic_gmv_label": ("Past sales volume", "text", None, None),
}


PARAMETERS: List[Dict[str, Any]] = [
    {
        "key": "pricing",
        "letter": "A",
        "label": "Pricing Intelligence",
        "description": "Unit price range across quantity tiers, and any promotion discount.",
        "gap_category": "pricing",
        "semantic_field_types": [],
        "metadata_fields": [
            "price", "max_price", "original_price", "discount_percent", "price_range_label", "price_unit",
        ],
        "query": None,
    },
    {
        "key": "positioning",
        "letter": "B",
        "label": "Product Positioning",
        "description": "Title structure and keyword usage, and brand vs generic positioning.",
        "gap_category": "positioning",
        "semantic_field_types": ["title"],
        "metadata_fields": ["brand", "is_branded", "title_word_count", "title_keyword_count"],
        "query": "brand name, product type, key features and intended use in the product title",
    },
    {
        "key": "content_quality",
        "letter": "C",
        "label": "Content Quality",
        "description": "Image count, product video, specification attributes and listing completeness.",
        "gap_category": "content",
        "semantic_field_types": ["specs"],
        "metadata_fields": ["image_count", "has_video", "spec_count", "content_completeness_score"],
        "query": "technical specifications, materials, dimensions, interface and compatibility",
    },
    {
        "key": "social_proof",
        "letter": "D",
        "label": "Social Proof",
        "description": "Rating and review volume. Alibaba listings do not publish review text.",
        "gap_category": "social_engagement",
        "semantic_field_types": [],
        "metadata_fields": ["rating", "review_count"],
        "query": None,
    },
    {
        "key": "availability_trust",
        "letter": "E",
        "label": "Availability & Trust",
        "description": "Whether the product ships ready-made, can be ordered online, and how fast it dispatches.",
        "gap_category": "conversion",
        "semantic_field_types": [],
        "metadata_fields": ["ready_to_ship", "buy_now_available", "lead_time_days", "lead_time_label"],
        "query": None,
    },
    {
        "key": "promotional_signals",
        "letter": "F",
        "label": "Promotional Signals",
        "description": "Ready-to-ship and campaign badges, and paid placement.",
        "gap_category": "conversion",
        "semantic_field_types": ["promo_tags"],
        "metadata_fields": ["promo_tag_count", "has_campaign_tag", "promo_tags", "sponsored"],
        "query": "ready to ship badge, seasonal sale campaign and promotional labels",
    },
    {
        "key": "variants",
        "letter": "G",
        "label": "Variant & Options Depth",
        "description": "Customisation offered to buyers (OEM/ODM, own logo). Variant counts are not published.",
        "gap_category": "audience",
        "semantic_field_types": [],
        "metadata_fields": ["variant_count", "customizable", "customization_signals"],
        "query": None,
    },
    {
        "key": "searchability",
        "letter": "H",
        "label": "Searchability / On-platform SEO",
        "description": "Keyword density in the title and how well the title matches the listed specifications.",
        "gap_category": "seo",
        "semantic_field_types": ["title"],
        "metadata_fields": [
            "title_length", "title_word_count", "title_keyword_density", "title_top_keywords",
            "title_attribute_match", "title_attribute_match_score",
        ],
        "query": "search keywords a buyer would type to find this product on Alibaba",
    },
    {
        "key": "order_terms",
        "letter": "I",
        "label": "Order Terms & Bulk Pricing",
        "description": "Minimum order quantity, quantity price breaks, bulk discount depth and dispatch time.",
        "gap_category": "pricing",
        "semantic_field_types": ["order_terms"],
        "metadata_fields": [
            "moq", "moq_label", "price_tier_count", "first_tier_price", "best_tier_price",
            "best_tier_min_quantity", "bulk_discount_percent", "lead_time_days",
        ],
        "query": "minimum order quantity, bulk quantity price breaks and dispatch time",
    },
    {
        "key": "supplier_credibility",
        "letter": "J",
        "label": "Supplier Credibility",
        "description": "Years on Alibaba, Gold / Verified / Trade Assurance status, responsiveness and track record.",
        "gap_category": "conversion",
        "semantic_field_types": ["supplier"],
        "metadata_fields": [
            "supplier_name", "supplier_country", "supplier_years", "gold_supplier", "verified_supplier",
            "trade_assurance", "transaction_level", "response_rate_percent", "historic_order_count",
            "historic_gmv_label",
        ],
        "query": "supplier years in business, verification, trade assurance, response rate and order history",
    },
]

PARAMETERS_BY_KEY: Dict[str, Dict[str, Any]] = {p["key"]: p for p in PARAMETERS}


# --------------------------------------------------------------- metric rows


def _numeric(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _judge(own: Any, competitor: Any, higher_is_better: Optional[bool]) -> Tuple[Optional[str], Optional[float], Optional[str]]:
    """(winner, delta, delta_label). No winner for descriptive or missing fields."""
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
        relative = abs(delta) / abs(competitor_num) * 100
        magnitude = f"{abs(delta):,.2f} ({relative:,.0f}%)"
    else:
        magnitude = f"{abs(delta):,.2f}"
    return ("own" if own_wins else "competitor"), delta, f"You are {magnitude} {'ahead' if own_wins else 'behind'}"


def _resolve_unit(template: Optional[str], own: Dict[str, Any], competitor: Dict[str, Any]) -> Tuple[Optional[str], bool]:
    """(unit, comparable). Money in two currencies, or quantities in two units, is not comparable.

    Quantity units come back plural ("pieces"), since one label serves both
    listings' figures; the page writes the singular for a quantity of one.
    """
    if template not in ("{currency}", "{moq_unit}"):
        return template, True
    key = template.strip("{}")
    own_unit, competitor_unit = own.get(key), competitor.get(key)
    word = plural_unit if key == "moq_unit" else (lambda unit: unit)
    if own_unit and competitor_unit and unit_key(own_unit) != unit_key(competitor_unit):
        return f"{word(own_unit)} vs {word(competitor_unit)}", False
    unit = own_unit or competitor_unit
    return (word(unit) if unit else None), True


def build_metric_rows(fields: List[str], own: Dict[str, Any], competitor: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for field in fields:
        label, kind, unit_template, higher_is_better = FIELD_SPECS.get(
            field, (field.replace("_", " ").title(), "text", None, None)
        )
        unit, comparable = _resolve_unit(unit_template, own, competitor)
        own_value, competitor_value = own.get(field), competitor.get(field)
        winner, delta, delta_label = _judge(own_value, competitor_value, higher_is_better if comparable else None)
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
    if param_key == "pricing":
        low, high = meta.get("price"), meta.get("max_price")
        return {
            "price_spread_percent": round((high - low) / high * 100, 2) if low and high and high > low else 0,
            "has_promotion": bool(meta.get("discount_percent")),
        }
    if param_key == "content_quality":
        return {
            "media_assets": (meta.get("image_count") or 0) + (1 if meta.get("has_video") else 0),
            "spec_attributes": meta.get("spec_count") or 0,
        }
    if param_key == "social_proof":
        rating, count = meta.get("rating") or 0, meta.get("review_count") or 0
        return {"credibility_index": round(rating * min(count, 1000) / 1000, 2)}
    if param_key == "availability_trust":
        return {"orderable_now": bool(meta.get("ready_to_ship")) and bool(meta.get("buy_now_available"))}
    if param_key == "promotional_signals":
        return {"active_signals": sum(1 for key in ("ready_to_ship", "has_campaign_tag") if meta.get(key))}
    if param_key == "variants":
        return {"customizable": bool(meta.get("customizable"))}
    if param_key == "searchability":
        return {
            "keyword_density": meta.get("title_keyword_density") or 0,
            "spec_match_score": meta.get("title_attribute_match_score") or 0,
        }
    if param_key == "positioning":
        return {"branded": bool(meta.get("is_branded"))}
    if param_key == "order_terms":
        moq = meta.get("moq")
        return {
            "entry_order_value": round(moq * meta["first_tier_price"], 2) if moq and meta.get("first_tier_price") else None,
            "bulk_discount_percent": meta.get("bulk_discount_percent") or 0,
        }
    if param_key == "supplier_credibility":
        badges = sum(1 for key in ("gold_supplier", "verified_supplier", "trade_assurance") if meta.get(key))
        return {"trust_badges": badges}
    return {}


# ------------------------------------------------------------------ insights


def _money(value: Optional[float], currency: Optional[str]) -> str:
    if value is None:
        return "not available"
    prefix = "US$" if (currency or "USD") == "USD" else f"{currency} "
    return f"{prefix}{value:,.2f}" if value >= 1 else f"{prefix}{value:,.4f}".rstrip("0").rstrip(".")


def build_insights(key: str, rows: List[Dict[str, Any]], own: Dict[str, Any], competitor: Dict[str, Any]) -> List[str]:
    insights: List[str] = []
    wins = [row for row in rows if row["winner"] == "own"]
    losses = [row for row in rows if row["winner"] == "competitor"]
    if wins or losses:
        insights.append(f"You lead on {len(wins)} of {len(wins) + len(losses)} comparable metrics in this group.")

    same_currency = (own.get("currency") or "USD") == (competitor.get("currency") or "USD")
    currency = own.get("currency")

    if key == "pricing":
        own_price, competitor_price = own.get("price"), competitor.get("price")
        if own_price and competitor_price and same_currency:
            gap = own_price - competitor_price
            if abs(gap) < 1e-9:
                insights.append("Both listings start at the same unit price.")
            else:
                side = "more expensive" if gap > 0 else "cheaper"
                insights.append(
                    f"Your lowest unit price is {_money(abs(gap), currency)} "
                    f"({abs(gap) / competitor_price * 100:.0f}%) {side} than the competitor's."
                )
        if not same_currency:
            insights.append("The two listings are priced in different currencies, so prices are not compared.")
        if (competitor.get("discount_percent") or 0) > (own.get("discount_percent") or 0) + 5:
            insights.append("The competitor is running a promotion discount deeper than yours.")

    elif key == "positioning":
        if competitor.get("is_branded") and not own.get("is_branded"):
            insights.append("The competitor lists a brand while yours reads as generic.")
        if (competitor.get("title_word_count") or 0) > (own.get("title_word_count") or 0) + 4:
            insights.append("The competitor's title is noticeably longer, covering more search terms.")

    elif key == "content_quality":
        if (competitor.get("image_count") or 0) > (own.get("image_count") or 0):
            insights.append("The competitor shows more product images.")
        if competitor.get("has_video") and not own.get("has_video"):
            insights.append("The competitor has a product video and you do not.")
        if (competitor.get("spec_count") or 0) > (own.get("spec_count") or 0):
            insights.append("The competitor lists more specification attributes, which buyers filter on.")

    elif key == "social_proof":
        own_reviews, competitor_reviews = own.get("review_count") or 0, competitor.get("review_count") or 0
        if competitor_reviews > own_reviews * 1.5 and competitor_reviews > 10:
            insights.append(f"The competitor has {competitor_reviews - own_reviews:,} more reviews.")
        if own_reviews == 0:
            insights.append("Your listing has no reviews yet; first orders will carry more weight.")
        own_rating, competitor_rating = own.get("rating"), competitor.get("rating")
        if own_rating and competitor_rating and abs(own_rating - competitor_rating) >= 0.2:
            better = "your" if own_rating > competitor_rating else "the competitor's"
            insights.append(f"Ratings differ meaningfully - {better} listing is rated higher.")

    elif key == "availability_trust":
        if competitor.get("ready_to_ship") and not own.get("ready_to_ship"):
            insights.append("The competitor is marked Ready to Ship and you are not - buyers with urgent orders filter on this.")
        own_days, competitor_days = own.get("lead_time_days"), competitor.get("lead_time_days")
        if own_days is not None and competitor_days is not None and own_days > competitor_days:
            insights.append(f"The competitor dispatches {own_days - competitor_days} day(s) sooner.")
        if competitor.get("buy_now_available") and not own.get("buy_now_available"):
            insights.append("The competitor can be ordered online directly; yours needs an inquiry.")

    elif key == "promotional_signals":
        if competitor.get("has_campaign_tag") and not own.get("has_campaign_tag"):
            insights.append("The competitor is part of a sales campaign and you are not.")
        if competitor.get("sponsored") and not own.get("sponsored"):
            insights.append("The competitor pays for sponsored placement in search results.")

    elif key == "variants":
        if competitor.get("customizable") and not own.get("customizable"):
            insights.append("The competitor advertises customisation (OEM/ODM or own logo) and you do not.")
        elif own.get("customizable") and not competitor.get("customizable"):
            insights.append("You advertise customisation and the competitor does not.")

    elif key == "searchability":
        if (competitor.get("title_attribute_match_score") or 0) > (own.get("title_attribute_match_score") or 0) + 10:
            insights.append("The competitor's title repeats more of its own specification values, helping search matching.")
        if (own.get("title_word_count") or 0) < 8:
            insights.append("Your title is short for Alibaba search - most ranking titles name material, use and key specs.")

    elif key == "order_terms":
        own_moq, competitor_moq = own.get("moq"), competitor.get("moq")
        same_unit = unit_key(own.get("moq_unit")) == unit_key(competitor.get("moq_unit")) or not (
            own.get("moq_unit") and competitor.get("moq_unit")
        )
        if own_moq and competitor_moq and same_unit and own_moq != competitor_moq:
            if competitor_moq < own_moq:
                ratio = own_moq / competitor_moq
                insights.append(
                    f"The competitor's minimum order is {competitor_moq:,} vs your {own_moq:,}"
                    + (f" - {ratio:.0f}x lower" if ratio >= 2 else "")
                    + ", so smaller buyers can start with them."
                )
            else:
                insights.append(f"Your minimum order ({own_moq:,}) is lower than the competitor's ({competitor_moq:,}).")
        if (competitor.get("price_tier_count") or 0) > (own.get("price_tier_count") or 0):
            insights.append("The competitor offers more quantity price breaks, rewarding larger orders.")
        if (competitor.get("bulk_discount_percent") or 0) > (own.get("bulk_discount_percent") or 0) + 5:
            insights.append(
                f"The competitor's best bulk price is {competitor.get('bulk_discount_percent'):.0f}% below its entry price, "
                f"vs {own.get('bulk_discount_percent') or 0:.0f}% for you."
            )

    elif key == "supplier_credibility":
        missing = [
            label for field, label in (
                ("trade_assurance", "Trade Assurance"),
                ("verified_supplier", "Verified supplier"),
                ("gold_supplier", "Gold Supplier"),
            ) if competitor.get(field) and not own.get(field)
        ]
        if missing:
            insights.append("Competitor-only trust badges: " + ", ".join(missing) + ".")
        own_years, competitor_years = own.get("supplier_years"), competitor.get("supplier_years")
        if own_years is not None and competitor_years is not None and competitor_years > own_years:
            insights.append(f"The competitor's supplier has been on Alibaba {competitor_years - own_years} year(s) longer.")
        own_rate, competitor_rate = own.get("response_rate_percent"), competitor.get("response_rate_percent")
        if own_rate is not None and competitor_rate is not None and competitor_rate > own_rate + 2:
            insights.append(f"The competitor answers inquiries more reliably ({competitor_rate}% vs {own_rate}%).")
        own_orders, competitor_orders = own.get("historic_order_count"), competitor.get("historic_order_count")
        if own_orders is not None and competitor_orders and competitor_orders > (own_orders or 0) * 2:
            insights.append("The competitor's supplier has a much longer order history on Alibaba.")

    if not insights:
        insights.append("No material difference detected between the two listings on this parameter.")
    return insights


def compare_all(own_meta: Dict[str, Any], competitor_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every parameter group compared at once; same shape as the Daraz module."""
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
