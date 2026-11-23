"""Audit distributions, remove noise, and create product-disjoint balanced splits."""
from __future__ import annotations

import html
import json
import re
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from common import ROOT, LABELS, config, save_json


def clean_text(value):
    if pd.isna(value):
        return ""
    value = html.unescape(str(value))
    value = re.sub(r"https?://\S+|[\x00-\x1f\x7f]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def spread(values):
    s = pd.to_numeric(values, errors="coerce").dropna()
    if s.empty:
        return {"count": 0}
    q1, q3 = s.quantile([.25, .75])
    iqr = q3 - q1
    outliers = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
    return {"count": int(len(s)), "mean": float(s.mean()), "median": float(s.median()),
            "std": float(s.std(ddof=0)), "min": float(s.min()), "q1": float(q1),
            "q3": float(q3), "max": float(s.max()), "iqr": float(iqr),
            "outliers": outliers, "outlier_pct": round(100 * outliers / len(s), 2)}


def audit(frame):
    return {field: spread(frame[field]) for field in ("review_word_count", "review_char_count", "price")}


def add_lengths(frame):
    frame = frame.copy()
    frame["review_word_count"] = frame.review_text.str.split().str.len()
    frame["review_char_count"] = frame.review_text.str.len()
    frame["price"] = pd.to_numeric(frame.price, errors="coerce")
    return frame


def grouped_split(frame, seed):
    # Ten folds give about 10% test; one of nine remaining folds gives about 10% validation.
    outer = StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=seed)
    trainval_idx, test_idx = next(outer.split(frame, frame.label, frame.parent_asin))
    trainval = frame.iloc[trainval_idx].reset_index(drop=True)
    test = frame.iloc[test_idx].reset_index(drop=True)
    inner = StratifiedGroupKFold(n_splits=9, shuffle=True, random_state=seed + 1)
    train_idx, val_idx = next(inner.split(trainval, trainval.label, trainval.parent_asin))
    train, val = trainval.iloc[train_idx], trainval.iloc[val_idx]
    groups = [set(part.parent_asin) for part in (train, val, test)]
    assert not groups[0] & groups[1] and not groups[0] & groups[2] and not groups[1] & groups[2]
    return train, val, test


