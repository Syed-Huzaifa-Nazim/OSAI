"""Instagram competitor analysis: scraped posts in, plain-language gaps out.

What the analysis does, layer by layer:

  1. Overall results  -- how each account's likes and comments compare with accounts of a
                         similar size (measured, from the 997 training accounts).
  2. Habits           -- posting rate, hashtags, captions, calls to action... shown side by side
                         with similar accounts as a TABLE, not as gaps (see the note in _analyze_pair).
                         Profile checklist: a website link, when 3 in 4 similar accounts have one.
  3. Post formats     -- photos / reels / carousels, tested statistically (Fisher exact test).
  4. Post results     -- which posts do better or worse than that account's usual post.
  5. Grader (trained) -- the Random Forest + SHAP. Its grade and the habits behind it are shown
                         under "technical details"; they no longer decide what is a gap.

Comment mood is no longer a gap: it described the audience, not something a strategy can change.
Topics are turned off by default (INSTAGRAM_TOPICS=false): the topic model reads English captions only.

Every number that decides whether something is shown is either measured from the posts, taken
from the similar accounts, or a standard statistical convention (quarters, p < 0.05, thirds).
There are no typed-in difference limits any more. See HAND_SET at the bottom for the full list.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import get_settings

from . import activity_gaps, content_layer, gaps, habit_rules as hr, media_gaps, media_scoring, peer, post_results as pr, topic_gaps
from .features import account_features
from .gap_common import (  # noqa: F401
    CONFIDENCE, LEVELS, MIN_POSTS, P_SHOWN, P_STRONG, Pair, _context_sentence, _down, _evidence, _gap, _ordinal, _p, bh_accept,
    NOT_PROVEN, count_text, more_text, vs_others,
)

logger = logging.getLogger("optistratix.analysis.instagram")

MODEL_PATH = Path(__file__).with_name("model.joblib")
_model = None

KIND_ORDER = {"format": 0, "reel": 1, "picture": 2, "caption": 3, "timing": 4, "reach": 5, "topic": 6, "hashtag": 7, "media": 8,
              "weakness": 9, "habit": 10, "profile": 11}

# --- the few conventions used (all standard, all explained in the app) ---
UNUSUAL_LOW, UNUSUAL_HIGH = 25, 75     # bottom / top quarter of similar accounts (profile checklist: 75% have it)

HAND_SET = {
    "P_SHOWN": P_SHOWN, "P_STRONG": P_STRONG, "UNUSUAL": (UNUSUAL_LOW, UNUSUAL_HIGH), "MIN_POSTS": MIN_POSTS,
    "MIN_GROUP (post_results)": pr.MIN_GROUP, "strong/weak = thirds": (1 / 3, 2 / 3),
}

# habits left out of the comparison table: the reference data is from 2023, so "days since the last post" there is
# months, and "unevenness between posts" is hard to read for a seller
TABLE_SKIP = {"feat_days_since_last_post", "feat_gap_std_days"}

FORMAT_TITLE = {"photo": "photos", "video / reel": "videos and reels", "carousel": "carousels"}
FORMAT_SAW = {"photo": "photos", "video / reel": "videos or reels", "carousel": "carousels (posts you swipe through)"}
PROFILE_ITEMS = [
    ("feat_has_website", "a website link in their profile", "a link to your shop or website",
     "Add a link to your shop or website in your profile so people can buy or contact you.", "positioning"),
]

# feature -> how to write its value in the technical panel
FEATURE_INFO: dict[str, tuple[str, str]] = {
    "feat_posts_per_week": ("content", "rate"), "feat_gap_std_days": ("content", "days"),
    "feat_days_since_last_post": ("content", "days"), "feat_avg_caption_length": ("content", "chars"),
    "feat_avg_hashtags": ("content", "number"), "feat_pct_posts_with_hashtags": ("content", "pct"),
    "feat_pct_captions_with_cta": ("conversion", "pct"), "feat_pct_captions_with_question": ("social_engagement", "pct"),
    "feat_bio_length": ("positioning", "chars"), "feat_bio_has_cta": ("conversion", "yesno"),
    "feat_has_website": ("positioning", "yesno"), "feat_highlights_count": ("positioning", "number"),
}


def get_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            return None
        import joblib
        _model = joblib.load(MODEL_PATH)
    return _model


# ------------------------------------------------------------------ small helpers
def _show(h, value) -> str:
    """A habit's value in words, or 'not measured' (e.g. posting rhythm when post dates are missing)."""
    return "not measured" if value is None or pd.isna(value) else h.show(value)


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
        "profile_url": rows[0].get("profile_url") or rows[0].get("submitted_url") or "",
        "source_id": rows[0].get("source_id"),
    }


