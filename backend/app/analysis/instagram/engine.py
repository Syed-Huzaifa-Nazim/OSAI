"""Instagram competitor analysis: scraped rows in, reviewable gaps out.

Three parts, kept honest about what each one is:
  1. Habit gaps   -- the trained Random Forest grades each account's engagement,
                     TreeSHAP says which habits moved each grade, and a habit is a
                     gap when it helps the competitor clearly more (gaps.py).
  2. Content gaps -- direct comparisons, no trained model: photo/video/carousel
                     mix and engagement trend (content_gaps.py).
  3. Comment mood -- comments labelled by an LLM (comment_gaps.py), only when an
                     LLM key is configured.

Output follows the gaps_opportunities table, so the existing Review Gaps
screen and checkpoint #1 work unchanged. Every gap carries evidence rows that
point at real scraped posts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.services import demo_data
from app.services.repository import new_id

from . import comment_gaps, content_gaps, gaps
from .features import account_features

logger = logging.getLogger("optistratix.analysis.instagram")

MODEL_PATH = Path(__file__).with_name("model.joblib")
_model = None

# feature -> (gaps_opportunities.category, how to show its value)
FEATURE_INFO: dict[str, tuple[str, str]] = {
    "feat_posts_per_week": ("content", "rate"),
    "feat_gap_std_days": ("content", "days"),
    "feat_days_since_last_post": ("content", "days"),
    "feat_avg_caption_length": ("content", "chars"),
    "feat_avg_hashtags": ("content", "number"),
    "feat_pct_posts_with_hashtags": ("content", "pct"),
    "feat_pct_captions_with_cta": ("conversion", "pct"),
    "feat_pct_captions_with_question": ("social_engagement", "pct"),
    "feat_bio_length": ("positioning", "chars"),
    "feat_bio_has_cta": ("conversion", "yesno"),
    "feat_has_website": ("positioning", "yesno"),
    "feat_highlights_count": ("positioning", "number"),
}


def get_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            return None
        import joblib
        _model = joblib.load(MODEL_PATH)
    return _model


# ------------------------------------------------------------------ helpers
def _fmt(value: float, kind: str) -> str:
    if kind == "pct":
        return f"{value:.0%} of posts"
    if kind == "rate":
        return f"{value:.1f} posts per week"
    if kind == "days":
        return f"{value:.0f} days"
    if kind == "chars":
        return f"{value:.0f} characters"
    if kind == "yesno":
        return "yes" if value >= 0.5 else "no"
    return f"{value:.1f}"


def _account(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The model's account fields, from the profile details on the post rows."""
    stats = next((r.get("profile_stats") for r in rows if r.get("profile_stats")), {}) or {}
    scraped = max((r.get("scraped_at") or "" for r in rows), default="") or None
    return {
        "followers_count": stats.get("followers_count"),
        "follows_count": stats.get("following_count", 0),
        "posts_count": stats.get("posts_count", len(rows)),
        "biography": stats.get("biography", ""),
        "is_verified": stats.get("is_verified", False),
        "website": stats.get("external_url"),
        "highlights_count": stats.get("highlights_count", 0),
        "category": stats.get("category"),
        "last_scraped_at": scraped or datetime.now(timezone.utc).isoformat(),
        "username": rows[0].get("profile_username") or rows[0].get("submitted_url", "?"),
    }


def _posts_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame({
        "caption": [r.get("caption") or "" for r in rows],
        "posted_at": [r.get("posted_at") for r in rows],
        "media_type": [r.get("media_type") for r in rows],
        "likes_count": [r.get("like_count") for r in rows],
        "comments_count": [r.get("comment_count") for r in rows],
    })


# Instagram's media_type -> the word the gaps use
FORMAT_OF = {"image": "photo", "video": "video / reel", "sidecar": "carousel"}


def post_format(row: dict[str, Any]) -> str:
    return FORMAT_OF.get(str(row.get("media_type") or "").lower(), "other")