def run():
    settings = config()
    raw = pd.read_csv(ROOT / "data/raw/amazon_raw_sample.csv", dtype={"parent_asin": str})
    required = {"parent_asin", "category", "rating", "review_text", "product_title", "price", "label"}
    if missing := required - set(raw):
        raise ValueError(f"Raw sample missing columns: {sorted(missing)}")
    before_count = len(raw)
    raw["review_text"] = raw.review_text.map(clean_text)
    raw["product_title"] = raw.product_title.map(clean_text)
    raw = add_lengths(raw)
    before = audit(raw)
    counts = {"raw": before_count}
    frame = raw.dropna(subset=["rating", "label", "parent_asin"])
    frame = frame[(frame.review_word_count >= 5) & frame.label.isin([0, 1, 2])].copy()
    counts["after_null_and_short"] = len(frame)
    frame["normal_review"] = frame.review_text.str.lower()
    frame = frame.drop_duplicates(["normal_review", "product_title"]).drop_duplicates(["normal_review"])
    counts["after_dedup"] = len(frame)
    cutoff = frame.review_word_count.quantile(.99)
    frame = frame[frame.review_word_count <= cutoff].copy()
    counts["after_length_trim"] = len(frame)
    minimum = int(frame.label.value_counts().min())
    if minimum < settings["min_clean_per_class"]:
        raise RuntimeError(f"Only {minimum} clean rows in smallest class; need {settings['min_clean_per_class']}. Increase raw_per_class.")
    frame = pd.concat([group.sample(n=minimum, random_state=settings["seed"]) for _, group in frame.groupby("label")])
    frame = frame.sample(frac=1, random_state=settings["seed"]).drop(columns="normal_review").reset_index(drop=True)
    counts["balanced"] = len(frame)
    train, val, test = grouped_split(frame, settings["seed"])
    processed = ROOT / "data/processed"
    processed.mkdir(parents=True, exist_ok=True)
    for name, part in (("train", train), ("val", val), ("test", test)):
        part.to_csv(processed / f"{name}.csv", index=False)
    reviews = pd.read_csv(ROOT / "data/alibaba_validation/alibaba_reviews_validation.csv")
    products = pd.read_csv(ROOT / "data/alibaba_validation/alibaba_products_validation.csv")
    reviews["review_text"] = reviews.review_text.map(clean_text)
    reviews["price"] = pd.to_numeric(reviews.price_usd, errors="coerce")
    reviews = add_lengths(reviews)
    alibaba = {"reviews": len(reviews), "products": len(products), "star_counts": reviews.review_rating.value_counts().sort_index().to_dict(),
               "severity_counts": reviews.gap_severity_label.value_counts().to_dict(), "review_spread": audit(reviews),
               "product_price_spread": spread(products.price_usd),
               "description_boilerplate_pct": round(100 * products.description.fillna("").str.contains("Find Complete Details about", case=False, regex=False).mean(), 2)}
    stats = {"row_counts": counts, "cutoff_words_p99": float(cutoff), "before": before, "after": audit(frame),
             "class_counts": frame.label.value_counts().sort_index().to_dict(),
             "splits": {name: {"rows": len(part), "classes": part.label.value_counts().sort_index().to_dict(), "products": part.parent_asin.nunique()}
                        for name, part in (("train", train), ("val", val), ("test", test))}, "alibaba": alibaba}
    eda = ROOT / "eda"
    eda.mkdir(exist_ok=True)
    save_json(eda / "eda_stats.json", stats)
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(3)
    ax.bar(x - .2, [stats["class_counts"].get(i, 0) for i in range(3)], .4, label="Amazon balanced")
    ax.bar(x + .2, [alibaba["severity_counts"].get(LABELS[i], 0) for i in range(3)], .4, label="Alibaba validation")
    ax.set_xticks(x, list(LABELS.values())); ax.legend(); fig.tight_layout(); fig.savefig(eda / "eda_class_balance.png"); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].boxplot([raw.review_word_count.dropna(), frame.review_word_count.dropna()], tick_labels=["Before", "After"], showfliers=False)
    axes[0].set_title("Review length (words)")
    axes[1].boxplot([raw.price.dropna(), frame.price.dropna(), products.price_usd.dropna()], tick_labels=["Raw Amazon", "Clean Amazon", "Alibaba"], showfliers=False)
    axes[1].set_title("Price"); fig.tight_layout(); fig.savefig(eda / "eda_spread_outliers.png"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    frame.category.value_counts().plot.bar(ax=ax); ax.set_ylabel("Reviews"); fig.tight_layout(); fig.savefig(eda / "eda_category_distribution.png"); plt.close(fig)
    report = ["# Pre-training EDA", "", f"Raw rows: {before_count}; after null/short: {counts['after_null_and_short']}; after dedup: {counts['after_dedup']}; after 99th percentile trim: {counts['after_length_trim']}; balanced: {len(frame)}.",
              f"Exactly {minimum} rows per class ({100/3:.1f}% each). Review length cutoff: {cutoff:.1f} words.", "", "## Spread and IQR outliers", "", "| Metric | Stage | Count | Mean | Median | Std | Min | Q1 | Q3 | Max | IQR | Outliers | Outlier % |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for stage, values in (("Raw Amazon", before), ("Clean Amazon", stats["after"]), ("Alibaba reviews", alibaba["review_spread"])):
        for metric, item in values.items():
            report.append("| " + metric + " | " + stage + " | " + " | ".join(str(round(item.get(k, 0), 2)) for k in ("count", "mean", "median", "std", "min", "q1", "q3", "max", "iqr", "outliers", "outlier_pct")) + " |")
    report += ["", "## Alibaba cross-domain audit", "", f"{len(reviews)} reviews and {len(products)} products. Star counts: {alibaba['star_counts']}. Severity counts: {alibaba['severity_counts']}.",
               f"Product price spread: {alibaba['product_price_spread']}. Description boilerplate: {alibaba['description_boilerplate_pct']}%.",
               "The small and highly skewed Alibaba review set is reserved for validation. Product-disjoint Amazon splits prevent parent-product leakage.", "", "## Split sizes", "", json.dumps(stats["splits"], indent=2)]
    (eda / "eda_report.md").write_text("\n".join(report), encoding="utf-8")
    return stats


if __name__ == "__main__":
    print(json.dumps(run()["row_counts"], indent=2))
