"""Daraz Model B: predict how well a listing ranks / sells from its LEVERS only (what a seller can change).

    ../../backend/.venv/bin/python train_rank_model.py

Targets (one model each):
  rank  -> rank score inside its search word, 1 = first, 0 = 80th
  sold  -> log(1 + number sold)  (blank "sold" = fewer than 5, counted as 0)
Inputs: the 14 levers only. Results (reviews, rating) are NOT inputs: they would leak the answer.
A second "levers + results" run is reported only to show how much the results themselves explain.

Fair test: GroupKFold by SEARCH WORD (5 folds): the model never sees the test words; a listing that also appears
under a test word is removed from training. Scores, compared with a baseline that predicts the average:
  within-word Spearman (median over words) - does it put listings of one word in the right order?
  words ranked right - in how many test words the order is better than chance (Spearman > 0)
  MAE - average error on the target.
Writes reports/model_b_rank.csv, reports/model_b_importance.csv, models/rank_model.joblib.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
LEVERS = ["price_vs_word", "discount_pct", "free_shipping", "voucher", "coins", "daraz_choice", "title_words",
          "title_has_search_word", "image_count", "photo_worn", "photo_face", "description_words", "bullet_count",
          "variant_count"]
RESULTS = ["reviews", "rating_f"]
MODELS = {
    "baseline: predict the average": None,
    "ridge regression": lambda: make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "random forest": lambda: RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=0, n_jobs=-1),
    "gradient boosting": lambda: HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300, random_state=0),
}


def data() -> pd.DataFrame:
    d = pd.read_csv(HERE / "datasets" / "listings_dataset.csv", dtype={"item_id": str})
    d = d[~d["sponsored"]].copy()
    for c in LEVERS:
        d[c] = d[c].astype(float)
    d["rating_f"] = d["rating"].fillna(0)
    d["rank_score"] = 1 - (d["rank"] - 1) / 79
    d["sold_log"] = np.log1p(d["sold_f"])
    return d.dropna(subset=LEVERS)


def evaluate(d: pd.DataFrame, target: str, features: list[str]) -> tuple[list[dict], dict]:
    rows, preds = [], {}
    folds = list(GroupKFold(n_splits=5).split(d, groups=d["search_word"]))
    for name, make in MODELS.items():
        pred = pd.Series(np.nan, index=d.index)
        for tr, te in folds:
            test = d.iloc[te]
            train = d.iloc[tr]
            train = train[~train["item_id"].isin(test["item_id"])]          # no listing on both sides
            if make is None:
                pred.iloc[te] = train[target].mean()
                continue
            m = make().fit(train[features], train[target])
            pred.iloc[te] = m.predict(test[features])
        rhos = []
        for _, g in d.assign(p=pred).groupby("search_word"):
            r = spearmanr(g["p"], g[target]).statistic if g["p"].nunique() > 1 else 0.0
            rhos.append(0.0 if not np.isfinite(r) else r)
        rows.append({"target": target, "inputs": "levers" if features == LEVERS else "levers + results", "model": name,
                     "within_word_spearman": round(float(np.median(rhos)), 3),
                     "words_ranked_right": f"{sum(r > 0 for r in rhos)}/{len(rhos)}",
                     "MAE": round(float((pred - d[target]).abs().mean()), 3)})
        preds[name] = pred
    return rows, preds


def main() -> None:
    d = data()
    print(f"{len(d)} listings x search word, {d['search_word'].nunique()} words")
    out = []
    for target in ("rank_score", "sold_log"):
        r, _ = evaluate(d, target, LEVERS)
        out += r
        r2, _ = evaluate(d, target, LEVERS + RESULTS)
        out += [x for x in r2 if x["model"] != "baseline: predict the average"]
    res = pd.DataFrame(out)
    (HERE / "reports").mkdir(exist_ok=True)
    res.to_csv(HERE / "reports" / "model_b_rank.csv", index=False)
    print(res.to_string(index=False))

    # importance of each lever (permutation, on held-out words) for the levers-only gradient boosting model
    imp_rows = []
    for target in ("rank_score", "sold_log"):
        scores = []
        for tr, te in GroupKFold(n_splits=5).split(d, groups=d["search_word"]):
            test, train = d.iloc[te], d.iloc[tr]
            train = train[~train["item_id"].isin(test["item_id"])]
            m = MODELS["gradient boosting"]().fit(train[LEVERS], train[target])
            pi = permutation_importance(m, test[LEVERS], test[target], n_repeats=10, random_state=0)
            scores.append(pi.importances_mean)
        mean = np.mean(scores, axis=0)
        imp_rows += [{"target": target, "lever": l, "importance": round(float(v), 4)} for l, v in zip(LEVERS, mean)]
    imp = pd.DataFrame(imp_rows).sort_values(["target", "importance"], ascending=[True, False])
    imp.to_csv(HERE / "reports" / "model_b_importance.csv", index=False)
    print(imp.groupby("target").head(6).to_string(index=False))

    models = {t: MODELS["gradient boosting"]().fit(d[LEVERS], d[t]) for t in ("rank_score", "sold_log")}
    (HERE / "models").mkdir(exist_ok=True)
    joblib.dump({"levers": LEVERS, "models": models, "note": "report only unless it beats the baseline clearly"},
                HERE / "models" / "rank_model.joblib")
    print("saved models/rank_model.joblib")


if __name__ == "__main__":
    main()
