"""The A-H comparison parameters for Daraz listings.

Ported from the standalone scraper's comparison engine. The scoring rules,
thresholds and wording are unchanged; what differs is where the output goes.
In the standalone tool these rows were the product. Here they are *evidence*:
the Insight Agent (stage 4) turns each losing metric into a gap with a
quantified justification, so a strategy claim can always be traced back to two
concrete numbers rather than to a model's opinion.

No vector search happens in this module. It compares two metadata dicts and
nothing else, which keeps it importable, cheap and unit-testable. Supporting
quotes are retrieved separately from the project's Chroma collection.
"""

from __future__ import annotations

from typing import Any

#: field -> (label, kind, unit, higher_is_better)
#: ``kind`` drives frontend formatting; ``higher_is_better`` of None means the
#: field is descriptive and has no winner.
FIELD_SPECS: dict[str, tuple[str, str, str | None, bool | None]] = {
    # A. Pricing
    "price": ("Selling price", "currency", "PKR", False),
    "original_price": ("Listed price (before discount)", "currency", "PKR", None),
    "discount_percent": ("Discount", "percent", "%", True),
    "price_per_unit": ("Price per unit", "currency", "PKR", False),
    "unit_quantity": ("Units in listing", "number", None, None),
    "shipping_cost": ("Shipping cost", "currency", "PKR", False),
    "shipping_cost_label": ("Shipping terms", "text", None, None),
    "deal_type": ("Deal type", "text", None, None),

    # B. Positioning
    "brand": ("Brand", "text", None, None),
    "is_branded": ("Branded (not generic)", "bool", None, True),
    "category": ("Category path", "text", None, None),
    "category_leaf": ("Placed in category", "text", None, None),
    "category_depth": ("Category depth", "number", "levels", True),
    "title_word_count": ("Title length (words)", "number", "words", None),
    "title_keyword_count": ("Distinct keywords in title", "number", None, True),

    # C. Content quality
    "description_length": ("Description size (characters)", "number", "chars", True),
    "description_word_count": ("Description length (words)", "number", "words", True),
    "spec_count": ("Specification lines", "number", None, True),
    "bullet_count": ("Bullet points", "number", None, True),
    "image_count": ("Images", "number", None, True),
    "has_video": ("Video present", "bool", None, True),
    "variant_chart_present": ("Size / variant chart", "bool", None, True),
    "content_completeness_score": ("Listing completeness", "percent", "/100", True),

    # D. Social proof
    "rating": ("Rating", "rating", "/5", True),
    "review_count": ("Number of reviews", "number", None, True),
    "reviews_scraped": ("Reviews retrieved", "number", None, None),
    "review_sentiment_score": ("Review sentiment", "number", "-1..+1", True),
    "review_positive_themes": ("Positive themes", "text", None, None),
    "review_negative_themes": ("Negative themes", "text", None, None),
    "qa_count": ("Q&A activity", "number", "questions", True),

    # E. Availability & trust
    "stock_status": ("Stock status", "text", None, None),
    "stock_quantity": ("Units in stock", "number", None, True),
    "delivery_estimate": ("Delivery estimate", "text", None, None),
    "seller_name": ("Seller", "text", None, None),
    "seller_rating": ("Seller rating", "rating", "/5", True),
    "seller_rating_percent": ("Seller positive rate", "percent", "%", True),
    "seller_verified": ("Verified / official store", "bool", None, True),

    # F. Promotional signals
    "is_bestseller": ("Best seller / trending tag", "bool", None, True),
    "has_bundle": ("Bundle offer", "bool", None, True),
    "has_flash_sale": ("Flash sale", "bool", None, True),
    "has_coupon": ("Voucher / coupon", "bool", None, True),
    "promo_tag_count": ("Promotional badges", "number", None, True),
    "warranty_present": ("Warranty offered", "bool", None, True),
    "warranty_text": ("Warranty terms", "text", None, None),

    # G. Variants
    "variant_count": ("Variant options", "number", None, True),
    "variant_groups": ("Option groups", "text", None, None),
    "customizable": ("Customisation available", "bool", None, True),

    # H. Searchability / SEO
    "title_length": ("Title size (characters)", "number", "chars", None),
    "title_keyword_density": ("Keyword density in title", "percent", "%", True),
    "title_top_keywords": ("Leading title keywords", "text", None, None),
    "category_tag_match": ("Category-tag relevance", "text", None, None),
    "category_tag_match_score": ("Title/category keyword overlap", "percent", "%", True),
}


