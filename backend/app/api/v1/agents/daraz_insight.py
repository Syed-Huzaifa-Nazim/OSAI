"""Stage 4 for Daraz: the data-based Daraz Gap Engine (app/analysis/daraz/engine.py).

It reads, for both listings: the page (already scraped in stage 2), the listing's own search result (price,
discount, badges, number sold), its rank for the matching search word, its newest reviews (read with the team's
review model) and what its main photo shows (our Model D). Then the engine keeps only gaps that pass its five checks.
Falls back to the arithmetic e-commerce comparison when the Daraz evidence file is missing.
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
import time
from typing import Any

import requests

from app.analysis.daraz import engine, reviews
from app.api.v1.agents.base import AgentResult, BaseAgent
from app.api.v1.agents.ecommerce_insight import EcommerceInsightAgent
from app.services import jobs
from app.scrapers import COMPETITOR, OWN
from app.scrapers.daraz import search

logger = logging.getLogger("optistratix.agents.insight.daraz")


def _photo_tags(url: str | None) -> dict[str, Any]:
    if not url:
        return {}
    try:
        from PIL import Image

        from app.analysis.instagram.content_layer import picture_tags

        r = requests.get(url if url.startswith("http") else "https:" + url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        im.thumbnail((512, 512))
        tag = picture_tags([im])[0]
        return {"photo_worn": tag["shown"] == "worn", "photo_face": bool(tag["face"])}
    except Exception as exc:  # noqa: BLE001 - one photo must not stop the analysis
        logger.warning("Photo tag failed for %s: %s", url, exc)
        return {}


def _side(product: dict[str, Any], live: list[dict[str, Any]]) -> dict[str, Any]:
    meta = product.get("raw_metadata") or {}
    url = product.get("url") or meta.get("product_url") or ""
    item_id = str(meta.get("item_id") or search.item_id_of(url) or "")
    title = product.get("product_name") or meta.get("product_name") or ""
    row = next((r for r in live if r["item_id"] == item_id), None)
    rank = row["rank"] if row else None
    if row is None:
        row = search.find(item_id, title)
    row = row or {}
    side: dict[str, Any] = {
        "item_id": item_id, "url": url, "title": title, "rank": rank,
        # The sale price buyers see: from search. The page alone only has the price before discount, which would
        # make a listing look dearer than it is, so then the price is left unknown (the price check is skipped).
        "price": row.get("price") or (None if str(meta.get("price_source") or "").startswith("price before discount")
                                      else meta.get("price")), "discount_pct": row.get("discount_pct", meta.get("discount_percent") or 0) or 0,
        "sold": row.get("sold", meta.get("sold")), "rating": row.get("rating", meta.get("rating")),
        "review_count": row.get("reviews", meta.get("review_count")),
        "image_count": meta.get("image_count"), "description_words": meta.get("description_word_count"),
        "bullet_count": meta.get("bullet_count") or 0, "variant_count": meta.get("variant_count") or 0,
        "description": ((product.get("text_fields") or {}).get("description") or "")[:5000],
    }
    side["has_discount"] = (side["discount_pct"] or 0) > 0
    for key in ("free_shipping", "voucher", "coins", "daraz_choice"):
        side[key] = row.get(key, meta.get(key))
    image = row.get("image") or meta.get("search_image") or meta.get("main_image") or (meta.get("images") or [None])[0]
    side["image"] = ("https:" + image) if isinstance(image, str) and image.startswith("//") else image
    side.update(_photo_tags(side["image"]))
    raw_reviews = search.reviews(item_id, url) if item_id else []
    side["analysed_reviews"] = reviews.analyse([r["text"] for r in raw_reviews])
    side["seller_replies"] = sum(r["seller_reply"] for r in raw_reviews)
    return side


class DarazInsightAgent(BaseAgent):
    name = "Gap Engine (Daraz)"
    stage = 4
    is_live = True

    async def run(self, context: dict[str, Any]) -> AgentResult:
        if not engine.available():
            return await EcommerceInsightAgent().run(context)
        started = time.perf_counter()
        project_id: str = context["project_id"]
        products: list[dict[str, Any]] = context.get("ecommerce_products", [])
        own = next((p for p in products if p.get("role") == OWN), None)
        rivals = [p for p in products if p.get("role") == COMPETITOR]
        if own is None or not rivals:
            return AgentResult(payload=[], warnings=["Need both your listing and at least one competitor's to compare."],
                               duration_ms=self._elapsed_ms(started))
        gaps, analyses, warnings = [], [], []
        own_title = own.get("product_name") or ""
        ids = {str((p.get("raw_metadata") or {}).get("item_id") or search.item_id_of(p.get("url") or "")) for p in [own, *rivals]}
        # The search word: a dataset word that matches the title, preferring one where a compared listing really ranks.
        candidates = engine.candidate_words(own_title) or engine.candidate_words(rivals[0].get("product_name") or "")
        word, live = None, []
        for cand in candidates[:6]:
            jobs.checkpoint(project_id)
            rows = await asyncio.to_thread(search.search, cand, 2)
            if word is None or any(r["item_id"] in ids for r in rows):
                word, live = cand, rows
            if any(r["item_id"] in ids for r in rows):
                break
        query = word or " ".join(re.findall(r"[A-Za-z]+", own_title)[:4])
        if word is None:
            live = await asyncio.to_thread(search.search, query, 2)
        if not live:
            warnings.append("Daraz search could not be read, so your rank and the top listings are not known.")
        jobs.checkpoint(project_id)
        me = await asyncio.to_thread(_side, own, live)
        for rival in rivals:
            jobs.checkpoint(project_id)
            them = await asyncio.to_thread(_side, rival, live)
            g, info = engine.analyze(project_id, dict(me), them, word, live)
            gaps.extend(g)
            analyses.append({"competitor": rival.get("product_name"), "search_query": query, **info})
        if not reviews.available():
            warnings.append("The review model was not found, so what customers say was not read.")
        return AgentResult(payload=gaps, artifacts={"daraz_analysis": {"competitors": analyses}},
                           items_processed=len(gaps), duration_ms=self._elapsed_ms(started), warnings=warnings)
