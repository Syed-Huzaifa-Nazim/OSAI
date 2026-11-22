"""Layer 4: how the pictures and videos look, and whether that goes with results.

The scores come from models we trained ourselves (media_scoring.py). Two kinds of finding:
  - the competitor's pictures or videos score higher than yours (Mann-Whitney test), and
  - on YOUR account, posts whose pictures score higher also get more likes and comments
    (Spearman correlation): the measured link between how a picture looks and how it performs.
"""
from __future__ import annotations

import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

from . import media_scoring as ms, post_results as pr
from .gap_common import MIN_POSTS, P_SHOWN, P_STRONG, Pair, _evidence, _gap, _p, bh_accept

TITLES = {
    "image_quality": ("Your competitor's photos look better made than yours.", "photos"),
    "video_quality": ("Your competitor's videos look better made than yours.", "videos"),
    "memorability": ("Your competitor's pictures are easier to remember than yours.", "pictures"),
    "reel_quality": ("Your competitor's reels look better made than yours.", "reels"),
}
WHY = {
    "image_quality": "Look at their best-scoring photos below and compare light, sharpness and framing with yours.",
    "video_quality": "Look at their best-scoring videos below and compare light, steadiness and sharpness with yours.",
    "memorability": "Look at their most memorable pictures below. What do they show that yours do not?",
    "reel_quality": "Look at their best-scoring reels below and compare light, sharpness and framing with yours.",
}
WEAK_TITLES = {
    "image_quality": "Your lower-quality photos get fewer likes and comments.",
    "video_quality": "Your lower-quality videos get fewer likes and comments.",
    "memorability": "Your less memorable pictures get fewer likes and comments.",
    "reel_quality": "Your lower-quality reels get fewer likes and comments.",
}


def _fmt(kind: str, v: float) -> str:
    return f"{v:.2f}" if kind == "memorability" else f"{v:.1f}"


def analyze(pair: Pair, up: pd.DataFrame, cp: pd.DataFrame, stats_u: dict, stats_c: dict):
    gaps: list[dict] = []
    status = ms.status()
    info = {"status": "ran" if ms.any_available() else "not_trained", "models": status,
            "scored": {"user": stats_u, "competitor": stats_c}, "gaps": 0, "reason": ""}
    if not ms.any_available():
        info["status"] = "not_trained"
        info["reason"] = ms.unavailable_reason()
        return gaps, info

    # ---- competitor vs you
    cand = {}
    for kind in TITLES:
        if not status[kind]["available"]:
            continue
        a, b = cp[kind].dropna(), up[kind].dropna()
        if len(a) < pr.MIN_GROUP or len(b) < pr.MIN_GROUP or a.median() <= b.median():
            continue
        cand[kind] = float(mannwhitneyu(a, b, alternative="greater")[1])
    for kind in sorted(bh_accept(cand), key=lambda k: cand[k]):
        title, noun = TITLES[kind]
        med_c, med_u = float(cp[kind].median()), float(up[kind].median())
        s = status[kind]
        best = cp.dropna(subset=[kind]).sort_values(kind, ascending=False).head(3)
        worst = up.dropna(subset=[kind]).sort_values(kind).head(2)
        ex = [pr.example(r, "competitor") for _, r in best.iterrows()] + [pr.example(r, "you") for _, r in worst.iterrows()]
        gaps.append(_gap(
            pair.project_id, title,
            f"On a scale from {ms.KINDS[kind]['scale']}, their {noun} score about {_fmt(kind, med_c)} on average. Yours score about {_fmt(kind, med_u)}.",
            pair.why(WHY[kind]), "content", pair.how_sure("High" if cand[kind] < P_STRONG else "Medium"),
            _evidence(best, pair.who, pair.ca) + _evidence(worst, pair.me, pair.ua),
            {"kind": "media", "who": pair.who, "context": pair.context, "examples": ex,
             "numbers": [{"label": f"Average {ms.KINDS[kind]['label'].lower()}", "you": _fmt(kind, med_u), "competitor": _fmt(kind, med_c), "typical": None}],
             "technical": [f"Mann-Whitney test {_p(cand[kind])} after correcting for testing {len(cand)} scores (shown only below {P_SHOWN}).",
                           f"How the score is made: {s['description']} ({s['n_train']} items rated by people). "
                           f"On ratings it had not seen it agreed with people at a rank correlation of {s['srcc']:.2f}."]}))
        info["gaps"] += 1

    # ---- on your own account: does how a picture looks go with how it performs?
    link = {}
    for kind in TITLES:
        if not status[kind]["available"]:
            continue
        both = up[[kind, "results"]].dropna()
        if len(both) < MIN_POSTS:
            continue
        rho, p = spearmanr(both[kind], both["results"])
        if rho > 0:
            link[kind] = (float(p) / 2 if p == p else 1.0, float(rho), len(both))     # one-sided: higher score, more likes
    for kind in sorted(bh_accept({k: v[0] for k, v in link.items()}), key=lambda k: link[k][0]):
        p, rho, n = link[kind]
        low = up.dropna(subset=[kind]).sort_values(kind).head(3)
        s = status[kind]
        gaps.append(_gap(
            pair.project_id, WEAK_TITLES[kind],
            f"Across your {n} scored posts, the ones with a higher {ms.KINDS[kind]['label'].lower()} score tend to get more likes and comments (correlation {rho:.2f}).",
            "This is a pattern inside your own account, so it does not depend on the competitor. Improving it may help, but this does not prove it.",
            "content", pair.how_sure("High" if p < P_STRONG else "Medium", uses_context=False),
            _evidence(low, pair.me, pair.ua),
            {"kind": "media", "who": pair.me, "context": pair.context, "examples": [pr.example(r, "you") for _, r in low.iterrows()],
             "numbers": [{"label": "Link between score and results", "you": f"correlation {rho:.2f} over {n} posts", "competitor": None, "typical": None}],
             "technical": [f"Spearman correlation {rho:.2f}, one-sided {_p(p)} after correcting for testing {len(link)} scores.",
                           f"How the score is made: {s['description']} ({s['n_train']} items rated by people). "
                           f"On ratings it had not seen it agreed with people at a rank correlation of {s['srcc']:.2f}."]}))
        info["gaps"] += 1
    return gaps, info