#: The eight comparison groups. ``gap_category`` maps each one onto the
#: project's existing GapCategory enum so stage 4 output slots into the gap
#: triage screen without a new taxonomy.
PARAMETERS: list[dict[str, Any]] = [
    {
        "key": "pricing",
        "letter": "A",
        "label": "Pricing Intelligence",
        "description": "Listed vs discounted price, discount depth, deal type, price-per-unit and shipping cost.",
        "gap_category": "pricing",
        "semantic_field_types": [],
        "metadata_fields": [
            "price", "original_price", "discount_percent", "deal_type",
            "price_per_unit", "unit_quantity", "shipping_cost", "shipping_cost_label",
        ],
        "query": None,
    },
    {
        "key": "positioning",
        "letter": "B",
        "label": "Product Positioning",
        "description": "Title structure and keyword usage, category placement, brand vs generic positioning.",
        "gap_category": "positioning",
        "semantic_field_types": ["title", "category"],
        "metadata_fields": [
            "brand", "is_branded", "category", "category_leaf",
            "category_depth", "title_word_count", "title_keyword_count",
        ],
        "query": "brand name, product type, key features and category placement in the product title",
    },
    {
        "key": "content_quality",
        "letter": "C",
        "label": "Content Quality",
        "description": "Description depth, specification completeness, image count, video presence and size charts.",
        "gap_category": "content",
        "semantic_field_types": ["description", "specs"],
        "metadata_fields": [
            "description_word_count", "description_length", "spec_count", "bullet_count",
            "image_count", "has_video", "variant_chart_present", "content_completeness_score",
        ],
        "query": "detailed product description, materials, dimensions, technical specifications and usage instructions",
    },
    {
        "key": "social_proof",
        "letter": "D",
        "label": "Social Proof",
        "description": "Rating, review volume, positive/negative sentiment themes and Q&A activity.",
        "gap_category": "social_engagement",
        "semantic_field_types": ["review"],
        "metadata_fields": [
            "rating", "review_count", "reviews_scraped", "review_sentiment_score",
            "review_positive_themes", "review_negative_themes", "qa_count",
        ],
        "query": "customer opinions on product quality, delivery speed, value for money and whether it is genuine",
    },
    {
        "key": "availability_trust",
        "letter": "E",
        "label": "Availability & Trust",
        "description": "Stock status, delivery estimate, return/refund policy terms and seller credibility.",
        "gap_category": "conversion",
        "semantic_field_types": ["policy_text"],
        "metadata_fields": [
            "stock_status", "stock_quantity", "delivery_estimate",
            "seller_name", "seller_rating", "seller_rating_percent", "seller_verified",
        ],
        "query": "return policy, refund window, replacement terms, warranty coverage and delivery guarantee",
    },
    {
        "key": "promotional_signals",
        "letter": "F",
        "label": "Promotional Signals",
        "description": "Best-seller / trending tags, bundle offers, vouchers and warranty messaging.",
        "gap_category": "conversion",
        "semantic_field_types": ["promo_tags"],
        "metadata_fields": [
            "is_bestseller", "has_bundle", "has_flash_sale", "has_coupon",
            "promo_tag_count", "warranty_present", "warranty_text",
        ],
        "query": "best seller badge, trending label, flash sale, bundle deal, voucher and warranty offer",
    },
    {
        "key": "variants",
        "letter": "G",
        "label": "Variant & Options Depth",
        "description": "How many colour/size/variant options are offered and whether customisation is available.",
        "gap_category": "audience",
        "semantic_field_types": [],
        "metadata_fields": ["variant_count", "variant_groups", "customizable"],
        "query": None,
    },
    {
        "key": "searchability",
        "letter": "H",
        "label": "Searchability / On-platform SEO",
        "description": "Keyword density in the title and how accurately the listing is tagged to its category.",
        "gap_category": "seo",
        "semantic_field_types": ["title"],
        "metadata_fields": [
            "title_length", "title_word_count", "title_keyword_density",
            "title_top_keywords", "category_tag_match", "category_tag_match_score",
        ],
        "query": "search keywords a shopper would type to find this product on Daraz",
    },
]

PARAMETERS_BY_KEY: dict[str, dict[str, Any]] = {p["key"]: p for p in PARAMETERS}


