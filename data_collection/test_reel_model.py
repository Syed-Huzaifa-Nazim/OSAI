"""Reel model: from what a reel looks and sounds like, predict whether it gets more views than the shop's usual reel.

  .venv/bin/python test_reel_model.py

Target: log(view lift), view lift = reel views / the shop's median reel views (so shops of every size compare fairly).
Reels younger than 1 day and shops with fewer than 6 reels are left out. Tested shop by shop (LeaveOneGroupOut: the
test shop is never seen in training), against the baseline "every reel gets the shop's usual views".
Feature sets: post basics only · basics + reel features (reel_features.py, reel_quality.py).
Writes reports/reel_model_results.csv and reports/reel_model_importance.csv.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneGroupOut

HERE = Path(__file__).resolve().parent
BASICS = ["caption_words", "hashtag_count", "weekend", "is_collab"]
REEL = ["duration_s", "cuts_per_10s", "cut_in_first_3s", "text_in_first_3s", "face_in_first_3s", "has_voice",
        "speech_share", "has_sound", "reel_quality"]


def load() -> pd.DataFrame:
    r = pd.read_csv(HERE / "datasets" / "reels_dataset.csv")
    q = HERE / "data" / "reel_parts" / "quality.csv"
    if q.exists():
        r = r.merge(pd.read_csv(q)[["shortcode", "reel_quality"]], on="shortcode", how="left")
    r = r[~r.young_post & r.views.notna() & (r.views > 0)].copy()
    r = r[r.groupby("handle")["views"].transform("size") >= 6]
    r["y"] = np.log(r["views"] / r.groupby("handle")["views"].transform("median"))
    r["worn_first_frame"] = (r["jewellery_shown_first_frame"] == "worn").astype(float)
    return r.reset_index(drop=True)


def X_of(r: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    X = pd.get_dummies(r[["part_of_day"]], dtype=float).join(r[[c for c in cols if c in r]].astype(float))
    return X.fillna(X.median())


def score(name: str, p: np.ndarray, y: np.ndarray, g: np.ndarray) -> dict:
    within = [spearmanr(p[g == h], y[g == h]).statistic for h in np.unique(g) if np.std(p[g == h]) > 0]
    return {"model": name, "MAE_log_view_lift": round(float(np.mean(np.abs(p - y))), 3),
            "spearman_all": round(float(spearmanr(p, y).statistic) if np.std(p) > 0 else 0.0, 3),
            "within_shop_median": round(float(np.nanmedian(within)) if within else 0.0, 3),
            "shops_ranked_right": f"{int(np.nansum(np.array(within) > 0))}/{len(np.unique(g))}"}


def main() -> None:
    r = load()
    y, g = r["y"].to_numpy(), r["handle"].to_numpy()
    print(f"{r.handle.nunique()} shops · {len(r)} reels")
    rows = [score("baseline: every reel = shop's usual views", np.zeros(len(r)), y, g)]
    sets = {"basics only": BASICS, "basics + reel features": BASICS + REEL + ["worn_first_frame"]}
    for name, cols in sets.items():
        X = X_of(r, cols)
        for mname, make in [("ridge", lambda: Ridge(alpha=10.0)),
                            ("boosting", lambda: HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200,
                                                                               min_samples_leaf=20, random_state=0))]:
            p = np.zeros(len(r))
            for tr, te in LeaveOneGroupOut().split(X, y, g):
                p[te] = make().fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
            rows.append(score(f"{mname}: {name}", p, y, g))
    res = pd.DataFrame(rows)
    (HERE / "reports").mkdir(exist_ok=True)
    res.to_csv(HERE / "reports" / "reel_model_results.csv", index=False)
    print(res.to_string(index=False))

    X = X_of(r, BASICS + REEL + ["worn_first_frame"])
    m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=20, random_state=0).fit(X, y)
    import joblib
    (HERE / "models").mkdir(exist_ok=True)
    joblib.dump({"model": m, "features": list(X.columns), "target": "log(reel view lift)", "tests": rows,
                 "trained_on": f"{r.handle.nunique()} shops, {len(r)} reels"}, HERE / "models" / "reel_views.joblib")
    print("saved models/reel_views.joblib")
    imp = permutation_importance(m, X, y, n_repeats=10, random_state=0)
    imp = pd.DataFrame({"feature": X.columns, "importance": imp.importances_mean.round(4)}).sort_values("importance", ascending=False)
    imp.to_csv(HERE / "reports" / "reel_model_importance.csv", index=False)
    print("\nwhat the model leans on (permutation importance, fitted on all reels):\n", imp.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
