"""Grounded review and B2B comparison to backend-compatible gap records."""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from common import ROOT, load_predictor, review_input, save_json

sys.path.insert(0, str(ROOT.parent / "backend"))
try:
    from app.models.gap import Gap  # noqa: E402
except ModuleNotFoundError:
    from schema_contract import Gap

ASPECTS = {
    "quality/durability": ("quality", "broken", "defect", "durable", "cheap", "material"),
    "battery/performance": ("battery", "performance", "power", "charge"),
    "sizing/wrong_item": ("size", "sizing", "wrong", "fit", "different item"),
    "shipping/delivery": ("shipping", "delivery", "late", "delay", "arrived"),
    "packaging": ("packaging", "package", "box", "packed"),
    "supplier_communication": ("supplier", "communication", "response", "reply", "seller"),
    "pricing/value": ("price", "expensive", "cost", "value", "overpriced"),
    "listing_mismatch": ("description", "photo", "picture", "advertised", "listing"),
}
ASPECT_CATEGORY = {"quality/durability": "content", "battery/performance": "content", "sizing/wrong_item": "content",
                   "shipping/delivery": "conversion", "packaging": "conversion", "supplier_communication": "positioning",
                   "pricing/value": "pricing", "listing_mismatch": "content"}


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def get(product, field):
    value = product.get(field)
    return value if value is not None else product.get("raw_metadata", {}).get(field)


def source(product, quote, relevance=1.0):
    return {"source_id": str(product.get("source_id") or product.get("id") or "unknown"),
            "source_url": str(product.get("url") or ""), "source_title": str(product.get("product_name") or "Unknown listing"),
            "quote": str(quote), "relevance": float(relevance)}


def reviews(product):
    # The live Alibaba scraper does not emit reviews. Accept attached review text only.
    field = (product.get("text_fields") or {}).get("review")
    raw = (product.get("raw_metadata") or {}).get("reviews")
    if isinstance(raw, list):
        return [str(item.get("review_text") or item.get("text") or "") if isinstance(item, dict) else str(item) for item in raw]
    if isinstance(field, list):
        return [str(item) for item in field]
    if isinstance(field, str) and field.strip():
        return [line.strip() for line in field.splitlines() if line.strip()]
    return []


def pain_points(texts):
    if not texts:
        return {}
    all_text = " ".join(texts).lower()
    aspects = {aspect: sum(all_text.count(term) for term in terms) for aspect, terms in ASPECTS.items()}
    aspects = {key: value for key, value in aspects.items() if value}
    if len(texts) >= 2:
        try:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(2, 3), max_features=100)
            matrix = vectorizer.fit_transform(texts)
            phrases = sorted(zip(vectorizer.get_feature_names_out(), matrix.mean(axis=0).A1), key=lambda pair: -pair[1])[:5]
            aspects["keyphrases"] = [term for term, _ in phrases]
        except ValueError:
            pass
    return aspects


