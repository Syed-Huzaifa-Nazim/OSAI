"""Daraz jewellery datasets, step 4: joins search results, listing pages, photo tags and reviews.

    ../../backend/.venv/bin/python build_datasets.py

Writes datasets/:
  listings_dataset.csv  one row per search word x listing: RESULTS (rank, sold, reviews, rating) and LEVERS
                        (what a seller can change: price, discount, badges, title, photos, description, variants)
  reviews_dataset.csv   one row per review (text, stars, seller reply); sentiment + reasons are added by
                        analyse_reviews.py
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "datasets"
STOP = {"for", "with", "and", "the", "of", "women", "girls", "set"}


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).lower())


def badges(icons: str) -> dict[str, bool]:
    kinds = " ".join(str(x.get("bizType", "")) + " " + str(x.get("text", "")) for x in json.loads(icons or "[]")).lower()
    return {"free_shipping": "freeshipping" in kinds, "voucher": "voucher" in kinds, "coins": "coins" in kinds,
            "daraz_choice": "choice" in kinds}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    s = pd.read_csv(HERE / "search_listings.csv", dtype={"item_id": str})
    details, reviews = {}, []
    for f in glob.glob(str(HERE / "raw" / "details" / "*.json")):
        d = json.load(open(f))
        m, t = d["meta"], d["text"]
        desc = t.get("description", "")
        desc = "" if desc.lower().startswith("no description") else desc
        details[str(d["item_id"])] = {
            "image_count": m.get("image_count"), "variant_count": m.get("variant_count") or 0,
            "description_words": len(desc.split()), "bullet_count": m.get("bullet_count") or 0,
            "category_leaf": m.get("category_leaf"), "brand_named": bool(m.get("is_branded")),
            "reviews_read": len(d["reviews"]),
            "seller_replies": sum(r["seller_reply"] for r in d["reviews"]),
            "review_photos": sum(1 for r in d["reviews"] if r["images"]),
        }
        for i, r in enumerate(d["reviews"]):
            if r["text"]:
                reviews.append({"item_id": str(d["item_id"]), "review_no": i, "stars": r["rating"], "text": r["text"],
                                "bought": r["bought"], "variant": r["sku"], "has_photo": r["images"] > 0,
                                "seller_reply": r["seller_reply"]})
    det = pd.DataFrame.from_dict(details, orient="index").rename_axis("item_id").reset_index()
    photos = pd.read_csv(HERE / "photo_tags.csv", dtype={"item_id": str}) if (HERE / "photo_tags.csv").exists() else None

    df = s.merge(det, on="item_id", how="left")
    if photos is not None:
        df = df.merge(photos, on="item_id", how="left")
        df["photo_worn"] = df["photo_shown"].eq("worn").where(df["photo_shown"].notna())
    df = pd.concat([df.drop(columns=["free_shipping"]), pd.DataFrame([badges(x) for x in df["icons"]])], axis=1)
    df["discount_pct"] = df["discount_pct"].fillna(0)
    df["has_discount"] = df["discount_pct"] > 0
    df["sold_f"] = df["sold"].fillna(0)            # Daraz shows "N sold" from 5 sold up; blank = fewer than 5
    df["price_vs_word"] = df["price"] / df.groupby("search_word")["price"].transform("median")
    df["title_words"] = df["name"].map(lambda x: len(words(x)))
    df["title_has_search_word"] = [all(w in words(n) for w in words(q) if w not in STOP) for q, n in zip(df["search_word"], df["name"])]
    df["top20"] = df["rank"] <= 20
    df["label_source"] = "measured (Daraz search + page + Model D photo tag)"
    df.drop(columns=["icons"]).to_csv(OUT / "listings_dataset.csv", index=False)
    rv = pd.DataFrame(reviews)
    old = OUT / "reviews_dataset.csv"
    if old.exists() and "sentiment" in pd.read_csv(old, nrows=1).columns and len(pd.read_csv(old)) == len(rv):
        print("reviews_dataset.csv already has the review model's output: kept")   # analyse_reviews.py ran on it
    else:
        rv.to_csv(old, index=False)
    print(f"listings_dataset: {len(df)} rows ({df['item_id'].nunique()} listings, details for {df['image_count'].notna().sum()})")
    print(f"reviews_dataset: {len(rv)} reviews from {rv['item_id'].nunique() if len(rv) else 0} listings")


if __name__ == "__main__":
    main()
