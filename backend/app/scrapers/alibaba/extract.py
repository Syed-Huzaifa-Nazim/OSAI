"""Turning one Alibaba listing offer into a product record.

Everything here is pure: an offer dict in, text fields / metadata / images /
price tiers / supplier profile out. No network, so it is exercised directly by
tests against real (sanitised) listing data.

Only the fields named in selectors.OFFER_PATHS are ever read. Supplier contact
routes, chat tokens and click-tracking links are never touched.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import selectors as S
from .images import ProductImage, extract_images
from .urls import absolute_url

#: Text fields that become their own embedded chunks. Alibaba's listing carries
#: no description or review text, so these are what it does have.
TEXT_FIELD_TYPES = ["title", "specs", "promo_tags", "order_terms", "supplier"]

_NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
# Prices in a range label ("$0.75-0.77") are never negative; the hyphen is the
# range separator, not a minus sign.
_PRICE_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class ExtractedProduct:
    text_fields: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    images: List[ProductImage] = field(default_factory=list)
    #: {"min_quantity", "max_quantity" (None = open-ended), "price", "currency", "unit"}
    price_tiers: List[Dict[str, Any]] = field(default_factory=list)
    supplier: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)


# --------------------------------------------------------------- helpers


def _get(offer: Dict[str, Any], key: str) -> Any:
    """First non-empty value among the dotted paths configured for `key`."""
    for path in S.OFFER_PATHS.get(key, []):
        node: Any = offer
        for part in path.split("."):
            node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                break
        if node not in (None, "", [], {}):
            return node
    return None


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html_lib.unescape(str(value))
    text = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", text.replace("\xa0", " ")).strip()


def to_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMBER_RE.search(str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def to_int(value: Any) -> Optional[int]:
    number = to_float(value)
    return int(number) if number is not None else None


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(value.strip())
    return out


def _money(value: Optional[float], currency: str) -> str:
    if value is None:
        return "not stated"
    symbol = "US$" if currency == "USD" else f"{currency} "
    return f"{symbol}{value:,.4f}".rstrip("0").rstrip(".") if value < 1 else f"{symbol}{value:,.2f}"


def _money_range(low: Optional[float], high: Optional[float], currency: str) -> str:
    if low is None:
        return "not stated"
    if high is None or abs(high - low) < 1e-9:
        return _money(low, currency)
    return f"{_money(low, currency)} - {_money(high, currency)}"


def unit_key(unit: Any) -> str:
    """'Pieces' and 'piece' are the same unit; 'boxes' and 'box' too."""
    word = str(unit or "").strip().lower()
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and word[:-2].endswith(("x", "s", "ch", "sh")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
        return word[:-1]
    return word


def plural_unit(unit: Any) -> str:
    """'piece' -> 'pieces', 'box' -> 'boxes'; a unit already plural is unchanged.

    A metric row carries one unit for both listings, so quantity units are sent
    in the plural and the page writes the singular for a quantity of one.
    """
    word = str(unit or "").strip().lower()
    if not word or unit_key(word) != word:
        return word
    if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    if word.endswith(("x", "s", "ch", "sh")):
        return word + "es"
    return word + "s"


# ------------------------------------------------------------------ parts


def _price_tiers(offer: Dict[str, Any], currency: str, fallback_unit: Optional[str]) -> List[Dict[str, Any]]:
    """Quantity price breaks, lowest quantity first.

    `quantityMax: -1` marks the open-ended top tier ("1000+"), stored as None.
    """
    raw = _get(offer, "quantity_prices")
    tiers: List[Dict[str, Any]] = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        price = to_float(entry.get("price"))
        minimum = to_int(entry.get("quantityMin"))
        if price is None or minimum is None or minimum < 1:
            continue
        maximum = to_int(entry.get("quantityMax"))
        if maximum is not None and (maximum < 0 or maximum < minimum):
            maximum = None
        unit = clean_text(entry.get("unit")) or fallback_unit
        tiers.append({
            "min_quantity": minimum,
            "max_quantity": maximum,
            "price": round(price, 4),
            "currency": currency,
            "unit": unit.lower() if unit else None,
        })
    return _unique_by_quantity(tiers)


def _unique_by_quantity(tiers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sorted, one row per starting quantity, so the table's order is well defined."""
    unique: List[Dict[str, Any]] = []
    for tier in sorted(tiers, key=lambda tier: tier["min_quantity"]):
        if not unique or unique[-1]["min_quantity"] != tier["min_quantity"]:
            unique.append(tier)
    return unique


