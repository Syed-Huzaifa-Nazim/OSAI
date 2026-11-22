"""Daraz jewellery dataset, step 2: each listing's page details and its reviews.

    cd Development/data_collection/daraz && ../../backend/.venv/bin/python collect_details.py [max_listings]

Uses the app's own Daraz page parser (backend/app/scrapers/daraz), so the dataset and the app read listings
the same way. Price comes from the search results (step 1), so the slow browser fallback is not needed.
Reviews come from Daraz's review JSON (up to MAX_REVIEWS per listing). One JSON file per listing in raw/details/,
so a stopped run resumes where it stopped. A few workers, each pausing between requests.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.scrapers.daraz import scraper as D  # noqa: E402
from app.scrapers.daraz import selectors as S  # noqa: E402

OUT = HERE / "raw" / "details"
WORKERS = 4
DELAY_S = 1.5
MAX_REVIEWS = 40
REVIEW_URL = "https://my.daraz.pk/pdp/review/getReviewList?itemId={item_id}&pageSize=20&filter=0&sort=0&pageNo={page}"


def reviews(item_id: str, referer: str) -> list[dict]:
    s = requests.Session()
    s.headers.update({**S.REQUEST_HEADERS, "Accept": "application/json,text/plain,*/*", "Referer": referer})
    out: list[dict] = []
    for page in (1, 2):
        r = s.get(REVIEW_URL.format(item_id=item_id, page=page), timeout=30)
        if "json" not in r.headers.get("content-type", ""):
            break
        items = ((r.json() or {}).get("model") or {}).get("items") or []
        for it in items:
            out.append({"rating": it.get("rating"), "text": (it.get("reviewContent") or "").strip(),
                        "bought": it.get("boughtDate"), "sku": it.get("skuInfo"), "likes": it.get("likeCount"),
                        "images": len(it.get("images") or []), "seller_reply": bool(it.get("replies"))})
        time.sleep(DELAY_S)
        if len(items) < 20 or len(out) >= MAX_REVIEWS:
            break
    return out[:MAX_REVIEWS]


def one(row: dict) -> str:
    path = OUT / f"{row['item_id']}.json"
    if path.exists():
        return "skip"
    try:
        url = D.canonical_url(row["item_url"])
        html = D._fetch_with_requests(url)
        p = D._parse_page(html, url, "listing")
        rec = {"item_id": row["item_id"], "url": url,
               "meta": {k: v for k, v in p.metadata.items() if isinstance(v, (str, int, float, bool)) or v is None},
               "text": {k: v for k, v in p.text_fields.items() if k != "review"},
               "images": [im.url for im in p.images][:12],
               "reviews": reviews(row["item_id"], url) if (row.get("reviews") or 0) > 0 else []}
        path.write_text(json.dumps(rec, ensure_ascii=False))
        time.sleep(DELAY_S)
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"fail {type(exc).__name__}: {str(exc)[:80]}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(HERE / "search_listings.csv").drop_duplicates("item_id")
    df = df.sort_values("rank")                         # best-ranked first, so a short run still covers the top
    if len(sys.argv) > 1:
        df = df.head(int(sys.argv[1]))
    rows = df.to_dict("records")
    t0, done, fails = time.time(), 0, 0
    with ThreadPoolExecutor(WORKERS) as pool:
        for res in pool.map(one, rows):
            done += 1
            fails += res.startswith("fail")
            if res.startswith("fail"):
                print(res, flush=True)
            if done % 50 == 0:
                print(f"{done}/{len(rows)} done, {fails} failed, {time.time() - t0:.0f} s", flush=True)
    print(f"finished {done}, failed {fails}, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
