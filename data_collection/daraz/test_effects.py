"""Daraz jewellery: which LEVERS go with a better search rank and with more sales?

    ../../backend/.venv/bin/python test_effects.py

Same idea as the Instagram cross-shop test: each search word is compared with ITSELF (listings competing for the
same customers), so the popularity of a word cancels out.
  1. Inside each search word: Spearman correlation between the lever and the result
     (result = rank position, where 1 is best, flipped so higher = better; and number sold).
  2. Across the 25 search words: Wilcoxon signed-rank test, are those correlations above or below 0?
  3. Benjamini-Hochberg over all levers, so a lever passing by luck is removed.
Typical values of the TOP 20 listings of each word are saved as the benchmark the app compares with.
Writes reports/effects.csv and models/daraz_evidence.json.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

HERE = Path(__file__).resolve().parent
MIN_EACH = 3        # a yes/no lever must have at least 3 listings with it and 3 without in a word to be tested there
STOP = {"for", "with", "and", "the", "of", "in", "to", "a", "pcs", "piece", "new", "1", "2", "3"}

# lever: (column, kind, plain name, what "better" means for the seller)
LEVERS = {
    "price_vs_word": ("price_vs_word", "number", "price compared with similar listings"),
    "discount_pct": ("discount_pct", "number", "discount shown (%)"),
    "has_discount": ("has_discount", "yesno", "a discount shown"),
    "free_shipping": ("free_shipping", "yesno", "free shipping badge"),
    "voucher": ("voucher", "yesno", "a voucher badge"),
    "coins": ("coins", "yesno", "Daraz coins discount"),
    "daraz_choice": ("daraz_choice", "yesno", "Daraz Choice badge"),
    "title_words": ("title_words", "number", "words in the title"),
    "title_has_search_word": ("title_has_search_word", "yesno", "the search word in the title"),
    "image_count": ("image_count", "number", "number of photos"),
    "photo_worn": ("photo_worn", "yesno", "main photo shows the jewellery worn"),
    "photo_face": ("photo_face", "yesno", "main photo shows a face"),
    "description_words": ("description_words", "number", "words in the description"),
    "bullet_count": ("bullet_count", "number", "bullet points in the description"),
    "variant_count": ("variant_count", "number", "colour / size options"),
}
OUTCOMES = {"rank": "search rank", "sold_f": "number sold"}


def bh(p: dict[str, float]) -> dict[str, float]:
    keys = sorted(p, key=p.get)
    m, out, prev = len(keys), {}, 1.0
    for i, k in reversed(list(enumerate(keys, 1))):
        prev = min(prev, p[k] * m / i)
        out[k] = prev
    return out


def main() -> None:
    df = pd.read_csv(HERE / "datasets" / "listings_dataset.csv", dtype={"item_id": str})
    df = df[~df["sponsored"]]
    df["score_rank"] = -df["rank"]
    rows = []
    for out_col, out_name in OUTCOMES.items():
        y = "score_rank" if out_col == "rank" else out_col
        res = {}
        for key, (col, kind, name) in LEVERS.items():
            if col not in df:
                rows.append({"outcome": out_name, "lever": key, "name": name, "words_tested": 0, "verdict": "not measured"})
                continue
            rhos, top_share, rest_share = [], [], []
            for word, g in df.groupby("search_word"):
                g = g[g[col].notna()]
                x = g[col].astype(float)
                if kind == "yesno" and (x.sum() < MIN_EACH or (1 - x).sum() < MIN_EACH):
                    continue
                if x.nunique() < 2 or len(g) < 20:
                    continue
                rhos.append(spearmanr(x, g[y]).statistic)
                top_share.append(x[g["top20"]].median() if kind == "number" else x[g["top20"]].mean())
                rest_share.append(x[~g["top20"]].median() if kind == "number" else x[~g["top20"]].mean())
            rhos = [r for r in rhos if np.isfinite(r)]
            if len(rhos) < 6:
                rows.append({"outcome": out_name, "lever": key, "name": name, "words_tested": len(rhos), "verdict": "too few words to test"})
                continue
            p = float(wilcoxon(rhos).pvalue)
            res[key] = p
            rows.append({"outcome": out_name, "lever": key, "name": name, "kind": kind, "words_tested": len(rhos),
                         "median_rho": round(float(np.median(rhos)), 3), "words_positive": int(sum(r > 0 for r in rhos)),
                         "top20_typical": round(float(np.median(top_share)), 3), "rest_typical": round(float(np.median(rest_share)), 3),
                         "p": p})
        corr = bh(res)
        for r in rows:
            if r["outcome"] == out_name and r["lever"] in corr:
                r["p_corrected"] = round(corr[r["lever"]], 4)
                r["proven"] = corr[r["lever"]] < 0.05
                r["direction"] = "more is better" if r["median_rho"] > 0 else "less is better"
                r["verdict"] = ("proven: " + r["direction"]) if r["proven"] else "not proven"
    eff = pd.DataFrame(rows)
    (HERE / "reports").mkdir(exist_ok=True)
    eff.to_csv(HERE / "reports" / "effects.csv", index=False)
    print(eff[["outcome", "lever", "words_tested", "median_rho", "words_positive", "top20_typical", "rest_typical", "p_corrected", "verdict"]].to_string())

    # ---- benchmark: the top 20 of each search word (and of all words together)
    bench = {}
    groups = list(df.groupby("search_word")) + [("_all", df)]
    for word, g in groups:
        t = g[g["top20"]]
        b = {}
        for key, (col, kind, _name) in LEVERS.items():
            if col not in t:
                continue
            v = t[col].dropna().astype(float)
            if not len(v):
                continue
            b[key] = ({"median": float(v.median()), "q1": float(v.quantile(.25)), "q3": float(v.quantile(.75)), "n": int(len(v))}
                      if kind == "number" else {"share": float(v.mean()), "n": int(len(v))})
        b["price"] = {"median": float(t["price"].median()), "q1": float(t["price"].quantile(.25)), "q3": float(t["price"].quantile(.75))}
        # title words used by at least half of the top 20 (a simple majority)
        c = Counter(w for n in t["name"] for w in set(re.findall(r"[a-z]+", str(n).lower())) if w not in STOP and len(w) > 2)
        b["title_words_majority"] = sorted([w for w, k in c.items() if k >= len(t) / 2], key=lambda w: -c[w])
        bench[word] = b
    evidence = {
        "domain": "Daraz Pakistan, jewellery (25 search words, top 80 listings each)",
        "built": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "method": "inside each search word: Spearman lever vs result; across words: Wilcoxon signed-rank; Benjamini-Hochberg 5%",
        "levers": {r["lever"] + "|" + ("rank" if r["outcome"] == "search rank" else "sold"): {k: (None if (isinstance(v, float) and not np.isfinite(v)) else v) for k, v in r.items()} for r in rows},
        "benchmarks": bench,
    }
    models = HERE.parents[1] / "backend" / "app" / "analysis" / "daraz" / "models"
    models.mkdir(parents=True, exist_ok=True)
    (models / "daraz_evidence.json").write_text(json.dumps(evidence, indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o)))
    print("wrote", models / "daraz_evidence.json")


if __name__ == "__main__":
    main()
