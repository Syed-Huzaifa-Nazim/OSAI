"""Which post and reel traits go with more engagement for Pakistani jewellery shops? (evidence for the new gaps)

  .venv/bin/python test_effects.py

Each trait is tested INSIDE each shop first: the shop's median log-lift of posts with the trait minus posts without it
(a shop counts only if it has at least MIN_EACH posts on both sides). So a big shop and a small shop are compared fairly,
and a shop's general popularity cannot fake an effect. Then, across shops: Wilcoxon signed-rank test on those differences
(are they above zero?), corrected for testing many traits (Benjamini-Hochberg, 5%).
  posts : lift = likes+comments / the shop's median post (usable shops: usual post >= 10 likes+comments; posts < 1 day
          old left out). Traits from Model C (caption type), Model D (how the jewellery is shown, face), format, OCR.
  reels : view lift = views / the shop's median reel views. Traits from reel_features.py and reel_quality.py; numeric
          traits are split at the shop's own median (e.g. "shorter than this shop's usual reel").
Writes reports/effects_posts.csv and reports/effects_reels.csv.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
MIN_EACH = 3              # posts needed on each side inside a shop
MIN_SHOPS = 8             # shops needed before a trait is tested at all
ALPHA = 0.05


def bh(p: np.ndarray) -> np.ndarray:
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    q[order] = np.minimum.accumulate((p[order] * n / np.arange(1, n + 1))[::-1])[::-1]
    return np.minimum(q, 1)


def test(df: pd.DataFrame, y: str, traits: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for name, mask in traits.items():
        mask = mask.fillna(False).astype(bool)
        diffs, share = [], []
        for _, g in df.groupby("handle"):
            m = mask.loc[g.index]
            share.append(m.mean())
            if m.sum() >= MIN_EACH and (~m).sum() >= MIN_EACH:
                diffs.append(g.loc[m, y].median() - g.loc[~m, y].median())
        row = {"trait": name, "posts_with_trait": int(mask.sum()), "shops_using_it": int((np.array(share) > 0).sum()),
               "shops_tested": len(diffs)}
        if len(diffs) >= MIN_SHOPS:
            d = np.array(diffs)
            row.update({"effect_x": round(float(np.exp(np.median(d))), 2), "shops_where_better": int((d > 0).sum()),
                        "p": float(wilcoxon(d).pvalue)})
        rows.append(row)
    out = pd.DataFrame(rows)
    tested = out["p"].notna() if "p" in out else pd.Series(False, index=out.index)
    out["p_corrected"] = np.nan
    if tested.any():
        out.loc[tested, "p_corrected"] = bh(out.loc[tested, "p"].to_numpy())
    out["proven"] = out["p_corrected"] < ALPHA
    out["verdict"] = np.select(
        [out["proven"] & (out.get("effect_x", 1) > 1), out["proven"], out["p"].notna() if "p" in out else False],
        ["helps (proven)", "hurts (proven)", "not proven"], "too few shops to test")
    return out.round({"p": 4, "p_corrected": 4})


def posts_effects() -> pd.DataFrame:
    d = pd.read_csv(HERE / "datasets" / "posts_dataset.csv")
    d["inter"] = d["likes"] + d["comments"]
    usual = d.groupby("handle")["inter"].median()
    m = d[d.handle.isin(usual[usual >= 10].index) & ~d.young_post & (d.lift > 0)].copy()
    m["y"] = np.log(m["lift"])
    cap = pd.read_csv(HERE / "datasets" / "captions_predicted.csv").drop(columns=["handle"])
    pic = pd.read_csv(HERE / "labels" / "pictures_tags_model.csv")
    for tag in ("jewellery_shown", "face"):
        pic[f"{tag}_d"] = pic[f"{tag}_verified"].fillna(pic[f"{tag}_model"])
    m = m.merge(cap, on="shortcode", how="left").merge(
        pic[["shortcode", "jewellery_shown_d", "face_d", "text_on_image", "price_on_image", "sale_words_on_image"]],
        on="shortcode", how="left").set_index(pd.RangeIndex(len(m)))
    traits = {f"caption: {c[3:].replace('_', ' ')}": m[c] == 1 for c in cap.columns if c.startswith("is_")}
    traits.update({f"picture: jewellery {v.replace('_', ' ')}": m["jewellery_shown_d"] == v for v in ("worn", "in_hand", "displayed")})
    traits.update({"picture: a face shown": m["face_d"] == "face",
                   "picture: text on the picture": m["text_on_image"].astype(str).str.lower() == "true",
                   "picture: price on the picture": m["price_on_image"].astype(str).str.lower() == "true",
                   "format: reel": m["format"] == "reel", "format: carousel": m["format"] == "carousel",
                   "format: photo": m["format"] == "photo"})
    print(f"posts: {m.handle.nunique()} shops, {len(m)} posts")
    return test(m, "y", traits)


def reels_effects() -> pd.DataFrame | None:
    f = HERE / "datasets" / "reels_dataset.csv"
    if not f.exists():
        print("reels_dataset.csv not built yet (run reel_features.py)")
        return None
    r = pd.read_csv(f)
    q = HERE / "data" / "reel_parts" / "quality.csv"
    if q.exists():
        r = r.merge(pd.read_csv(q), on="shortcode", how="left")
    r = r[~r.young_post & r.views.notna() & (r.views > 0)].copy()
    r["view_lift"] = r["views"] / r.groupby("handle")["views"].transform("median")
    r = r[r.groupby("handle")["views"].transform("size") >= 2 * MIN_EACH].reset_index(drop=True)
    r["y"] = np.log(r["view_lift"])
    above = lambda c: r[c] > r.groupby("handle")[c].transform("median")   # noqa: E731
    traits = {"text on screen in the first 3 s": r["text_in_first_3s"], "a face in the first 3 s": r["face_in_first_3s"],
              "a scene cut in the first 3 s": r["cut_in_first_3s"], "someone speaking (voice)": r["has_voice"],
              "has sound": r["has_sound"],
              "jewellery worn in the first frame": r["jewellery_shown_first_frame"] == "worn",
              "shorter than the shop's usual reel": r["duration_s"] < r.groupby("handle")["duration_s"].transform("median"),
              "more cuts than the shop's usual reel": above("cuts_per_10s")}
    if "reel_quality" in r:
        traits["sharper / better-looking than the shop's usual reel"] = above("reel_quality")
    print(f"reels: {r.handle.nunique()} shops, {len(r)} reels")
    return test(r, "y", traits)


def main() -> None:
    (HERE / "reports").mkdir(exist_ok=True)
    pd.set_option("display.width", 200)
    p = posts_effects()
    p.to_csv(HERE / "reports" / "effects_posts.csv", index=False)
    print(p.to_string(index=False), "\n")
    r = reels_effects()
    if r is not None:
        r.to_csv(HERE / "reports" / "effects_reels.csv", index=False)
        print(r.to_string(index=False))


if __name__ == "__main__":
    main()