def _align_tiers_to_moq(
    tiers: List[Dict[str, Any]], moq: Optional[int], moq_unit: Optional[str]
) -> List[Dict[str, Any]]:
    """Start the ladder at the minimum order.

    Single-price listings publish one placeholder tier from quantity 1 even when
    the minimum order is 500 ("1+ units" next to "Min. order: 500 units").
    Nothing below the minimum can be ordered, so a tier ending under it is
    dropped and one straddling it starts at it. Left alone when the two are
    counted in different units, since then they cannot be compared.
    """
    if not tiers or not moq:
        return tiers
    tier_unit = tiers[0]["unit"]
    if tier_unit and moq_unit and unit_key(tier_unit) != unit_key(moq_unit):
        return tiers
    aligned = [
        {**tier, "min_quantity": max(tier["min_quantity"], moq)}
        for tier in tiers
        if tier["max_quantity"] is None or tier["max_quantity"] >= moq
    ]
    return _unique_by_quantity(aligned) if aligned else tiers


def _promotion(
    offer: Dict[str, Any], list_low: Optional[float], list_high: Optional[float]
) -> Optional[Dict[str, float]]:
    """The live prices while a promotion runs, or None.

    During a promotion Alibaba keeps the list range in originalPriceFrom/To (and
    the top-level `price`), publishes the discounted range separately, and
    leaves the quantity ladder at list prices.
    """
    if not to_bool(_get(offer, "promotion_active")):
        return None
    original_low = to_float(_get(offer, "list_price_min")) or list_low
    original_high = to_float(_get(offer, "list_price_max")) or list_high or original_low
    live_low = to_float(_get(offer, "promotion_price_min"))
    live_high = to_float(_get(offer, "promotion_price_max"))
    if not original_low or live_low is None or not 0 <= live_low < original_low:
        return None
    if live_high is None or live_high < live_low:
        live_high = live_low
    discount = to_float(_get(offer, "promotion_discount"))
    if discount is None or not 0 < discount < 100:
        discount = (original_low - live_low) / original_low * 100
    return {
        "price": live_low,
        "max_price": live_high,
        "original_price": original_low,
        "original_max_price": original_high,
        "discount_percent": round(discount, 2),
    }


def _live_price(list_price: float, promotion: Optional[Dict[str, float]]) -> float:
    """What a list price costs while the promotion runs.

    The ends of the ladder map onto the range Alibaba publishes, exactly; a
    middle tier gets the same proportional discount.
    """
    if not promotion:
        return list_price
    if abs(list_price - promotion["original_price"]) < 1e-9:
        return promotion["price"]
    if abs(list_price - promotion["original_max_price"]) < 1e-9:
        return promotion["max_price"]
    return round(list_price * promotion["price"] / promotion["original_price"], 4)


def _moq(offer: Dict[str, Any]) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """'100 pieces' -> (100, 'pieces', '100 pieces')."""
    label = clean_text(_get(offer, "moq_label")) or None
    quantity = to_int(label) if label else None
    if quantity is None:
        quantity = to_int(_get(offer, "moq_number"))
    unit = None
    if label:
        match = re.match(r"\s*[\d,.]+\s*(.*)$", label)
        unit = (match.group(1).strip().lower() or None) if match else None
    return quantity, unit, label


def _lead_time(offer: Dict[str, Any]) -> Tuple[Optional[int], Optional[str]]:
    """Dispatch time in days, from the buyer-facing label when there is one."""
    label = clean_text(_get(offer, "dispatch_label")) or None
    days = to_int(label) if label else None
    if days is None:
        days = to_int(_get(offer, "process_days"))
        if days is not None and days < 0:
            days = None
        if days is not None and not label:
            label = f"{days}-day processing"
    return days, label


def _attributes(offer: Dict[str, Any]) -> List[Tuple[str, str]]:
    raw = _get(offer, "attributes")
    pairs: List[Tuple[str, str]] = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        name = clean_text(entry.get("name") or entry.get("originalName"))
        value = clean_text(entry.get("value"))
        if name and value:
            pairs.append((name, value))
    return pairs


