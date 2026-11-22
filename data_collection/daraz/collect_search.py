"""Daraz jewellery dataset, step 1: search results WITH their rank.

    cd Development/data_collection/daraz && ../../backend/.venv/bin/python collect_search.py

For each search word, the first PAGES result pages (40 listings each) are read from Daraz's own search
JSON (the same data the search page shows), in Daraz's default "Best Match" order, so rank = position.
Every raw answer is saved in raw/ so the dataset can be rebuilt. Polite: one request every DELAY_S seconds.
Writes search_listings.csv (one row per search word x listing).
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PAGES = 2
DELAY_S = 3.0
SEARCH_WORDS = [
    "bridal jewellery set", "kundan set", "jhumka", "earrings for girls", "necklace for women",
    "artificial jewellery", "gold plated jewellery", "bangles for women", "bracelet for women", "ring for women",
    "nose pin", "anklet payal", "pendant necklace", "choker set", "maang tikka",
    "jewellery set for women", "pearl necklace", "stud earrings", "silver ring", "oxidized jewellery",
    "bridal bangles", "polki set", "kada for women", "locket for girls", "jhumki earrings",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept": "application/json"}


def _num(text) -> float | None:
    if text in (None, ""):
        return None
    m = re.search(r"([\d.]+)\s*([kK])?", str(text).replace(",", ""))
    if not m:
        return None
    return float(m.group(1)) * (1000 if m.group(2) else 1)


def fetch(word: str, page: int) -> dict:
    path = RAW / f"search_{word.replace(' ', '_')}_p{page}.json"
    if path.exists():
        return json.loads(path.read_text())
    url = f"https://www.daraz.pk/catalog/?ajax=true&q={quote_plus(word)}&page={page}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    path.write_text(json.dumps(data))
    time.sleep(DELAY_S)
    return data


def main() -> None:
    RAW.mkdir(exist_ok=True)
    rows = []
    for word in SEARCH_WORDS:
        for page in range(1, PAGES + 1):
            try:
                data = fetch(word, page)
            except Exception as exc:  # noqa: BLE001
                print(f"  {word} p{page}: failed ({exc})")
                continue
            items = (data.get("mods") or {}).get("listItems") or []
            total = (data.get("mainInfo") or {}).get("totalResults")
            for i, it in enumerate(items):
                rows.append({
                    "search_word": word, "rank": (page - 1) * 40 + i + 1, "total_results": _num(total),
                    "item_id": str(it.get("itemId") or it.get("nid") or ""), "name": it.get("name"),
                    "item_url": "https:" + it["itemUrl"] if str(it.get("itemUrl", "")).startswith("//") else it.get("itemUrl"),
                    "price": _num(it.get("price")), "original_price": _num(it.get("originalPrice")),
                    "discount_pct": _num(it.get("discount")), "rating": _num(it.get("ratingScore")),
                    "reviews": _num(it.get("review")) or 0, "sold": _num(it.get("itemSoldCntShow")),
                    "seller_id": it.get("sellerId"), "seller_name": (it.get("sellerName") or "").strip(),
                    "location": it.get("location"), "brand": it.get("brandName"),
                    "sponsored": bool(it.get("isSponsored")) or str(it.get("adFlag")) not in ("0", "None", ""),
                    "in_stock": it.get("inStock"), "image": it.get("image"),
                    "skus": len(it.get("skus") or []), "free_shipping": any("free" in json.dumps(x).lower() and "ship" in json.dumps(x).lower() for x in (it.get("icons") or [])),
                    "icons": json.dumps(it.get("icons") or []),
                })
            print(f"{word} p{page}: {len(items)} listings (of {total})")
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "search_listings.csv", index=False)
    print(f"\n{len(df)} rows, {df['item_id'].nunique()} distinct listings, {df['search_word'].nunique()} search words")


if __name__ == "__main__":
    main()
