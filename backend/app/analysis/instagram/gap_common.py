"""Pieces every gap layer shares: the gap record, evidence, certainty and the multiple-test correction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.services import demo_data
from app.services.repository import new_id

from . import post_results as pr

LEVELS = ["Low", "Medium", "High"]
CONFIDENCE = {"Low": 0.3, "Medium": 0.6, "High": 0.9}   # only to fill the database column

# --- conventions (standard, explained in the app) ---
P_SHOWN = 0.05          # a difference is shown only if a test says it is unlikely to be chance
P_STRONG = 0.01         # ... and "High" certainty if it is very unlikely
MIN_POSTS = 10          # fewer posts than this caps the certainty at "Low"


NOT_PROVEN = " This is based on only a few posts, so treat it as an idea to try, not a sure result."


def count_text(k: int, n: int, noun: str = "posts", whose: str = "your") -> str:
    """'none of your last 20 posts', 'almost all of their last 30 posts (28)', '5 of your last 20 posts'."""
    if k == 0:
        return f"none of {whose} last {n} {noun}"
    if k == n:
        return f"all of {whose} last {n} {noun}"
    if k / n >= 0.8:
        return f"almost all of {whose} last {n} {noun} ({k})"
    return f"{k} of {whose} last {n} {noun}"


def more_text(effect: float, measure: str = "likes and comments") -> str:
    """1.37 -> 'about 40% more likes and comments'; 2.3 -> 'about 2.3 times the likes and comments'."""
    if effect >= 2:
        return f"about {effect:.1f} times the {measure}"
    return f"about {max(10, round((effect - 1) * 10) * 10)}% more {measure}"


def vs_others(effect: float, short: bool = False) -> str:
    """Their posts like this against their other posts: 'about 40% more likes and comments than their other posts'."""
    if short:
        return f"about {effect:.1f} times their usual" if effect >= 2 else f"about {max(10, round((effect - 1) * 10) * 10)}% more than usual"
    if effect >= 2:
        return f"about {effect:.1f} times the likes and comments of their other posts"
    return f"{more_text(effect)} than their other posts"


def _ordinal(n: float) -> str:
    n = int(round(n))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def _down(level: str) -> str:
    return LEVELS[max(0, LEVELS.index(level) - 1)]


def bh_accept(pvals: dict[str, float], q: float = P_SHOWN) -> set[str]:
    """Benjamini-Hochberg: when many things are tested at once, some pass by luck.
    Returns the keys that still pass after allowing for that."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, cut = len(items), -1
    for i, (_, p) in enumerate(items, start=1):
        if p <= q * i / m:
            cut = i
    return {k for k, _ in items[:cut]} if cut > 0 else set()


def _evidence(examples: pd.DataFrame, handle: str, account: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for _, r in examples.iterrows():
        out.append({
            "source_id": r.get("source_id") or r.get("id") or "",
            "source_url": r.get("post_url") or account["profile_url"] or "",
            "source_title": f"@{handle} {r.get('format', 'post')} post",
            "quote": pr.excerpt(r.get("caption")) or "(post without a caption)",
            "relevance": 1.0,
        })
    return out


def _gap(project_id, title, saw, why, category, how_sure, evidence, details):
    details = {**details, "howSure": how_sure}
    return {
        "id": new_id("gap"), "project_id": project_id, "title": title[:200], "description": saw,
        "category": category, "priority": "medium",       # the seller sets the priority at review
        "confidence": CONFIDENCE[how_sure], "evidence": [e for e in evidence if e.get("source_url") is not None],
        "opportunity": why, "decision": "pending", "created_at": demo_data.iso(), "details": details,
    }


def _context_sentence(context: str, handle: str) -> str:
    if context == "unknown":
        return (f"We could not compare your overall likes and comments with @{handle}'s, so treat this as "
                "something to test, not as proof of a problem")
    if context == "behind":
        return f"@{handle} gets more likes and comments than you compared with accounts of their size"
    if context == "even":
        return f"You and @{handle} do about equally well, so treat this as something to test, not as proof of a problem"
    return f"You already do better than @{handle} overall, so this is a difference, not a problem"


@dataclass
class Pair:
    """Everything a layer needs to know about the two accounts being compared."""
    project_id: str
    me: str
    who: str
    ua: dict[str, Any]
    ca: dict[str, Any]
    context: str            # behind / even / ahead / unknown
    few: bool               # fewer than MIN_POSTS posts on one side

    def how_sure(self, base: str, *, uses_context: bool = True) -> str:
        level = base
        if uses_context and self.context in ("even", "ahead", "unknown"):
            level = _down(level)
        return "Low" if self.few else level

    @property
    def ctx(self) -> str:
        return self.context

    def why(self, idea: str) -> str:
        return f"{_context_sentence(self.ctx, self.who)}. {idea}"