def _posts_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame({
        "id": [r.get("id") for r in rows],
        "source_id": [r.get("source_id") for r in rows],
        "caption": [r.get("caption") or "" for r in rows],
        "posted_at": [r.get("posted_at") for r in rows],
        "media_type": [r.get("media_type") for r in rows],
        "likes_count": [r.get("like_count") for r in rows],
        "comments_count": [r.get("comment_count") for r in rows],
        "post_url": [r.get("post_url") for r in rows],
        "media_url": [r.get("media_url") for r in rows],
        "views": [r.get("video_view_count") for r in rows],
    })














# ------------------------------------------------------------------ the grader's summary (technical panel)
def _model_summary(model, ua, ca, up_raw, cp_raw) -> dict[str, Any]:
    u_feat, c_feat = account_features(ua, up_raw), account_features(ca, cp_raw)
    gu, gc = gaps.grade_account(model, u_feat), gaps.grade_account(model, c_feat)

    def show(d):
        items = []
        for it in d["items"]:
            v, f = it["value"], it["feature"]
            if v is None:
                text = "not measured"
            elif f in FEATURE_INFO:
                text = _fmt(v, FEATURE_INFO[f][1])
            elif f == "feat_is_verified" or f.startswith("feat_cat_"):
                text = "yes" if v >= 0.5 else "no"
            elif f == "feat_follow_ratio":
                text = f"{v:.1f}"
            else:
                text = f"{v:,.0f}"
            items.append({"label": re.sub(r"\s*\(.*\)$", "", it["label"]), "value_text": text,
                          "points": round(it["shap"] * 100, 1), "actionable": it["actionable"]})
        return {"start": round(d["base_good_chance"] * 100, 1), "items": items}

    def with_rest(drv, chance):
        shown = sum(i["points"] for i in drv["items"])
        drv["others_points"] = round(chance * 100 - drv["start"] - shown, 1)
        drv["final"] = round(chance * 100, 1)
        return drv

    return {
        "status": "ran", "reason": "",
        "user_grade": gu["grade"], "competitor_grade": gc["grade"],
        "user_good_chance": round(gu["probabilities"].get("good", 0.0), 3),
        "competitor_good_chance": round(gc["probabilities"].get("good", 0.0), 3),
        "user_drivers": with_rest(show(gaps.drivers(model, u_feat)), gu["probabilities"].get("good", 0.0)),
        "competitor_drivers": with_rest(show(gaps.drivers(model, c_feat)), gc["probabilities"].get("good", 0.0)),
    }


