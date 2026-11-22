"""Builds peer_benchmark.json: what is "typical" for Instagram business accounts of a similar size.

Run once (or again if the training data changes):

    python -m app.analysis.instagram.build_peer_benchmark \
        --train instagram_train.csv --test instagram_test.csv --accounts instagram_accounts_table.csv

The numbers come from the 997 public business profiles the grader was trained on.
Accounts are split into three equal-sized groups by follower count (small, medium,
large). For every habit we keep the sorted values of the accounts in each group, so
the app can say "you post less often than 80% of accounts your size" instead of
using a number somebody typed in.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

OUT = Path(__file__).with_name("peer_benchmark.json")

HABIT_METRICS = [
    "feat_posts_per_week", "feat_avg_hashtags", "feat_pct_posts_with_hashtags",
    "feat_avg_caption_length", "feat_pct_captions_with_question", "feat_pct_captions_with_cta",
    "feat_days_since_last_post", "feat_gap_std_days",
]
YES_NO_METRICS = ["feat_has_website", "feat_bio_has_cta"]


def _associations(d: pd.DataFrame, q: float = 0.05) -> dict:
    """Which habits really go with engagement among accounts of the same size?

    Habit and engagement are ranked within each size group, the groups are pooled, and the Spearman
    correlation is tested. With ten habits tested at once, Benjamini-Hochberg removes the lucky ones.
    Only habits that survive can become gaps.
    """
    rows = []
    for m in HABIT_METRICS + YES_NO_METRICS:
        parts = []
        for _, g in d.groupby("info_size_band"):
            x, y = pd.to_numeric(g[m], errors="coerce"), g["target_engagement_rate"]
            ok = x.notna() & y.notna()
            parts.append(pd.DataFrame({"x": x[ok].rank(pct=True), "y": y[ok].rank(pct=True)}))
        pool = pd.concat(parts)
        rho, p = spearmanr(pool.x, pool.y)
        rows.append((m, float(rho), float(p), int(len(pool))))
    order = sorted(rows, key=lambda r: r[2])
    cut = max((i for i, r in enumerate(order, 1) if r[2] <= q * i / len(order)), default=0)
    sig = {r[0] for r in order[:cut]}
    return {m: {"rho": round(rho, 4), "p": round(p, 6), "n": n, "significant": m in sig} for m, rho, p, n in rows}


def build(train: str, test: str, accounts: str) -> dict:
    d = pd.concat([pd.read_csv(train), pd.read_csv(test)], ignore_index=True)
    a = pd.read_csv(accounts)[["info_account", "target_engagement_rate"]]
    d = d.merge(a, on="info_account", how="left")

    # three follower groups of (nearly) equal size, exactly as the grades were made
    edges = {}
    for band in ("small", "medium", "large"):
        edges[band] = (int(d.loc[d.info_size_band == band, "feat_followers"].min()),
                       int(d.loc[d.info_size_band == band, "feat_followers"].max()))
    upper_small, upper_medium = edges["small"][1], edges["medium"][1]
    lower_medium, lower_large = edges["medium"][0], edges["large"][0]

    out = {
        "source": "997 public Instagram business profiles (the grader's training accounts)",
        "bands": {},
        "associations": _associations(d),
        # an account between two groups goes to the nearer one
        "band_edges": [int((upper_small + lower_medium) / 2), int((upper_medium + lower_large) / 2)],
    }
    for band in ("small", "medium", "large"):
        g = d[d.info_size_band == band]
        metrics = {}
        for m in HABIT_METRICS + YES_NO_METRICS:
            vals = pd.to_numeric(g[m], errors="coerce").dropna().to_numpy(dtype=float)
            metrics[m] = [round(float(v), 4) for v in np.sort(vals)]
        er = pd.to_numeric(g["target_engagement_rate"], errors="coerce").dropna().to_numpy(dtype=float)
        metrics["engagement_rate"] = [round(float(v), 6) for v in np.sort(er)]
        out["bands"][band] = {
            "followers_min": edges[band][0], "followers_max": edges[band][1],
            "n_accounts": int(len(g)), "metrics": metrics,
        }
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True); ap.add_argument("--test", required=True)
    ap.add_argument("--accounts", required=True)
    args = ap.parse_args()
    data = build(args.train, args.test, args.accounts)
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print("wrote", OUT, f"({OUT.stat().st_size // 1024} KB)")