def _evidence(
    rows: list[dict[str, Any]], who: str, kind: str = "caption", fmt: str | None = None
) -> dict[str, Any] | None:
    """One evidence row pointing at a real scraped post of this side.

    fmt limits it to posts of one format (e.g. "carousel"), so a format gap is
    never "proven" with a post of another format.
    """
    pool = [r for r in rows if post_format(r) == fmt] if fmt else rows
    ranked = sorted(pool, key=lambda r: r.get("engagement_count") or 0, reverse=True)
    for r in ranked:
        if not r.get("source_id"):
            continue
        if kind == "date" and r.get("posted_at"):
            quote = f"Posted on {str(r['posted_at'])[:10]}"
        else:
            quote = (r.get("caption") or "").strip().replace("\n", " ")[:180] or "(post without a caption)"
        return {
            "source_id": r["source_id"],
            "source_url": r.get("post_url") or r.get("submitted_url") or "",
            "source_title": f"@{who} {post_format(r)} post",
            "quote": quote,
            "relevance": 0.6,
        }
    return None


def _gap_row(project_id, title, description, category, priority, confidence, evidence, opportunity):
    return {
        "id": new_id("gap"),
        "project_id": project_id,
        "title": title[:200],
        "description": description,
        "category": category,
        "priority": priority,
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "evidence": [e for e in evidence if e],
        "opportunity": opportunity,
        "decision": "pending",
        "created_at": demo_data.iso(),
    }


