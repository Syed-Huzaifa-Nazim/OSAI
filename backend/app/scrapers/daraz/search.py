"""Daraz search results and reviews, read from the JSON Daraz's own pages use.

Search gives what a product page loads only with JavaScript: price, discount, number sold, rating, review count,
badges (free shipping, voucher, coins, Daraz Choice) and the listing's RANK for a search word. The same reader built
the jewellery dataset (Development/data_collection/daraz/collect_search.py), so app and dataset agree.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.parse import quote_plus

import requests

from app.core.config import get_settings
from app.scrapers.daraz import selectors as S

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.daraz.pk/catalog/?ajax=true&q={q}&page={page}"
REVIEW_URL = "https://my.daraz.pk/pdp/review/getReviewList?itemId={item_id}&pageSize=20&filter=0&sort=0&pageNo={page}"
PER_PAGE = 40
HEADERS = {"User-Agent": S.REQUEST_HEADERS["User-Agent"], "Accept": "application/json,text/plain,*/*"}


def item_id_of(url: str) -> str | None:
    m = re.search(r"-i(\d+)", url or "")
    return m.group(1) if m else None


def num(text: Any) -> float | None:
    if text in (None, ""):
        return None
    m = re.search(r"([\d.]+)\s*([kK])?", str(text).replace(",", ""))
    return float(m.group(1)) * (1000 if m.group(2) else 1) if m else None


def badges(icons: list | None) -> dict[str, bool]:
    kinds = " ".join(f"{x.get('bizType', '')} {x.get('text', '')}" for x in (icons or []) if isinstance(x, dict)).lower()
    return {"free_shipping": "freeshipping" in kinds, "voucher": "voucher" in kinds, "coins": "coins" in kinds,
            "daraz_choice": "choice" in kinds}


def listing_row(it: dict[str, Any], rank: int) -> dict[str, Any]:
    """One search result as the dataset stores it."""
    url = str(it.get("itemUrl") or "")
    return {
        "rank": rank, "item_id": str(it.get("itemId") or it.get("nid") or ""), "name": it.get("name") or "",
        "item_url": "https:" + url if url.startswith("//") else url,
        "price": num(it.get("price")), "original_price": num(it.get("originalPrice")),
        "discount_pct": num(it.get("discount")) or 0.0, "rating": num(it.get("ratingScore")),
        "reviews": num(it.get("review")) or 0.0, "sold": num(it.get("itemSoldCntShow")),
        "seller_name": (it.get("sellerName") or "").strip(), "location": it.get("location"),
        "sponsored": bool(it.get("isSponsored")) or str(it.get("adFlag")) not in ("0", "None", ""),
        "image": it.get("image"), **badges(it.get("icons")),
    }


def search(query: str, pages: int = 2) -> list[dict[str, Any]]:
    """The first `pages` result pages for a search word, in Daraz's default order (rank 1 = first)."""
    out: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        items = None
        for attempt in (1, 2, 3):                   # Daraz sometimes refuses a request; polite retries
            try:
                r = requests.get(SEARCH_URL.format(q=quote_plus(query), page=page), headers=HEADERS,
                                 timeout=get_settings().scraper_timeout)
                r.raise_for_status()
                items = ((r.json() or {}).get("mods") or {}).get("listItems") or []
                if items or page > 1 or attempt == 3:
                    break
                log.info("Daraz search gave an empty page for %r; trying again", query)
                items = None                        # an empty first page is usually a refused request
                time.sleep(3)
                continue
            except Exception as exc:  # noqa: BLE001 - search is best effort; the caller says what is missing
                log.warning("Daraz search failed for %r page %d (try %d): %s", query, page, attempt, exc)
                time.sleep(2)
        if items is None:
            break
        out.extend(listing_row(it, (page - 1) * PER_PAGE + i + 1) for i, it in enumerate(items))
        if len(items) < PER_PAGE:
            break
    return out


def find(item_id: str, title: str) -> dict[str, Any] | None:
    """A listing's own search row (price, badges, sold...), found by searching its title."""
    words = re.findall(r"[A-Za-z0-9]+", title or "")[:10]
    if not item_id or not words:
        return None
    for row in search(" ".join(words), pages=2):
        if row["item_id"] == item_id:
            return row
    return None


def reviews(item_id: str, referer: str, limit: int = 40) -> list[dict[str, Any]]:
    """Up to `limit` newest reviews: stars, text, whether the seller replied."""
    s = requests.Session()
    s.headers.update({**HEADERS, "Referer": referer})
    out: list[dict[str, Any]] = []
    for page in (1, 2, 3):
        try:
            r = s.get(REVIEW_URL.format(item_id=item_id, page=page), timeout=get_settings().scraper_timeout)
            if "json" not in r.headers.get("content-type", ""):
                break
            items = ((r.json() or {}).get("model") or {}).get("items") or []
        except Exception as exc:  # noqa: BLE001
            log.warning("Daraz reviews failed for %s: %s", item_id, exc)
            break
        out.extend({"stars": it.get("rating"), "text": (it.get("reviewContent") or "").strip(),
                    "seller_reply": bool(it.get("replies"))} for it in items if (it.get("reviewContent") or "").strip())
        if len(items) < 20 or len(out) >= limit:
            break
    return out[:limit]


def dumps(rows: list[dict[str, Any]]) -> str:
    return json.dumps(rows, ensure_ascii=False)