# ------------------------------------------------------------------ one seller vs one competitor
def _analyze_pair(project_id, own_rows, comp_rows, warnings, model):
    ua, ca = _account(own_rows), _account(comp_rows)
    me, who = ua["username"], ca["username"]
    up_raw, cp_raw = _posts_frame(own_rows), _posts_frame(comp_rows)
    up, cp = pr.prepare(up_raw), pr.prepare(cp_raw)
    n_u, n_c = len(up), len(cp)
    out: list[dict[str, Any]] = []
    strengths: list[dict[str, Any]] = []
    info: dict[str, Any] = {
        "competitor": who, "model": {"status": "skipped", "reason": ""},
        "results": {"status": "skipped", "reason": ""}, "habits": {"status": "skipped", "reason": "", "gaps": 0},
        "formats": {}, "topics": {"status": "skipped", "reason": ""}, "media": {"status": "skipped", "reason": ""},
        "activity": {"status": "skipped", "reason": ""}, "content": {"status": "skipped", "reason": ""},
    }
    few = min(n_u, n_c) < MIN_POSTS
    if few:
        warnings.append(f"Only {min(n_u, n_c)} posts were scraped for one side (vs @{who}); results are less certain. "
                        f"Scrape up to 30 posts per account for a clearer picture.")

    # ---- layer 1: overall results against similar accounts (measured)
    context, band_u, band_c, pu, pc = "unknown", None, None, None, None
    outside: list[str] = []                 # accounts too big (or too small) for the reference accounts
    if peer.available() and ua["followers_count"] and ca["followers_count"]:
        band_u, band_c = peer.band_of(ua["followers_count"]), peer.band_of(ca["followers_count"])
        outside = [f"@{h} has {int(f):,} followers" for h, f in ((me, ua["followers_count"]), (who, ca["followers_count"]))
                   if not peer.in_range(f)]
        if not outside:
            pu = peer.percentile("engagement_rate", band_u, pr.engagement_rate(up, ua["followers_count"]))
            pc = peer.percentile("engagement_rate", band_c, pr.engagement_rate(cp, ca["followers_count"]))
    qu, qc = peer.quarter(pu), peer.quarter(pc)
    if outside:
        lo, hi = peer.reference_range()
        info["results"]["reason"] = (
            f"{' and '.join(outside)}. The accounts we compare with have {lo:,} to {hi:,} followers, so a fair "
            "comparison with \"accounts your size\" is not possible. The two accounts are still compared with each other below.")
    elif qu is not None and qc is not None:
        context = "behind" if qc > qu else "ahead" if qu > qc else "even"
        info["results"] = {
            "status": "ran", "reason": "", "context": context,
            "user": {"percentile": pu, "quarter": qu, "posts": n_u, "band": band_u},
            "competitor": {"percentile": pc, "quarter": qc, "posts": n_c, "band": band_c},
            "peers": peer.band_info(band_u)["n_accounts"],
        }
    else:
        info["results"]["reason"] = "Follower counts were not scraped, so results cannot be compared with similar accounts."
        warnings.append(f"Follower counts were missing for one side (vs @{who}); re-scrape to compare with similar accounts.")

    pair = Pair(project_id=project_id, me=me, who=who, ua=ua, ca=ca, context=context, few=few)
    how_sure = pair.how_sure

    # ---- post formats (tested; many tests at once are corrected so luck does not pass for a finding)
    u_known, c_known = int((up["format"] != "other").sum()), int((cp["format"] != "other").sum())
    u_counts, c_counts = pr.format_counts(up), pr.format_counts(cp)
    info["formats"] = {"user": pr.format_shares(up), "competitor": pr.format_shares(cp), "gaps": 0, "weak_spots": 0}
    if u_known and c_known:
        more_p, lifts = {}, {}
        for fmt in ("photo", "video / reel", "carousel"):
            k_c, k_u = c_counts.get(fmt, 0), u_counts.get(fmt, 0)
            if k_c / c_known <= k_u / u_known:
                continue
            lift = pr.lift(cp, fmt)
            if k_c < pr.MIN_GROUP or lift is None or lift <= 1:
                continue                           # too few of their posts to tell, or it does not work for them
            more_p[fmt], lifts[fmt] = pr.more_often_p(k_c, c_known, k_u, u_known), lift
        for fmt in sorted(bh_accept(more_p), key=lambda f: more_p[f]):
            p, lift, phrase = more_p[fmt], lifts[fmt], FORMAT_TITLE[fmt]
            k_c, k_u = c_counts.get(fmt, 0), u_counts.get(fmt, 0)
            saw = (f"Your competitor: {count_text(k_c, c_known, 'posts', 'their')} are {FORMAT_SAW[fmt]}. "
                   f"You: {count_text(k_u, u_known)}.")
            if lift is not None:
                saw += f" Their {phrase} get {vs_others(lift)}."
            top_c = cp[cp["format"] == fmt].sort_values("results", ascending=False).head(3)
            mine = up.sort_values("results", ascending=False).head(2)
            ex = [pr.example(r, "competitor") for _, r in top_c.iterrows()] + [pr.example(r, "you") for _, r in mine.iterrows()]
            out.append(_gap(
                pair.project_id, f"Post more {phrase}: your competitor does, you rarely do", saw,
                pair.why(f"Try this: post a few {phrase} over the next two weeks and see if they get more likes and comments than your usual posts."), "content",
                pair.how_sure("High" if p < P_STRONG else "Medium"), _evidence(top_c, who, ca) + _evidence(mine, me, ua),
                {"kind": "format", "who": who, "context": context, "examples": ex,
                 "numbers": [{"label": f"Recent posts that are {phrase}", "you": f"{k_u} of {u_known}", "competitor": f"{k_c} of {c_known}", "typical": None}],
                 "technical": [f"Fisher exact test: {_p(p)} after correcting for testing {len(more_p)} formats (shown only below {P_SHOWN})."]
                              + ([f"Their {phrase}: median {lift:.2f}x their usual likes + comments."] if lift is not None else [])}))
            info["formats"]["gaps"] += 1
        # Not proven yet: the competitor really does post this more, and it works for them, but with this many posts it
        # could still be chance. Shown with "Low" certainty and labelled, so the seller has something to TEST.
        # "Worth testing" = a real difference before correcting for many tests (p below P_SHOWN), not after it.
        for fmt in sorted((f for f in set(more_p) - bh_accept(more_p) if more_p[f] < P_SHOWN), key=lambda f: more_p[f]):
            lift, phrase = lifts[fmt], FORMAT_TITLE[fmt]
            k_c, k_u = c_counts.get(fmt, 0), u_counts.get(fmt, 0)
            saw = (f"Your competitor: {count_text(k_c, c_known, 'posts', 'their')} are {FORMAT_SAW[fmt]}. "
                   f"You: {count_text(k_u, u_known)}.")
            if lift is not None:
                saw += f" Their {phrase} get {vs_others(lift)}."
            saw += NOT_PROVEN
            top_c = cp[cp["format"] == fmt].sort_values("results", ascending=False).head(3)
            out.append(_gap(
                pair.project_id, f"Worth trying: more {phrase}", saw,
                f"Try this: post a few {phrase} over the next two weeks and see if they get more likes and comments than your usual posts.", "content",
                "Low", _evidence(top_c, who, ca),
                {"kind": "format", "who": who, "context": context, "unproven": True,
                 "examples": [pr.example(r, "competitor") for _, r in top_c.iterrows()],
                 "numbers": [{"label": f"Recent posts that are {phrase}", "you": f"{k_u} of {u_known}", "competitor": f"{k_c} of {c_known}", "typical": None}],
                 "technical": [f"Fisher exact test {_p(more_p[fmt])}: not significant after correcting for {len(more_p)} formats "
                               f"(a proven gap needs p below {P_SHOWN})."]}))
            info["formats"]["worth_testing"] = info["formats"].get("worth_testing", 0) + 1

    # ---- your weak spots among formats, measured on your own posts
    weak_p = {f: pr.worse_format_p(up, f) for f in ("photo", "video / reel", "carousel")}
    weak_p = {f: p for f, p in weak_p.items() if p is not None}
    for fmt in sorted(bh_accept(weak_p), key=lambda f: weak_p[f]):
        p, phrase = weak_p[fmt], FORMAT_TITLE[fmt]
        med_fmt = float(up.loc[up["format"] == fmt, "results"].median())
        med_other = float(up.loc[up["format"] != fmt, "results"].median())
        low = up[up["format"] == fmt].sort_values("results").head(3)
        out.append(_gap(
            project_id, f"Your {phrase} get fewer likes and comments than your other posts",
            f"A typical post of yours gets about {med_other:,.0f} likes and comments. Your {phrase} get about {med_fmt:,.0f}.",
            f"This comes from your own posts, not from the competitor. Try posting fewer {phrase}, or make them differently, and see if your likes and comments go up.",
            "content", pair.how_sure("High" if p < P_STRONG else "Medium", uses_context=False), _evidence(low, me, ua),
            {"kind": "weakness", "who": me, "context": context, "examples": [pr.example(r, "you") for _, r in low.iterrows()],
             "numbers": [{"label": "Typical likes + comments", "you": f"{med_fmt:,.0f} ({phrase}) vs {med_other:,.0f} (other posts)", "competitor": None, "typical": None}],
             "technical": [f"Mann-Whitney test: {_p(p)} after correcting for testing {len(weak_p)} formats (shown only below {P_SHOWN})."]}))
        info["formats"]["weak_spots"] += 1
    for fmt in ("photo", "video / reel", "carousel"):
        p = pr.group_p(up, up["format"] == fmt, "greater")
        if p is not None and p in bh_accept({fmt: p}):
            m = up["format"] == fmt
            strengths.append({"kind": "format", "label": f"Your {FORMAT_TITLE[fmt]}",
                              "detail": f"They get about {up.loc[m, 'results'].median():,.0f} likes and comments, against {up.loc[~m, 'results'].median():,.0f} for your other posts."})

    # ---- layer 2: habits against similar accounts
    if band_u and band_c:
        try:
            uf, cf = account_features(ua, up_raw).iloc[0], account_features(ca, cp_raw).iloc[0]
        except ValueError as exc:
            info["habits"]["reason"] = str(exc)
            warnings.append(f"Habits vs @{who} were skipped: {exc}")
        else:
            # Habits are shown as a side-by-side table, never as gaps. In the 997 peer accounts the only habits linked
            # with engagement rate point the "wrong" way (posting more often and more evenly, and more calls to action,
            # go with FEWER likes per follower), and the posting-rhythm ones could only be measured for ~700 accounts
            # because of placeholder dates. That is a measurement effect, not advice a seller should follow.
            rows, related = [], 0
            for h in hr.HABITS:
                assoc = peer.association(h.metric)
                if assoc and assoc["significant"]:
                    related += 1
                if h.metric in TABLE_SKIP:
                    continue
                uv, cv = uf.get(h.metric), cf.get(h.metric)
                rng = None if outside else peer.typical_range(h.metric, band_u)
                rows.append({
                    "label": h.label, "you": _show(h, uv), "competitor": _show(h, cv),
                    "typical": h.rng(*rng) if rng else None,
                    "you_percentile": None if outside else peer.percentile(h.metric, band_u, uv),
                    "competitor_percentile": None if outside else peer.percentile(h.metric, band_c, cv),
                })
            info["habits"] = {"status": "ran", "reason": "", "checked": len(hr.HABITS) + len(PROFILE_ITEMS),
                              "related": related, "gaps": 0, "table": rows}

            # profile checklist: something they have and you do not
            for metric, they, you, idea, category in PROFILE_ITEMS:
                if not (cf.get(metric) >= 0.5 and uf.get(metric) < 0.5):
                    continue
                share = peer.share_yes(metric, band_u)
                if share is None or share * 100 < UNUSUAL_HIGH:
                    continue                                   # only things most (three quarters of) similar accounts have
                saw = f"@{who} has {they}. You do not. Most business accounts on Instagram have this (about {share:.0%})."
                bio = pr.excerpt(comp_rows[0].get("profile_stats", {}).get("biography") if isinstance(comp_rows[0].get("profile_stats"), dict) else "")
                out.append(_gap(
                    project_id, f"Your competitor has {they}, you don't", saw,
                    pair.why(idea), category,
                    how_sure("Medium"),
                    [{"source_id": ca["source_id"] or "", "source_url": ca["profile_url"], "source_title": f"@{who} profile",
                      "quote": bio or "(profile)", "relevance": 1.0}],
                    {"kind": "profile", "who": who, "context": context, "examples": [],
                     "numbers": [{"label": you[0].upper() + you[1:], "you": "no", "competitor": "yes",
                                  "typical": f"{share:.0%} of business accounts"}],
                     "technical": [f"A checklist item, not a finding about engagement: shown only when at least {UNUSUAL_HIGH}% of similar accounts have it."]}))
                info["habits"]["gaps"] += 1
    else:
        info["habits"]["reason"] = "Follower counts were not scraped, so habits cannot be compared with similar accounts."

    # ---- layer 3: what the posts are about, and hashtags
    try:
        t_gaps, t_strengths, t_info = topic_gaps.analyze(pair, up, cp)
        out.extend(t_gaps); strengths.extend(t_strengths); info["topics"] = t_info
    except Exception as exc:  # noqa: BLE001 - one layer failing must not lose the others
        logger.exception("Topic layer failed")
        info["topics"] = {"status": "error", "reason": str(exc)}
        warnings.append(f"The topic and hashtag layer failed for @{who}: {exc}")

    # ---- layer 5: when and how often they post, and how far their reels reach
    try:
        a_gaps, a_info = activity_gaps.analyze(pair, up, cp, get_settings().instagram_timezone)
        out.extend(a_gaps); info["activity"] = a_info
    except Exception as exc:  # noqa: BLE001 - one layer failing must not lose the others
        logger.exception("Activity layer failed")
        info["activity"] = {"status": "error", "reason": str(exc)}
        warnings.append(f"The posting time and reach layer failed for @{who}: {exc}")

    # ---- layer 4: pictures and videos (needs the models we trained)
    try:
        if get_settings().instagram_score_media and media_scoring.any_available():
            up_s, st_u = media_scoring.score_posts(up)
            cp_s, st_c = media_scoring.score_posts(cp)
            up, cp = up.join(up_s), cp.join(cp_s)
        else:
            st_u = st_c = {"posts": 0, "scored": 0, "failed": 0, "videos_skipped": 0}
            for d in (up, cp):
                for k in media_scoring.KINDS:
                    d[k] = float("nan")
        m_gaps, m_info = media_gaps.analyze(pair, up, cp, st_u, st_c)
        out.extend(m_gaps); info["media"] = m_info
    except Exception as exc:  # noqa: BLE001
        logger.exception("Media layer failed")
        info["media"] = {"status": "error", "reason": str(exc)}
        warnings.append(f"The picture and video layer failed for @{who}: {exc}")

    # ---- layer 6: what the captions say, what the pictures show, how the reels open (jewellery-shop models)
    try:
        if get_settings().instagram_score_media:
            up_t, st_u6 = content_layer.measure(up)
            cp_t, st_c6 = content_layer.measure(cp)
            up, cp = up.join(up_t), cp.join(cp_t)
            c_gaps, c_info = content_layer.analyze(pair, up, cp, st_u6, st_c6)
            out.extend(c_gaps); info["content"] = c_info
            strengths.extend(c_info.get("strengths", []))
        else:
            info["content"]["reason"] = "Picture and video scoring is turned off (INSTAGRAM_SCORE_MEDIA)."
    except Exception as exc:  # noqa: BLE001 - one layer failing must not lose the others
        logger.exception("Content layer failed")
        info["content"] = {"status": "error", "reason": str(exc)}
        warnings.append(f"The caption, picture and reel layer failed for @{who}: {exc}")

    # ---- what works for you, and the report the Strategist will read
    info["strengths"] = strengths
    info["report"] = {
        "works_for_you": strengths,
        "weak_spots": [{"id": g["id"], "title": g["title"]} for g in out if g["details"]["kind"] in ("weakness",) or
                       (g["details"]["kind"] == "media" and g["details"].get("who") == me)],
        "to_try": [{"id": g["id"], "title": g["title"]} for g in out if not g["details"].get("unproven") and
                   (g["details"]["kind"] in ("format", "timing", "reach", "topic", "hashtag", "habit", "profile", "caption", "picture", "reel")
                    or (g["details"]["kind"] == "media" and g["details"].get("who") == who))],
        "worth_testing": [{"id": g["id"], "title": g["title"]} for g in out if g["details"].get("unproven")],
    }

    # ---- the trained grader, for the technical panel only
    if model is not None and not (not ua["followers_count"] or not ca["followers_count"]):
        try:
            info["model"] = _model_summary(model, ua, ca, up_raw, cp_raw)
        except Exception as exc:  # noqa: BLE001 - the technical panel is optional
            info["model"]["reason"] = str(exc)
    elif model is None:
        info["model"]["reason"] = "No trained model file (model.joblib) was found."
    return out, info