def _promotion_tags(offer: Dict[str, Any]) -> List[str]:
    raw = _get(offer, "promotion_tags")
    names = [clean_text(tag.get("name")) for tag in raw if isinstance(tag, dict)] if isinstance(raw, list) else []
    return _dedupe(name for name in names if name)


def _supplier(offer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Public trust credentials only. No contact route of any kind."""
    name = clean_text(_get(offer, "supplier_name")) or None
    if not name:
        return None
    response_rate = to_float(_get(offer, "response_rate"))
    if response_rate is not None and not 0 <= response_rate <= 100:
        response_rate = None
    gmv_label = clean_text(_get(offer, "historic_gmv")) or None
    return {
        "name": name,
        "country_code": clean_text(_get(offer, "supplier_country_code")).upper() or None,
        "country_name": clean_text(_get(offer, "supplier_country")) or None,
        "years_on_platform": to_int(_get(offer, "supplier_years")),
        "gold_supplier": to_bool(_get(offer, "gold_supplier")),
        "verified": to_bool(_get(offer, "verified_supplier")),
        "trade_assurance": to_bool(_get(offer, "trade_assurance")),
        "transaction_level": to_int(_get(offer, "transaction_level")),
        "response_rate": round(response_rate, 2) if response_rate is not None else None,
        "historic_order_count": to_int(_get(offer, "historic_order_count")),
        "historic_gmv_label": gmv_label,
        "historic_gmv_min": to_float(gmv_label) if gmv_label else None,
        "main_products": clean_text(_get(offer, "main_products")) or None,
    }


# ------------------------------------------------------------------- main


def extract_offer(offer: Dict[str, Any], *, from_page_data: bool = True) -> ExtractedProduct:
    """Everything the comparison needs from one listing offer."""
    product = ExtractedProduct()
    meta = product.metadata

    title = clean_text(_get(offer, "title"))
    currency = (clean_text(_get(offer, "currency")) or "USD").upper()
    price_unit = clean_text(_get(offer, "price_unit")).lower() or None

    # --- pricing ------------------------------------------------------------
    moq, moq_unit, moq_label = _moq(offer)
    tiers = _align_tiers_to_moq(_price_tiers(offer, currency, price_unit), moq, moq_unit)
    product.price_tiers = tiers
    tier_prices = [tier["price"] for tier in tiers]
    price_label = clean_text(_get(offer, "price_label")) or None

    # The published range is authoritative: on a listing with variants it spans
    # every variant, while the quantity ladder can describe just one of them.
    # The ladder fills in only when no range is published.
    list_price = to_float(_get(offer, "price_min"))
    list_max = to_float(_get(offer, "price_max"))
    if list_price is None and tier_prices:
        list_price = min(tier_prices)
    if list_max is None and tier_prices:
        list_max = max(tier_prices)
    if list_price is None and price_label:
        numbers = [to_float(n) for n in _PRICE_RE.findall(price_label)]
        numbers = [n for n in numbers if n is not None]
        if numbers:
            list_price, list_max = min(numbers), max(numbers)
    if list_max is not None and list_price is not None and list_max < list_price:
        list_price, list_max = list_max, list_price

    # `price` is what a buyer pays today: the promotion range while one runs,
    # with the list price kept as the crossed-out original.
    promotion = _promotion(offer, list_price, list_max)
    price, max_price = (promotion["price"], promotion["max_price"]) if promotion else (list_price, list_max)

    meta["currency"] = currency
    meta["price"] = round(price, 4) if price is not None else None
    meta["max_price"] = round(max_price, 4) if max_price is not None else None
    meta["original_price"] = round(promotion["original_price"], 4) if promotion else None
    meta["discount_percent"] = promotion["discount_percent"] if promotion else None
    meta["price_unit"] = price_unit
    if promotion:
        meta["price_range_label"] = (
            f"{_money_range(price, max_price, currency)} on promotion "
            f"(list {price_label or _money_range(list_price, list_max, currency)})"
        )
    else:
        meta["price_range_label"] = price_label or _money_range(price, max_price, currency)

    # --- order terms ----------------------------------------------------------
    lead_days, lead_label = _lead_time(offer)
    first_tier = tiers[0] if tiers else None
    best_tier = min(tiers, key=lambda tier: (tier["price"], tier["min_quantity"])) if tiers else None
    meta["moq"] = moq
    meta["moq_unit"] = moq_unit
    meta["moq_label"] = moq_label or "not stated"
    meta["price_tier_count"] = len(tiers)
    meta["first_tier_price"] = _live_price(first_tier["price"], promotion) if first_tier else meta["price"]
    meta["best_tier_price"] = _live_price(best_tier["price"], promotion) if best_tier else meta["price"]
    meta["best_tier_min_quantity"] = best_tier["min_quantity"] if best_tier else moq
    meta["bulk_discount_percent"] = (
        round((first_tier["price"] - best_tier["price"]) / first_tier["price"] * 100, 2)
        if first_tier and best_tier and first_tier["price"] > 0
        else 0.0
    )
    meta["lead_time_days"] = lead_days
    meta["lead_time_label"] = lead_label or "not stated"
    meta["buy_now_available"] = to_bool(_get(offer, "buy_now"))

    # --- social proof -------------------------------------------------------
    review_count = to_int(_get(offer, "review_count")) or 0
    score = to_float(_get(offer, "review_score"))
    meta["review_count"] = max(review_count, 0)
    # A score with no reviews behind it is Alibaba's placeholder, not a rating.
    meta["rating"] = round(score, 2) if score is not None and 0 < score <= 5 and review_count > 0 else None

    # --- content ------------------------------------------------------------
    images = extract_images(_get(offer, "images"), _get(offer, "big_image"))
    product.images = images
    attributes = _attributes(offer)
    meta["image_count"] = len(images)
    meta["has_video"] = to_bool(_get(offer, "has_video"))
    meta["spec_count"] = len(attributes)

    brand = next((value for name, value in attributes if name.lower() in S.BRAND_ATTRIBUTE_NAMES), "")
    meta["brand"] = brand or "No Brand"
    meta["is_branded"] = bool(brand) and brand.strip().lower() not in S.GENERIC_BRANDS

    # --- promotion ------------------------------------------------------------
    tags = _promotion_tags(offer)
    meta["promo_tags"] = ", ".join(tags) if tags else "none"
    meta["promo_tag_count"] = len(tags)
    meta["ready_to_ship"] = any(tag.lower() == S.PROMOTION_TAG_READY_TO_SHIP for tag in tags)
    meta["has_campaign_tag"] = any(tag.lower() != S.PROMOTION_TAG_READY_TO_SHIP for tag in tags)
    meta["sponsored"] = to_bool(_get(offer, "sponsored")) or clean_text(_get(offer, "item_type")).lower() == "p4p"

    # --- customisation ------------------------------------------------------
    custom_blob = " ".join([title.lower()] + [f"{n} {v}".lower() for n, v in attributes])
    signals = [keyword for keyword in S.CUSTOMIZATION_KEYWORDS if keyword in custom_blob]
    meta["customizable"] = bool(signals)
    meta["customization_signals"] = ", ".join(_dedupe(signals)) if signals else "none"
    meta["variant_count"] = None  # not published on the listing surface

    # --- title / search ------------------------------------------------------
    words = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in S.TITLE_STOPWORDS]
    unique_words = set(words)
    title_word_total = len(title.split())
    meta["title_length"] = len(title)
    meta["title_word_count"] = title_word_total
    meta["title_keyword_count"] = len(unique_words)
    meta["title_keyword_density"] = round(len(unique_words) / title_word_total * 100, 2) if title_word_total else 0.0
    meta["title_top_keywords"] = ", ".join(sorted(unique_words, key=len, reverse=True)[:8])
    attribute_words = {
        w for _, value in attributes for w in re.findall(r"[a-z0-9]+", value.lower()) if w not in S.TITLE_STOPWORDS
    }
    overlap = len(unique_words & attribute_words)
    match_score = round(overlap / len(attribute_words) * 100, 2) if attribute_words else 0.0
    meta["title_attribute_match_score"] = match_score
    meta["title_attribute_match"] = (
        "unknown" if not attribute_words else "high" if match_score >= 50 else "medium" if match_score >= 20 else "low"
    )

    # --- supplier -----------------------------------------------------------
    supplier = _supplier(offer)
    product.supplier = supplier
    supplier = supplier or {}
    meta["seller_name"] = supplier.get("name") or "Unknown supplier"
    meta["supplier_name"] = supplier.get("name") or "Unknown supplier"
    meta["supplier_country"] = supplier.get("country_name") or "Unknown"
    meta["supplier_years"] = supplier.get("years_on_platform")
    meta["gold_supplier"] = bool(supplier.get("gold_supplier"))
    meta["verified_supplier"] = bool(supplier.get("verified"))
    meta["trade_assurance"] = bool(supplier.get("trade_assurance"))
    meta["transaction_level"] = supplier.get("transaction_level")
    meta["response_rate_percent"] = supplier.get("response_rate")
    meta["historic_order_count"] = supplier.get("historic_order_count")
    meta["historic_gmv_label"] = supplier.get("historic_gmv_label") or "not stated"
    meta["historic_gmv_min"] = supplier.get("historic_gmv_min")

    # --- identity -------------------------------------------------------------
    meta["item_id"] = str(_get(offer, "id") or "")
    meta["category_id"] = str(_get(offer, "category_id") or "") or None
    meta["listing_url"] = absolute_url(_get(offer, "product_url"))

    # --- a simple 0-100 completeness score for the Content Quality lens ------
    checks = [
        meta["image_count"] >= 5,
        meta["has_video"],
        meta["spec_count"] >= 3,
        meta["review_count"] > 0,
        meta["ready_to_ship"],
        meta["price_tier_count"] >= 2,
    ]
    meta["content_completeness_score"] = round(sum(bool(c) for c in checks) / len(checks) * 100, 1)

    # --- text fields ------------------------------------------------------------
    product.text_fields = {
        "title": title or "Title not found",
        "specs": "\n".join(f"- {name}: {value}" for name, value in attributes)
        or "No specification attributes are listed for this product.",
        "promo_tags": "\n".join(tags) or "No promotional badges on this listing.",
        "order_terms": _order_terms_text(meta, tiers),
        "supplier": _supplier_text(supplier) if supplier else "No supplier profile is shown for this listing.",
    }
    for field_type in TEXT_FIELD_TYPES:
        meta[f"{field_type}_chars"] = len(product.text_fields[field_type])

    if not from_page_data:
        product.warnings.append(
            "Alibaba's product data was read from the page layout rather than its embedded data, "
            "so price tiers, supplier credentials and specifications may be missing."
        )
    if not images:
        product.warnings.append("No product images were found on this listing.")
    return product


def _order_terms_text(meta: Dict[str, Any], tiers: List[Dict[str, Any]]) -> str:
    currency = meta["currency"]
    lines = [f"Minimum order quantity: {meta['moq_label']}"]
    if tiers:
        lines.append("Quantity price breaks:" if not meta["discount_percent"] else "Quantity price breaks (list prices):")
        for tier in tiers:
            upper = f"-{tier['max_quantity']:,}" if tier["max_quantity"] else "+"
            unit = f" {tier['unit']}" if tier["unit"] else ""
            lines.append(f"- {tier['min_quantity']:,}{upper}{unit}: {_money(tier['price'], currency)}")
    if meta["discount_percent"]:
        lines.append(f"Promotion: {meta['discount_percent']:g}% off list prices right now")
    lines.append(f"Price range: {meta['price_range_label']}")
    lines.append(f"Dispatch: {meta['lead_time_label']}")
    lines.append(f"Buy online: {'available' if meta['buy_now_available'] else 'inquiry only'}")
    return "\n".join(lines)


def _supplier_text(supplier: Dict[str, Any]) -> str:
    badges = [
        label for label, on in (
            ("Gold Supplier", supplier.get("gold_supplier")),
            ("Verified supplier", supplier.get("verified")),
            ("Trade Assurance", supplier.get("trade_assurance")),
        ) if on
    ]
    parts = [f"{supplier['name']}" + (f" ({supplier['country_name']})" if supplier.get("country_name") else "")]
    if supplier.get("years_on_platform") is not None:
        parts.append(f"{supplier['years_on_platform']} years on Alibaba")
    parts.append(", ".join(badges) if badges else "No Gold, Verified or Trade Assurance badge")
    if supplier.get("transaction_level") is not None:
        parts.append(f"Transaction level {supplier['transaction_level']}")
    if supplier.get("response_rate") is not None:
        parts.append(f"Response rate {supplier['response_rate']}%")
    if supplier.get("historic_order_count") is not None:
        gmv = f" ({supplier['historic_gmv_label']})" if supplier.get("historic_gmv_label") else ""
        parts.append(f"{supplier['historic_order_count']:,} past orders{gmv}")
    if supplier.get("main_products"):
        parts.append(f"Main products: {supplier['main_products']}")
    return ". ".join(parts) + "."
