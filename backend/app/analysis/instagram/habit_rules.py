"""Plain-language wording and example-post picking for each account habit.

The wording is fixed text. The numbers it shows, and which accounts count as
"typical", come from the data (see peer.py and the measured post results).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from .features import CTA_WORDS, HASHTAG


def _n(x: float, digits: int = 0) -> str:
    return f"{x:,.{digits}f}"


@dataclass(frozen=True)
class Habit:
    metric: str                 # benchmark / feature name
    category: str               # gaps_opportunities.category
    label: str                  # short name used in the sentence "<label>: ..."
    show: Callable[[float], str]
    rng: Callable[[float, float], str]   # "X to Y" for the typical range
    high_title: str
    low_title: str
    high_idea: str
    low_idea: str
    trait: str                  # how example posts are picked (see trait_scores)


HABITS: list[Habit] = [
    Habit("feat_posts_per_week", "content", "Posting rate", lambda v: f"{_n(v, 1)} posts a week",
          lambda a, b: f"{_n(a, 1)} – {_n(b, 1)} posts a week",
          "Your competitor posts more often than most similar accounts.",
          "Your competitor posts less often than most similar accounts.",
          "Try posting a little more often for a few weeks and watch what happens to your likes and comments.",
          "They post less often than most accounts like them. Check whether fewer, stronger posts could work for you too.",
          "recent"),
    Habit("feat_avg_hashtags", "social_engagement", "Hashtags", lambda v: f"{_n(v, 1)} hashtags per post",
          lambda a, b: f"{_n(a, 1)} – {_n(b, 1)} hashtags per post",
          "Your competitor uses more hashtags per post than most similar accounts.",
          "Your competitor uses fewer hashtags per post than most similar accounts.",
          "Test adding a few relevant hashtags to your posts and compare the results.",
          "Test using fewer hashtags. A short, focused set may work better for you.",
          "hashtags"),
    Habit("feat_pct_posts_with_hashtags", "social_engagement", "Posts with hashtags", lambda v: f"{_n(100 * v)}% of posts use hashtags",
          lambda a, b: f"{_n(100 * a)}% – {_n(100 * b)}% of posts",
          "Your competitor uses hashtags in more of their posts than most similar accounts.",
          "Your competitor uses hashtags in fewer of their posts than most similar accounts.",
          "Try adding hashtags to every post for a few weeks and compare the results.",
          "Try leaving hashtags off some posts and compare the results.",
          "hashtags"),
    Habit("feat_avg_caption_length", "content", "Caption length", lambda v: f"{_n(v)} characters per caption",
          lambda a, b: f"{_n(a)} – {_n(b)} characters",
          "Your competitor writes longer captions than most similar accounts.",
          "Your competitor writes shorter captions than most similar accounts.",
          "Try longer captions that explain the product or tell a short story.",
          "Try shorter captions that get to the point quickly.",
          "length"),
    Habit("feat_pct_captions_with_question", "social_engagement", "Questions in captions", lambda v: f"{_n(100 * v)}% of captions ask a question",
          lambda a, b: f"{_n(100 * a)}% – {_n(100 * b)}% of captions",
          "Your competitor asks the audience a question in more of their captions than most similar accounts.",
          "Your competitor asks the audience a question in fewer of their captions than most similar accounts.",
          "Try ending some captions with a question to invite comments.",
          "Their captions are more direct than yours. Try statements and offers instead of questions.",
          "question"),
    Habit("feat_pct_captions_with_cta", "conversion", "Calls to action", lambda v: f"{_n(100 * v)}% of captions tell people what to do",
          lambda a, b: f"{_n(100 * a)}% – {_n(100 * b)}% of captions",
          "Your competitor tells people what to do (like \"order now\" or \"DM us\") in more captions than most similar accounts.",
          "Your competitor tells people what to do (like \"order now\" or \"DM us\") in fewer captions than most similar accounts.",
          "Add a clear next step, like \"DM us to order\", to some of your captions.",
          "Their captions are less pushy. Try mixing in posts without a sales message.",
          "cta"),
    Habit("feat_days_since_last_post", "content", "Time since the last post", lambda v: f"{_n(v)} days since the last post",
          lambda a, b: f"{_n(a)} – {_n(b)} days",
          "Your competitor has been quiet for longer than most similar accounts.",
          "Your competitor posted more recently than most similar accounts.",
          "Their account looks less active right now. Keep your own posting steady so you stay visible.",
          "Keep your posting regular so your account never looks inactive.",
          "recent"),
    Habit("feat_gap_std_days", "content", "Regular posting", lambda v: f"{_n(v, 1)} days of unevenness between posts",
          lambda a, b: f"{_n(a, 1)} – {_n(b, 1)} days of unevenness",
          "Your competitor posts at much more uneven times than most similar accounts.",
          "Your competitor posts on a steadier schedule than most similar accounts.",
          "Their posting comes in bursts. A steady schedule is not the only way to do it.",
          "Try a steady schedule, such as the same days every week.",
          "recent"),
]
BY_METRIC = {h.metric: h for h in HABITS}


def trait_scores(posts: pd.DataFrame, trait: str) -> pd.Series:
    """For picking example posts: a bigger number = the post shows more of this habit."""
    cap = posts["caption"].fillna("").astype(str)
    if trait == "recent":
        return posts["when"].astype("int64").where(posts["when"].notna(), -1).astype(float)
    if trait == "hashtags":
        return cap.map(lambda t: len(HASHTAG.findall(t))).astype(float)
    if trait == "length":
        return cap.str.len().astype(float)
    if trait == "question":
        return cap.str.contains(r"\?", regex=True).astype(float)
    if trait == "cta":
        return cap.map(lambda t: float(bool(CTA_WORDS.search(t))))
    return pd.Series(np.zeros(len(posts)), index=posts.index)


def pick_examples(posts: pd.DataFrame, trait: str, more_of_it: bool, n: int) -> pd.DataFrame:
    """The n posts that show most (or least) of a habit, best-performing first among ties."""
    d = posts.copy()
    d["_trait"] = trait_scores(d, trait)
    d["_res"] = d["results"].fillna(-1)
    if trait == "recent":
        return d.sort_values("_trait", ascending=False).head(n)
    return d.sort_values(["_trait", "_res"], ascending=[not more_of_it, False]).head(n)