# --------------------------------------------------------------- metric rows


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _judge(
    own: Any, competitor: Any, higher_is_better: bool | None
) -> tuple[str | None, float | None, str | None]:
    """Returns (winner, delta, delta_label) for one metric row.

    A descriptive field, or one where either side is missing, has no winner at
    all rather than a defaulted one, which is what stops the gap list filling
    up with differences that were never measured.
    """
    if higher_is_better is None:
        return None, None, None

    own_num = _numeric(own)
    competitor_num = _numeric(competitor)
    if own_num is None or competitor_num is None:
        return None, None, None

    delta = round(own_num - competitor_num, 2)
    if abs(delta) < 1e-9:
        return "tie", 0.0, "Level"

    own_wins = (delta > 0) if higher_is_better else (delta < 0)
    winner = "own" if own_wins else "competitor"

    if competitor_num:
        relative = abs(delta) / abs(competitor_num) * 100
        magnitude = f"{abs(delta):,.2f} ({relative:,.0f}%)"
    else:
        magnitude = f"{abs(delta):,.2f}"
    direction = "ahead" if own_wins else "behind"
    return winner, delta, f"You are {magnitude} {direction}"


def build_metric_rows(
    fields: list[str],
    own_meta: dict[str, Any],
    competitor_meta: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in fields:
        label, kind, unit, higher_is_better = FIELD_SPECS.get(
            field, (field.replace("_", " ").title(), "text", None, None)
        )
        own_value = own_meta.get(field)
        competitor_value = competitor_meta.get(field)
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


def derived_for(param_key: str, meta: dict[str, Any]) -> dict[str, Any]:
    """Parameter-specific figures that are not plain metadata reads."""
    if param_key == "pricing":
        price = meta.get("price") or 0
        original = meta.get("original_price")
        return {
            "effective_price": price,
            "absolute_saving": round(original - price, 2) if original and price and original > price else 0,
            "has_discount": bool(meta.get("discount_percent")),
        }
    if param_key == "content_quality":
        return {
            "description_words": meta.get("description_word_count") or 0,
            "spec_lines": meta.get("spec_count") or 0,
            "media_assets": (meta.get("image_count") or 0) + (1 if meta.get("has_video") else 0),
        }
    if param_key == "social_proof":
        rating = meta.get("rating") or 0
        count = meta.get("review_count") or 0
        # Volume-weighted credibility: a 5.0 from 3 buyers is weaker than a 4.6 from 900.
        return {
            "credibility_index": round(rating * min(count, 1000) / 1000, 2),
            "positive_hits": meta.get("review_positive_hits") or 0,
            "negative_hits": meta.get("review_negative_hits") or 0,
        }
    if param_key == "searchability":
        return {
            "keyword_density": meta.get("title_keyword_density") or 0,
            "category_match_score": meta.get("category_tag_match_score") or 0,
        }
    if param_key == "variants":
        return {"option_depth": meta.get("variant_count") or 0}
    if param_key == "availability_trust":
        return {"in_stock": meta.get("stock_status") == "in_stock"}
    if param_key == "promotional_signals":
        signals = ["is_bestseller", "has_bundle", "has_flash_sale", "has_coupon", "warranty_present"]
        return {"active_signals": sum(1 for s in signals if meta.get(s))}
    if param_key == "positioning":
        return {"branded": bool(meta.get("is_branded"))}
    return {}


# ------------------------------------------------------------------ insights


def build_insights(
    param_key: str,
    rows: list[dict[str, Any]],
    own: dict[str, Any],
    competitor: dict[str, Any],
) -> list[str]:
    """Rule-based findings for one parameter group. No LLM involved.

    These are what the Insight Agent promotes into gap descriptions, so they
    are written as statements about the user's listing rather than as neutral
    observations.
    """
    insights: list[str] = []

    wins = [r for r in rows if r["winner"] == "own"]
    losses = [r for r in rows if r["winner"] == "competitor"]
    if wins or losses:
        insights.append(
            f"You lead on {len(wins)} of {len(wins) + len(losses)} comparable metrics in this group."
        )

    if param_key == "pricing":
        own_price, competitor_price = own.get("price"), competitor.get("price")
        if own_price and competitor_price:
            gap = own_price - competitor_price
            if abs(gap) < 0.01:
                insights.append("Both products are priced identically.")
            else:
                pct = abs(gap) / competitor_price * 100
                side = "more expensive" if gap > 0 else "cheaper"
                insights.append(f"You are Rs. {abs(gap):,.0f} ({pct:.0f}%) {side} than the competitor.")
        own_discount = own.get("discount_percent") or 0
        competitor_discount = competitor.get("discount_percent") or 0
        if competitor_discount > own_discount + 5:
            insights.append(
                f"The competitor advertises a deeper discount ({competitor_discount:.0f}% vs your {own_discount:.0f}%), "
                "which reads as better value even at a similar net price."
            )
        if competitor.get("shipping_cost") == 0 and (own.get("shipping_cost") or 0) > 0:
            insights.append("The competitor offers free shipping while yours is paid - a common conversion gap.")

    elif param_key == "positioning":
        if competitor.get("is_branded") and not own.get("is_branded"):
            insights.append("The competitor lists under a brand while yours reads as generic, which usually wins trust.")
        own_words = own.get("title_word_count") or 0
        competitor_words = competitor.get("title_word_count") or 0
        if competitor_words > own_words + 4:
            insights.append(
                f"The competitor's title carries {competitor_words - own_words} more words, capturing more search terms."
            )

    elif param_key == "content_quality":
        own_desc = own.get("description_word_count") or 0
        competitor_desc = competitor.get("description_word_count") or 0
        if competitor_desc > own_desc * 1.3 and competitor_desc > 50:
            insights.append(f"Competitor description is {competitor_desc - own_desc} words longer - more detail to convert on.")
        if (competitor.get("image_count") or 0) > (own.get("image_count") or 0):
            insights.append("The competitor shows more product images.")
        if competitor.get("has_video") and not own.get("has_video"):
            insights.append("The competitor has a product video and you do not - the single cheapest content upgrade here.")

    elif param_key == "social_proof":
        own_reviews = own.get("review_count") or 0
        competitor_reviews = competitor.get("review_count") or 0
        if competitor_reviews > own_reviews * 1.5 and competitor_reviews > 10:
            insights.append(
                f"The competitor has {competitor_reviews - own_reviews:,} more reviews, a substantial social-proof moat."
            )
        own_rating, competitor_rating = own.get("rating"), competitor.get("rating")
        if own_rating and competitor_rating and abs(own_rating - competitor_rating) >= 0.2:
            better = "your" if own_rating > competitor_rating else "the competitor's"
            insights.append(
                f"Ratings differ meaningfully - {better} listing is rated higher "
                f"({max(own_rating, competitor_rating):.1f}/5)."
            )
        if (competitor.get("review_negative_hits") or 0) > (competitor.get("review_positive_hits") or 0):
            insights.append("Competitor reviews skew negative - an angle you can position against.")

    elif param_key == "availability_trust":
        if competitor.get("stock_status") == "out_of_stock":
            insights.append("The competitor is out of stock right now - an immediate demand-capture window.")
        if own.get("stock_status") == "out_of_stock":
            insights.append("Your listing reads as out of stock, which suppresses ranking and conversion.")
        if competitor.get("seller_verified") and not own.get("seller_verified"):
            insights.append("The competitor carries a verified/official-store badge and you do not.")

    elif param_key == "promotional_signals":
        missing = [
            FIELD_SPECS[f][0]
            for f in ("is_bestseller", "has_bundle", "has_coupon", "warranty_present")
            if competitor.get(f) and not own.get(f)
        ]
        if missing:
            insights.append("Competitor-only promotional signals: " + ", ".join(missing) + ".")

    elif param_key == "variants":
        own_variants = own.get("variant_count") or 0
        competitor_variants = competitor.get("variant_count") or 0
        if competitor_variants > own_variants:
            insights.append(
                f"The competitor offers {competitor_variants - own_variants} more variant option(s), "
                "widening their addressable demand."
            )
        elif own_variants > competitor_variants:
            insights.append("You offer more variant choice than the competitor.")

    elif param_key == "searchability":
        own_match = own.get("category_tag_match_score") or 0
        competitor_match = competitor.get("category_tag_match_score") or 0
        if competitor_match > own_match + 10:
            insights.append("The competitor's title aligns more closely with its category tags, helping on-platform search.")
        if (own.get("title_word_count") or 0) < 8:
            insights.append("Your title is short for Daraz search - most ranking titles run 12-20 words.")

    if not insights:
        insights.append("No material difference detected between the two listings on this parameter.")
    return insights


def compare_all(
    own_meta: dict[str, Any], competitor_meta: dict[str, Any]
) -> list[dict[str, Any]]:
    """Every parameter group compared at once.

    Returns one entry per group with its metric rows, derived figures and
    rule-based insights. This is the whole structured-comparison surface the
    Insight Agent works from.
    """
    groups: list[dict[str, Any]] = []
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
            "own_wins": sum(1 for r in rows if r["winner"] == "own"),
            "competitor_wins": sum(1 for r in rows if r["winner"] == "competitor"),
        })
    return groups