# ------------------------------------------------------------------ main
def analyze_project(
    project_id: str,
    posts: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    call_llm=None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    """Returns (gap rows, warnings, summary) for one Instagram project."""
    warnings: list[str] = []
    own = [p for p in posts if p.get("role") == "own"]
    by_comp: dict[str, list[dict[str, Any]]] = {}
    for p in posts:
        if p.get("role") == "competitor":
            by_comp.setdefault(p.get("competitor_id") or "competitor", []).append(p)
    if not own or not by_comp:
        return [], ["Both your profile and a competitor need scraped posts before analysis."], {}

    comments_by_post: dict[str, list[str]] = {}
    for c in comments:
        comments_by_post.setdefault(c.get("post_id"), []).append(c.get("comment_text") or "")

    def side_comments(rows):
        return [t for r in rows for t in comments_by_post.get(r.get("id"), [])]

    model = get_model()
    if model is None:
        warnings.append(f"No trained model at {MODEL_PATH.name}; habit gaps were skipped.")

    ua, up = _account(own), _posts_frame(own)
    out: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"user": ua["username"], "competitors": []}

    for comp_rows in by_comp.values():
        ca, cp = _account(comp_rows), _posts_frame(comp_rows)
        who = ca["username"]
        # What each part of the analysis found, shown to the user even when a
        # part produced no gap, so an empty result is never a mystery.
        comp_info: dict[str, Any] = {
            "competitor": who,
            "model": {"status": "skipped", "reason": "", "habit_gaps": 0},
            "media_mix": {},
            "trend": {},
            "comments": {"status": "skipped", "reason": "", "gaps": 0},
            "media_quality": {"status": "not_connected",
                              "reason": "Image and video quality scoring is not connected yet."},
        }

        # ---- 1. habit gaps (trained model + SHAP)
        if model is None:
            comp_info["model"]["reason"] = "No trained model file (model.joblib) was found."
        else:
            if not ua["followers_count"] or not ca["followers_count"]:
                comp_info["model"]["reason"] = "Followers were not scraped for one side."
                warnings.append(
                    f"Followers were not available for one side (vs @{who}); re-scrape "
                    "to get profile details. Habit gaps were skipped for this pair."
                )
            elif len(up) < 3 or len(cp) < 3:
                comp_info["model"]["reason"] = "Fewer than 3 posts on one side."
                warnings.append(f"Fewer than 3 posts on one side (vs @{who}); habit gaps skipped.")
            else:
                res = gaps.find_gaps(model, account_features(ua, up), account_features(ca, cp))
                n_before = len(out)
                comp_info["model"] = {
                    "status": "ran",
                    "reason": "",
                    "user_grade": res["user"]["grade"],
                    "user_good_chance": round(res["user"]["probabilities"].get("good", 0.0), 3),
                    "competitor_grade": res["competitor"]["grade"],
                    "competitor_good_chance": round(res["competitor"]["probabilities"].get("good", 0.0), 3),
                    "difference": round(res["good_chance_difference"], 3),
                    "clear_difference": res["clear_difference"],
                    "habit_gaps": 0,
                }
                low = not res["clear_difference"]
                comp_info["model"]["low_confidence"] = low
                if low:
                    warnings.append(
                        f"@{who} is not clearly ahead of you on the engagement model "
                        f"(difference {res['good_chance_difference']*100:+.0f} points; 10 needed), so "
                        "habit differences are shown as low confidence."
                    )
                lead = res["good_chance_difference"]
                for g in res["gaps"]:
                    category, kind = FEATURE_INFO.get(g["feature"], ("content", "number"))
                    size = g["gap_size"]
                    priority = "low" if low else "high" if size >= 0.04 else "medium" if size >= 0.02 else "low"
                    ev_kind = "date" if g["feature"] in (
                        "feat_posts_per_week", "feat_gap_std_days", "feat_days_since_last_post") else "caption"
                    caution = (
                        f"Low confidence: @{who} is not clearly ahead of you overall "
                        f"({lead*100:+.0f} points on the engagement model; 10 are needed), so treat "
                        "this as a weak signal. "
                    ) if low else ""
                    out.append(_gap_row(
                        project_id,
                        f"{g['label']}: @{who} differs from you" + (" (low confidence)" if low else ""),
                        (caution +
                         f"@{who}: {_fmt(g['competitor_value'], kind)}. You: {_fmt(g['user_value'], kind)}. "
                         f"In our engagement model this habit lifts @{who}'s chance of a 'good' "
                         f"engagement grade by {g['competitor_shap']*100:+.1f} points, against "
                         f"{g['user_shap']*100:+.1f} for you. This is a pattern learned from about "
                         f"800 accounts, linked to engagement rate; it is not proof that changing "
                         f"it will cause growth."),
                        category, priority, (max(0.1, 0.4 + lead) if low else 0.5 + lead),
                        [_evidence(comp_rows, who, ev_kind), _evidence(own, ua["username"], ev_kind)],
                        (f"Compare how you and @{who} handle {g['label'].lower()} and decide "
                         f"whether testing a change fits your brand."),
                    ))
                comp_info["model"]["habit_gaps"] = len(out) - n_before
                if comp_info["model"]["habit_gaps"] == 0:
                    warnings.append(f"No habit helps @{who} clearly more than it helps you "
                                    "(each needs at least 1 point of difference).")

        # ---- 2. content gaps (direct comparison)
        n_posts = len(up) + len(cp)
        u_trend = content_gaps.engagement_trend(up, ua["followers_count"])
        c_trend = content_gaps.engagement_trend(cp, ca["followers_count"])
        comp_info["media_mix"] = {
            "user": {k: round(v, 3) for k, v in content_gaps.media_mix(up).items()},
            "competitor": {k: round(v, 3) for k, v in content_gaps.media_mix(cp).items()},
            "gaps": 0,
        }
        comp_info["trend"] = {
            "user": None if u_trend is None else round(u_trend, 3),
            "competitor": None if c_trend is None else round(c_trend, 3),
            "gaps": 0,
        }
        for g in content_gaps.find_content_gaps(
            {"followers_count": ua["followers_count"]}, up,
            {"followers_count": ca["followers_count"]}, cp,
        ):
            size = g["gap_size"]
            if g["feature"] == "engagement_trend":
                desc = (f"@{who}'s recent posts get {g['competitor_value']:+.0%} engagement per "
                        f"follower compared with its older posts; yours changed by {g['user_value']:+.0%}.")
                category, priority = "social_engagement", ("high" if size >= 0.5 else "medium")
                opp = f"Look at what @{who} changed in its recent posts."
            else:
                desc = (f"@{who} uses {g['label'].replace('Use of ', '')} in "
                        f"{g['competitor_value']:.0%} of posts; you use them in {g['user_value']:.0%}. "
                        "This is a difference in approach, not a measure of better or worse.")
                category = "content"
                priority = "high" if size >= 0.5 else "medium" if size >= 0.35 else "low"
                opp = f"Consider testing more {g['label'].replace('Use of ', '')}."
            fmt = g["feature"].replace("media_", "", 1) if g["feature"].startswith("media_") else None
            comp_info["trend" if g["feature"] == "engagement_trend" else "media_mix"]["gaps"] += 1
            out.append(_gap_row(
                project_id, f"{g['label']}: @{who} differs from you", desc, category, priority,
                min(0.9, 0.4 + n_posts / 40),
                [_evidence(comp_rows, who, fmt=fmt), _evidence(own, ua["username"])], opp,
            ))

        # ---- 3. comment mood (LLM)
        if call_llm is None:
            comp_info["comments"]["reason"] = "No LLM key (GROQ_API_KEY) is set."
            if not any("Comment mood" in w for w in warnings):
                warnings.append("Comment mood was skipped: no LLM key (GROQ_API_KEY) is set.")
        else:
            try:
                res = comment_gaps.find_comment_gaps(side_comments(own), side_comments(comp_rows), call_llm)

                def mood(s: dict[str, Any]) -> dict[str, Any]:
                    r3 = lambda x: None if x is None else round(x, 3)  # noqa: E731
                    return {"comments": s["n_comments"], "scored": s["n_scored"],
                            "positive": r3(s["positive"]), "negative": r3(s["negative"]),
                            "neutral": r3(s["neutral"])}

                comp_info["comments"] = {
                    "status": "skipped" if res.get("note") else "ran",
                    "reason": res.get("note") or "",
                    "user": mood(res["user"]),
                    "competitor": mood(res["competitor"]),
                    "gaps": len(res.get("gaps", [])),
                }
                if res.get("note"):
                    warnings.append(f"Comments vs @{who}: {res['note']}")
                elif not res.get("gaps"):
                    u, c = res["user"], res["competitor"]
                    behind = (c["positive"] - u["positive"]) > 0 or (u["negative"] - c["negative"]) > 0
                    why = ("the difference is under 15 points, so it is not reported as a gap"
                           if behind else "your comments are as positive or more positive, so there is no gap")
                    warnings.append(
                        f"Comment mood was analysed: you {u['positive']:.0%} positive, {u['negative']:.0%} "
                        f"negative; @{who} {c['positive']:.0%} positive, {c['negative']:.0%} negative. "
                        f"{why[0].upper() + why[1:]}.")
                for g in res.get("gaps", []):
                    n = (res["user"]["n_scored"] or 0) + (res["competitor"]["n_scored"] or 0)
                    out.append(_gap_row(
                        project_id, f"{g['label']}: @{who} differs from you",
                        (f"{g['label']}: @{who} {g['competitor_value']:.0%}, you {g['user_value']:.0%} "
                         f"(comments labelled positive, negative or neutral by an LLM; "
                         f"{n} comments in total)."),
                        "audience", "high" if g["gap_size"] >= 0.3 else "medium",
                        min(0.9, 0.4 + n / 100),
                        [_evidence(comp_rows, who), _evidence(own, ua["username"])],
                        f"Read the comments on your and @{who}'s posts to see what drives the difference.",
                    ))
            except Exception as exc:  # noqa: BLE001 - comments are an extra
                comp_info["comments"]["reason"] = f"Could not be computed ({exc})."
                warnings.append(f"Comment mood vs @{who} could not be computed ({exc}).")

        summary["competitors"].append(comp_info)

    # Gaps without any evidence would break the 'every claim is cited' rule.
    out = [g for g in out if g["evidence"]]
    return out, warnings, summary