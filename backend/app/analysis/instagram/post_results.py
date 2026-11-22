"""How each post did compared with that account's own usual post.

Measured directly from the scraped likes and comments. Nothing is predicted and
nothing is typed in: a post is "strong" if it is in the top third of its own
account's posts, "weak" if it is in the bottom third.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

FORMAT_NAMES = {"image": "photo", "video": "video / reel", "sidecar": "carousel"}
MIN_GROUP = 3          # need a few posts before a middle value means anything
CAPTION_CHARS = 140


def prepare(posts: pd.DataFrame) -> pd.DataFrame:
    """Adds format, results (likes + comments) and strong / normal / weak to a posts table."""
    d = posts.copy().reset_index(drop=True)
    d["format"] = (d["media_type"].fillna("other").astype(str).str.lower().map(lambda x: FORMAT_NAMES.get(x, "other")))
    likes = pd.to_numeric(d["likes_count"], errors="coerce")
    likes = likes.where(likes >= 0)                       # negative = hidden likes
    comments = pd.to_numeric(d["comments_count"], errors="coerce").fillna(0).clip(lower=0)
    d["results"] = likes + comments
    rank = d["results"].rank(pct=True, method="average")
    d["level"] = np.where(rank.isna(), "unknown", np.where(rank <= 1 / 3, "weak", np.where(rank > 2 / 3, "strong", "normal")))
    d["when"] = pd.to_datetime(d["posted_at"], errors="coerce", utc=True).where(lambda s: s.dt.year >= 2010)
    return d


def usual_results(d: pd.DataFrame) -> float | None:
    v = d["results"].dropna()
    return None if v.empty else float(v.median())


def format_shares(d: pd.DataFrame) -> dict[str, float]:
    kinds = d.loc[d["format"] != "other", "format"]
    return {} if kinds.empty else {k: float(v) for k, v in kinds.value_counts(normalize=True).items()}


def format_counts(d: pd.DataFrame) -> dict[str, int]:
    return {k: int(v) for k, v in d["format"].value_counts().items()}


def lift(d: pd.DataFrame, fmt: str) -> float | None:
    """How a format's posts do against the account's usual post (1.0 = the same, 2.0 = twice as well)."""
    sub = d.loc[d["format"] == fmt, "results"].dropna()
    usual = usual_results(d)
    if len(sub) < MIN_GROUP or not usual:
        return None
    return float(sub.median() / usual)


def more_often_p(k_comp: int, n_comp: int, k_user: int, n_user: int) -> float:
    """Fisher exact test: is the competitor's share of this format really higher, or just chance?"""
    _, p = fisher_exact([[k_comp, n_comp - k_comp], [k_user, n_user - k_user]], alternative="greater")
    return float(p)


def group_p(d: pd.DataFrame, mask: pd.Series, alternative: str) -> float | None:
    """Mann-Whitney test: do the posts in `mask` really get less ("less") or more ("greater") than the rest?"""
    a = d.loc[mask, "results"].dropna()
    b = d.loc[~mask, "results"].dropna()
    if len(a) < MIN_GROUP or len(b) < MIN_GROUP:
        return None
    _, p = mannwhitneyu(a, b, alternative=alternative)
    return float(p)


def group_lift(d: pd.DataFrame, mask: pd.Series) -> float | None:
    """How the posts in `mask` do against the account's usual post (1.0 = the same)."""
    sub = d.loc[mask, "results"].dropna()
    usual = usual_results(d)
    if len(sub) < MIN_GROUP or not usual:
        return None
    return float(sub.median() / usual)


def worse_format_p(d: pd.DataFrame, fmt: str) -> float | None:
    """Do this format's posts really get less than the account's other posts?"""
    return group_p(d, d["format"] == fmt, "less")


def engagement_rate(d: pd.DataFrame, followers: float | None) -> float | None:
    v = d["results"].dropna()
    if v.empty or not followers or followers <= 0:
        return None
    return float(v.mean() / followers)


def excerpt(text: Any, n: int = CAPTION_CHARS) -> str:
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def example(row: pd.Series, who: str) -> dict[str, Any]:
    """One post, shaped for the post card on the screen."""
    when = row.get("when")
    return {
        "who": who,
        "postUrl": row.get("post_url") or "",
        "imageUrl": row.get("media_url") or "",
        "date": None if pd.isna(when) else when.strftime("%d %b %Y"),
        "format": row.get("format", "other"),
        "likes": None if pd.isna(row.get("likes_count")) or row.get("likes_count") < 0 else int(row["likes_count"]),
        "comments": None if pd.isna(row.get("comments_count")) else int(row["comments_count"]),
        "caption": excerpt(row.get("caption")),
        "level": row.get("level", "unknown"),
    }