class AlibabaGapAnalyzer:
    def __init__(self, predictor=None):
        self.predictor = predictor

    def _make_gap(self, own, title, description, category, priority, confidence, evidence, opportunity):
        payload = {"id": f"gap_{uuid4().hex}", "project_id": str(own.get("project_id") or "demo_project"),
                   "title": title, "description": description, "category": category, "priority": priority,
                   "confidence": round(max(0, min(1, confidence)), 3), "evidence": evidence,
                   "opportunity": opportunity, "created_at": datetime.now(timezone.utc).isoformat()}
        if not evidence or not all(item["quote"].strip() for item in evidence):
            raise ValueError("Every gap requires quoted source evidence")
        return Gap.model_validate(payload).model_dump(mode="json", by_alias=False)

    def _metric(self, own, competitor, field, lower, category, title, opportunity, unit=""):
        a, b = number(get(own, field)), number(get(competitor, field))
        if a is None or b is None or (a <= b if lower else a >= b):
            return None
        delta = abs(a - b)
        quote = f"Own {field}: {a:g}{unit}; competitor {field}: {b:g}{unit}; difference: {delta:g}{unit}."
        magnitude = delta / max(abs(b), 1)
        return self._make_gap(own, title, f"The competitor leads on {field} by {delta:g}{unit}.", category,
                              "high" if magnitude >= .3 else "medium", min(.95, .7 + magnitude / 5),
                              [source(own, quote), source(competitor, quote)], opportunity)

    def _review_gaps(self, own, competitor):
        if self.predictor is None:
            return []
        result = []
        for side, product in (("own", own), ("competitor", competitor)):
            texts = [text for text in reviews(product) if len(text.split()) >= 3]
            if not texts:
                continue
            predictions = self.predictor([review_input(text, get(product, "category"), product.get("product_name")) for text in texts])
            negative = [(text, pred) for text, pred in zip(texts, predictions) if pred["label"] in (1, 2)]
            if not negative:
                continue
            extracted = pain_points([text for text, _ in negative])
            for aspect in ASPECTS:
                matches = [(text, pred) for text, pred in negative if any(term in text.lower() for term in ASPECTS[aspect])]
                if not matches:
                    continue
                text, pred = max(matches, key=lambda pair: pair[1]["confidence"])
                priority = "high" if len(matches) >= 2 or pred["label"] == 2 else "medium"
                title = f"{'Address own' if side == 'own' else 'Exploit competitor'} {aspect.replace('_', ' ')} complaints"
                phrases = ", ".join(extracted.get("keyphrases", [])[:3])
                description = f"{len(matches)} of {len(texts)} attached {side} reviews mention {aspect.replace('_', ' ')} and were classified as gaps. Extracted phrases: {phrases or 'none'}."
                opportunity = (f"Investigate the {aspect.replace('_', ' ')} issue and update the product or listing with evidence of the fix."
                               if side == "own" else f"Show verified strengths in {aspect.replace('_', ' ')} in your listing copy and comparison messaging.")
                result.append(self._make_gap(own, title, description, ASPECT_CATEGORY[aspect], priority,
                                             min(.95, pred["confidence"] * min(1, .7 + .1 * len(matches))),
                                             [source(product, text, pred["confidence"])], opportunity))
        return result

    def compare(self, own, competitor):
        if own.get("platform") != "alibaba" or competitor.get("platform") != "alibaba":
            raise ValueError("Both products must use platform=alibaba")
        if own.get("role") != "own" or competitor.get("role") != "competitor":
            raise ValueError("Expected own and competitor roles")
        result = self._review_gaps(own, competitor)
        comparisons = [
            ("price", True, "pricing", "Competitor has a lower unit price", "Review pricing or show a documented value advantage."),
            ("max_price", True, "pricing", "Competitor has a lower starting price", "Review the lowest-volume price tier."),
            ("moq", True, "conversion", "Competitor has a lower minimum order", "Offer a smaller trial order if commercially feasible."),
            ("lead_time_days", True, "conversion", "Competitor delivers sooner", "Improve fulfillment speed or clearly explain the lead time."),
            ("image_count", False, "content", "Competitor shows more product images", "Add clear product, detail, and scale images."),
            ("content_completeness_score", False, "content", "Competitor listing is more complete", "Fill missing product attributes and media."),
            ("rating", False, "social_engagement", "Competitor has a higher rating", "Investigate customer feedback and improve the underlying experience."),
            ("review_count", False, "social_engagement", "Competitor has more review evidence", "Request authentic post-purchase reviews."),
        ]
        for field, lower, category, title, opportunity in comparisons:
            if field in {"price", "max_price"} and str(own.get("currency")) != str(competitor.get("currency")):
                continue
            gap = self._metric(own, competitor, field, lower, category, title, opportunity)
            if gap:
                result.append(gap)
        own_supplier, other_supplier = own.get("supplier") or {}, competitor.get("supplier") or {}
        for field in ("verified", "gold_supplier", "trade_assurance"):
            if other_supplier.get(field) is True and own_supplier.get(field) is False:
                quote = f"Own {field}: false; competitor {field}: true."
                result.append(self._make_gap(own, f"Competitor displays {field.replace('_', ' ')}", "The competitor shows a supplier trust credential absent from the own listing.",
                                             "positioning", "medium", .9, [source(own, quote), source(competitor, quote)],
                                             f"Obtain and display {field.replace('_', ' ')} if eligible; otherwise strengthen other verifiable trust signals."))
        for field in ("response_rate", "years_on_platform"):
            a, b = number(own_supplier.get(field)), number(other_supplier.get(field))
            if a is not None and b is not None and a < b:
                quote = f"Own supplier {field}: {a:g}; competitor supplier {field}: {b:g}."
                result.append(self._make_gap(own, f"Competitor leads on supplier {field.replace('_', ' ')}", quote,
                                             "positioning", "low", .85, [source(own, quote), source(competitor, quote)],
                                             "Improve supplier responsiveness or highlight other verified strengths."))
        # Compare equivalent quantity tiers only where both have a price at the same threshold.
        for own_tier in own.get("price_tiers") or []:
            quantity = number(own_tier.get("min_quantity"))
            peer = next((tier for tier in competitor.get("price_tiers") or [] if number(tier.get("min_quantity")) == quantity), None)
            if peer and number(own_tier.get("price")) is not None and number(peer.get("price")) is not None and number(own_tier["price"]) > number(peer["price"]):
                quote = f"At {int(quantity)} units, own price {own_tier['price']} vs competitor {peer['price']} ({own_tier.get('currency', own.get('currency', ''))})."
                result.append(self._make_gap(own, f"Higher price at {int(quantity)} units", quote, "pricing", "medium", .9,
                                             [source(own, quote), source(competitor, quote)], "Review this volume tier or demonstrate a verified value advantage."))
        own_desc = str((own.get("text_fields") or {}).get("description") or "")
        other_desc = str((competitor.get("text_fields") or {}).get("description") or "")
        if len(own_desc.split()) < 20 and len(other_desc.split()) >= 20:
            quote = f"Own description: {len(own_desc.split())} words; competitor description: {len(other_desc.split())} words."
            result.append(self._make_gap(own, "Own product description is thin", quote, "seo", "medium", .8,
                                         [source(own, quote), source(competitor, quote)], "Add factual specifications, uses, and buyer questions to the description."))
        return result


