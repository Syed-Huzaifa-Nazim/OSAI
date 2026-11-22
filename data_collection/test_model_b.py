"""Model B (post lift): does knowing how the jewellery is shown help predict which posts do better than the shop's usual?

  .venv/bin/python test_model_b.py

Target: log(lift), lift = post likes+comments / the shop's median post. Usable shops: usual post >= 10 interactions;
posts younger than 1 day dropped. Tested shop by shop (LeaveOneGroupOut: the test shop is never seen in training).
Three feature sets: no picture tags · CLIP zero-shot drafts · Model D tags (person-checked where available).
Writes reports/model_b_results.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import LeaveOneGroupOut

HERE = Path(__file__).resolve().parent
BASE = ["weekend", "slides", "caption_words", "first_line_chars", "emoji_count", "has_question", "price_in_caption",
        "order_cta_in_caption", "phone_in_caption", "offer_words_in_caption", "hashtag_count", "is_collab"]
OCR = ["text_on_image", "price_on_image", "phone_on_image", "sale_words_on_image"]


def load() -> pd.DataFrame:
    d = pd.read_csv(HERE / "datasets" / "posts_dataset.csv")
    d["interactions"] = d["likes"] + d["comments"]
    usual = d.groupby("handle")["interactions"].median()
    m = d[d.handle.isin(usual[usual >= 10].index) & ~d.young_post & d.lift.notna() & (d.lift > 0)].copy()
    t = pd.read_csv(HERE / "labels" / "pictures_tags_model.csv")
    for tag in ("jewellery_shown", "face"):
        t[f"{tag}_d"] = t[f"{tag}_verified"].fillna(t[f"{tag}_model"])          # person's answer if checked, else Model D
    keep = ["shortcode", "jewellery_shown", "face", "background", "amount", "jewellery_shown_d", "face_d", *OCR]
    m = m.merge(t[keep], on="shortcode", how="left")
    m["y"] = np.log(m["lift"])
    return m


def features(m: pd.DataFrame, picture: list[str]) -> pd.DataFrame:
    X = pd.get_dummies(m[["format", "part_of_day", "caption_language", *picture]], dtype=float)
    X = X.join(m[BASE].astype(float))
    if picture:
        X = X.join(m[OCR].fillna(False).astype(float))
    return X


def score(name: str, p: np.ndarray, y: np.ndarray, g: np.ndarray) -> dict:
    within = [spearmanr(p[g == h], y[g == h]).statistic for h in np.unique(g) if np.std(p[g == h]) > 0]
    return {"features": name, "MAE_log_lift": round(float(np.mean(np.abs(p - y))), 3),
            "spearman_all": round(float(spearmanr(p, y).statistic) if np.std(p) > 0 else 0.0, 3),
            "within_shop_median": round(float(np.nanmedian(within)) if within else 0.0, 3),
            "shops_ranked_right": f"{int(np.nansum(np.array(within) > 0))}/{len(np.unique(g))}"}


def main() -> None:
    m = load()
    y, g = m["y"].to_numpy(), m["handle"].to_numpy()
    print(f"{m.handle.nunique()} shops · {len(m)} posts")
    rows = [score("baseline: every post = shop's usual", np.zeros(len(m)), y, g)]
    sets = {"no picture tags": [],
            "CLIP zero-shot draft tags": ["jewellery_shown", "face", "background", "amount"],
            "Model D tags (jewellery_shown, face)": ["jewellery_shown_d", "face_d"]}
    for name, pic in sets.items():
        X = features(m, pic)
        p = np.zeros(len(m))
        for tr, te in LeaveOneGroupOut().split(X, y, g):
            p[te] = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=20,
                                                  random_state=0).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
        rows.append(score(name, p, y, g))
    res = pd.DataFrame(rows)
    (HERE / "reports").mkdir(exist_ok=True)
    res.to_csv(HERE / "reports" / "model_b_results.csv", index=False)
    print(res.to_string(index=False))

    # the final model: trained on every usable post (Model D tags included), saved with its test scores
    import joblib
    X = features(m, sets["Model D tags (jewellery_shown, face)"])
    final = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=20, random_state=0).fit(X, y)
    (HERE / "models").mkdir(exist_ok=True)
    joblib.dump({"model": final, "features": list(X.columns), "target": "log(post lift)", "tests": rows,
                 "trained_on": f"{m.handle.nunique()} shops, {len(m)} posts"}, HERE / "models" / "model_b_post_lift.joblib")
    print("saved models/model_b_post_lift.joblib")

    # plain view: lift by how the jewellery is shown (Model D tags), median over posts
    view = m.groupby("jewellery_shown_d")["lift"].agg(["count", "median"]).round(2)
    print("\nmedian lift by how jewellery is shown:\n", view.to_string())


if __name__ == "__main__":
    main()