# ------------------------------------------------------------------ entry point used by the pipeline
def analyze_project(project_id, posts, comments=None, call_llm=None):
    """Returns (gap rows, warnings, summary). `comments` and `call_llm` are kept for the pipeline's
    sake; comment mood is no longer a gap and no language model is needed to find gaps."""
    warnings: list[str] = []
    own = [p for p in posts if p.get("role") == "own"]
    by_comp: dict[str, list[dict[str, Any]]] = {}
    for p in posts:
        if p.get("role") == "competitor":
            by_comp.setdefault(p.get("competitor_id") or "competitor", []).append(p)
    if not own or not by_comp:
        return [], ["Both your profile and a competitor need scraped posts before analysis."], {}
    if not peer.available():
        warnings.append("peer_benchmark.json is missing, so habits cannot be compared with similar accounts.")

    model = get_model()
    out: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"user": _account(own)["username"], "competitors": []}
    for comp_rows in by_comp.values():
        gaps_for_pair, info = _analyze_pair(project_id, own, comp_rows, warnings, model)
        out.extend(gaps_for_pair)
        summary["competitors"].append(info)

    certainty = {lvl: i for i, lvl in enumerate(LEVELS)}
    out.sort(key=lambda g: (-certainty[g["details"]["howSure"]], KIND_ORDER[g["details"]["kind"]]))
    if not out:
        warnings.append("No difference between the two accounts was clear enough to find. With more posts "
                        "(scrape again for up to 30 per account) small differences become easier to see.")
    return out, warnings, summary