def validation_product(row, role, reviews_frame):
    item_id = str(row.item_id)
    matches = reviews_frame[reviews_frame.item_id.astype(str) == item_id]
    return {"id": item_id, "project_id": "alibaba_validation_demo", "source_id": item_id,
            "platform": "alibaba", "role": role, "url": row.url, "product_name": row.title,
            "category": row.top_category, "price": number(row.price_usd), "currency": "USD",
            "rating": number(row.star_rating) if number(row.star_rating) and number(row.review_count) else None,
            "review_count": int(row.review_count), "text_fields": {"title": row.title, "description": str(row.description),
            "review": "\n".join(matches.review_text.astype(str))}, "raw_metadata": {}, "price_tiers": [], "supplier": None}


def sample_comparison():
    products = pd.read_csv(ROOT / "data/alibaba_validation/alibaba_products_validation.csv", dtype={"item_id": str}).fillna("")
    reviews_frame = pd.read_csv(ROOT / "data/alibaba_validation/alibaba_reviews_validation.csv", dtype={"item_id": str}).fillna("")
    candidates = products[products.item_id.isin(reviews_frame.item_id)].reset_index(drop=True)
    if len(candidates) < 2:
        raise RuntimeError("Need two validation products with reviews")
    similarity = cosine_similarity(TfidfVectorizer(stop_words="english").fit_transform(candidates.title.fillna("")))
    pairs = [(similarity[i, j], i, j) for i in range(len(candidates)) for j in range(i + 1, len(candidates))
             if candidates.at[i, "top_category"] == candidates.at[j, "top_category"]
             and candidates.at[i, "sub_category"] == candidates.at[j, "sub_category"]
             and number(candidates.at[i, "price_usd"]) is not None
             and number(candidates.at[j, "price_usd"]) is not None
             and number(candidates.at[i, "price_usd"]) != number(candidates.at[j, "price_usd"])]
    if not pairs:
        raise RuntimeError("Need two comparable validation products with reviews")
    _, i, j = max(pairs)
    high, low = sorted((candidates.iloc[i], candidates.iloc[j]), key=lambda row: number(row.price_usd), reverse=True)
    own = validation_product(high, "own", reviews_frame)
    competitor = validation_product(low, "competitor", reviews_frame)
    model_ready = (ROOT / "artifacts/model/config.json").exists()
    predictor = load_predictor() if model_ready else None
    output = {"own": own, "competitor": competitor, "review_model_status": "fine-tuned" if model_ready else "pending training",
              "gaps_opportunities": AlibabaGapAnalyzer(predictor).compare(own, competitor)}
    save_json(ROOT / "artifacts/reports/sample_comparison_output.json", output)
    return output


if __name__ == "__main__":
    print(json.dumps(sample_comparison(), indent=2))
