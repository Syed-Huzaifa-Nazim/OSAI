"""Daraz jewellery reviews, step 5: sentiment and reasons with the team's review model
(two fine-tuned XLM-RoBERTa models in Development/Daraz_Model/model_package, used as they are).

    ../../backend/.venv/bin/python analyse_reviews.py

Adds to datasets/reviews_dataset.csv: sentiment, sentiment_confidence, reasons ("Delivery-; Quality+").
Also writes labels/review_check_150.csv (+ .xlsx): 150 random reviews (seeded) for a person to check, because the model
was trained mostly on electronics reviews and has never been measured on jewellery.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1] / "Daraz_Model" / "model_package"
sys.path.insert(0, str(PKG))
from review_analyzer import ReviewAnalyzer  # noqa: E402


def main() -> None:
    path = HERE / "datasets" / "reviews_dataset.csv"
    rv = pd.read_csv(path, dtype={"item_id": str})
    az = ReviewAnalyzer(PKG)
    out = []
    texts = rv["text"].astype(str).tolist()
    for i in range(0, len(texts), 256):
        res = az.analyze(texts[i:i + 256])["per_review"]
        out.extend(res)
        print(f"{min(i + 256, len(texts))}/{len(texts)}", flush=True)
    assert len(out) == len(rv), "every review must get one result"
    rv["sentiment"] = [o["sentiment"] for o in out]
    rv["sentiment_confidence"] = [o["sentiment_confidence"] for o in out]
    rv["reasons"] = ["; ".join(f"{r['aspect']}{'+' if r['polarity'] == 'positive' else '-'}" for r in o["reasons"]) for o in out]
    rv["label_source"] = "team review model (XLM-R), not checked"
    rv.to_csv(path, index=False)
    print(rv["sentiment"].value_counts().to_dict(), "| reviews with a reason:", int((rv["reasons"] != "").sum()))

    (HERE / "labels").mkdir(exist_ok=True)
    chk = rv.sample(n=min(150, len(rv)), random_state=42)[["item_id", "stars", "text", "sentiment", "reasons"]].copy()
    chk["sentiment right? (Y/N)"] = ""
    chk["reasons right? (Y/N)"] = ""
    chk["reason the model missed (write it, e.g. plating faded, stone fell, late delivery)"] = ""
    chk.to_csv(HERE / "labels" / "review_check_150.csv", index=False)
    try:
        chk.to_excel(HERE / "labels" / "review_check_150.xlsx", index=False)
    except ImportError:         # the backend venv has no openpyxl; convert the csv with the data_collection venv
        print("no openpyxl here: wrote labels/review_check_150.csv only")


if __name__ == "__main__":
    main()
