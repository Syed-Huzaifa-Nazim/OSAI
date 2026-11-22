"""Copies the trained models and the jewellery-shop evidence into the app (backend).

  .venv/bin/python export_to_app.py

  models/picture_heads.joblib        -> backend/.../instagram/models/picture_heads.joblib   (Model D)
  models/caption_model/              -> backend/.../instagram/models/caption_model/        (Model C)
  reports/effects_posts.csv + effects_reels.csv + datasets/accounts_dataset.csv
                                     -> backend/.../instagram/models/jewellery_evidence.json
"""
from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
APP = HERE.parent / "backend" / "app" / "analysis" / "instagram" / "models"
POST_TRAITS = {"picture: a face shown": "face", "picture: jewellery worn": "worn", "caption: price": "price",
               "caption: offer": "offer", "caption: call to order": "call_to_order", "caption: product details": "product_details",
               "caption: new arrival": "new_arrival", "caption: review": "review", "caption: event season": "event_season"}
REEL_TRAITS = {"a face in the first 3 s": "reel_face", "text on screen in the first 3 s": "reel_text",
               "a scene cut in the first 3 s": "reel_cut", "someone speaking (voice)": "reel_voice",
               "more cuts than the shop's usual reel": "reel_fast", "shorter than the shop's usual reel": "reel_short"}


def traits() -> dict:
    out = {}
    for f, names, measure in (("effects_posts.csv", POST_TRAITS, "likes and comments"), ("effects_reels.csv", REEL_TRAITS, "views")):
        d = pd.read_csv(HERE / "reports" / f)
        for _, r in d.iterrows():
            key = names.get(r["trait"])
            if key is None:
                continue
            out[key] = {"trait": r["trait"], "measure": measure, "verdict": r["verdict"],
                        "effect_x": None if pd.isna(r.get("effect_x")) else float(r["effect_x"]),
                        "shops_tested": int(r["shops_tested"]),
                        "shops_where_better": None if pd.isna(r.get("shops_where_better")) else int(r["shops_where_better"]),
                        "p_corrected": None if pd.isna(r.get("p_corrected")) else float(r["p_corrected"])}
    return out


def typical_shares() -> dict:
    """For each trait: the share of posts (or reels) with it at the typical jewellery shop (median over shops)."""
    out = {}
    pic = pd.read_csv(HERE / "labels" / "pictures_tags_model.csv")
    pic["face_t"] = pic["face_verified"].fillna(pic["face_model"]) == "face"
    pic["worn_t"] = pic["jewellery_shown_verified"].fillna(pic["jewellery_shown_model"]) == "worn"
    for key, col in (("face", "face_t"), ("worn", "worn_t")):
        out[key] = pic.groupby("handle")[col].mean()
    reels = pd.read_csv(HERE / "datasets" / "reels_dataset.csv")
    reels["has_voice"] = reels["vad_speech_seconds"].fillna(0) >= 1.0
    for key, col in (("reel_face", "face_in_first_3s"), ("reel_text", "text_in_first_3s"), ("reel_cut", "cut_in_first_3s"),
                     ("reel_voice", "has_voice")):
        out[key] = reels.groupby("handle")[col].apply(lambda s: s.dropna().astype(bool).mean())
    cap = pd.read_csv(HERE / "datasets" / "captions_predicted.csv")
    for key in ("price", "offer", "call_to_order", "product_details", "new_arrival", "review", "event_season"):
        if f"is_{key}" in cap:
            out[key] = cap.groupby("handle")[f"is_{key}"].mean()
    return {k: {"typical_share": round(float(v.median()), 3), "shops": int(v.notna().sum())} for k, v in out.items()}


def benchmark() -> dict:
    d = pd.read_csv(HERE / "datasets" / "posts_dataset.csv")
    d = d[~d.young_post & d.likes.notna()]
    a = d.groupby("handle").agg(followers=("followers", "first"), er=("engagement_pct", "median"))
    bands = {"1k-5k": (1_000, 5_000), "5k-20k": (5_000, 20_000), "20k-100k": (20_000, 100_000)}
    out = {}
    for name, (lo, hi) in bands.items():
        s = a[(a.followers >= lo) & (a.followers < hi)].er.dropna()
        out[name] = {"min_followers": lo, "max_followers": hi, "shops": int(len(s)),
                     "engagement_pct": {q: round(float(np.quantile(s, v)), 3) for q, v in (("p25", .25), ("median", .5), ("p75", .75))}}
    return out


def main() -> None:
    APP.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "models" / "picture_heads.joblib", APP / "picture_heads.joblib")
    print("copied picture_heads.joblib")
    cm = HERE / "models" / "caption_model"
    if (cm / "head.pt").exists():
        shutil.copytree(cm, APP / "caption_model", dirs_exist_ok=True)
        print("copied caption_model/")
    else:
        print("caption_model/ not trained yet: skipped")
    ev = {"domain": "Pakistani jewellery shops on Instagram (1k-100k followers)", "built": date.today().isoformat(),
          "method": "each shop compared with itself; Wilcoxon signed-rank across shops; Benjamini-Hochberg 5%",
          "traits": traits(), "typical": typical_shares(), "engagement_benchmark": benchmark()}
    (APP / "jewellery_evidence.json").write_text(json.dumps(ev, indent=1))
    print(f"wrote jewellery_evidence.json ({len(ev['traits'])} traits)")


if __name__ == "__main__":
    main()
