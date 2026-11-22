"""Layer 5: when and how often each account posts, and how far its reels reach.

Three kinds of finding, each decided by a statistical test on the scraped posts (nothing is typed in):

  Posting time   The competitor's posts made at one time of day (or on weekends / weekdays) get more likes and
                 comments than their other posts (Mann-Whitney test, inside their own account), and you post at that
                 time less often than they do. Several times are tested at once, so Benjamini-Hochberg removes the
                 ones that pass by luck. The most promising time that is not proven is shown as "worth testing".
  How often      The competitor's gaps between posts are really shorter than yours (Mann-Whitney test). Always shown
                 as "worth testing": one account has one posting rate, so 30 posts cannot show that posting more
                 brings more likes (and among the 997 reference accounts, accounts that post more often get FEWER
                 likes and comments per post).
  Reel reach     The competitor's reels get more views per follower than yours (Mann-Whitney test). Views are divided
                 by followers so a bigger account does not win just for being bigger.

Times are shown in the shop's time zone (settings.instagram_timezone, Pakistan by default); Instagram gives UTC.
"""
from __future__ import annotations

import pandas as pd
from scipy.stats import mannwhitneyu

from . import post_results as pr
from .gap_common import NOT_PROVEN, P_SHOWN, P_STRONG, Pair, _evidence, _gap, _p, bh_accept, count_text, more_text, vs_others

# Parts of the day: the usual convention (morning until noon, evening from 5 pm, night from 9 pm).
SLOTS = {"morning": (5, 12), "afternoon": (12, 17), "evening": (17, 21), "night": (21, 5)}
SLOT_TEXT = {
    "morning": "in the morning (5 am to 12 pm)",
    "afternoon": "in the afternoon (12 pm to 5 pm)",
    "evening": "in the evening (5 pm to 9 pm)",
    "night": "at night (9 pm to 5 am)",
}
TZ_NAMES = {"Asia/Karachi": "Pakistan"}


def _slot(hour: int) -> str:
    for name, (start, end) in SLOTS.items():
        if (start <= hour < end) if start < end else (hour >= start or hour < end):
            return name
    return "night"


def _local(d: pd.DataFrame, tz: str) -> pd.DataFrame:
    d = d.dropna(subset=["when"]).copy()
    local = d["when"].dt.tz_convert(tz)
    d["slot"] = local.dt.hour.map(_slot)
    d["weekend"] = local.dt.dayofweek >= 5          # Saturday and Sunday
    return d


def _per_week(d: pd.DataFrame) -> float | None:
    t = d["when"].dropna().sort_values()
    days = (t.iloc[-1] - t.iloc[0]).total_seconds() / 86400 if len(t) > 1 else 0
    return None if days <= 0 else (len(t) - 1) / (days / 7)


def _span(d: pd.DataFrame) -> str:
    """Real counts instead of a decimal rate: "30 posts in 12 days (about 18 a week)"."""
    t = d["when"].dropna().sort_values()
    days = max(1, round((t.iloc[-1] - t.iloc[0]).total_seconds() / 86400))
    week = (len(t) - 1) / (days / 7)
    rate = "less than 1 a week" if week < 1 else f"about {round(week)} a week"
    return f"{len(t)} posts in {days} days ({rate})"


def _intervals(d: pd.DataFrame) -> pd.Series:
    return d["when"].dropna().sort_values().diff().dt.total_seconds().dropna() / 86400


def _posting_time(pair: Pair, u: pd.DataFrame, c: pd.DataFrame, tz: str, gaps: list, info: dict) -> None:
    where = TZ_NAMES.get(tz, tz)
    groups = {f"slot:{s}": (c["slot"] == s, u["slot"] == s, SLOT_TEXT[s]) for s in SLOTS}
    groups["day:weekend"] = (c["weekend"], u["weekend"], "at the weekend (Saturday and Sunday)")
    groups["day:weekday"] = (~c["weekend"], ~u["weekend"], "on weekdays (Monday to Friday)")
    cand: dict[str, float] = {}
    facts: dict[str, tuple] = {}
    for key, (mc, mu, text) in groups.items():
        if mu.mean() >= mc.mean():                 # you already post then at least as often as they do
            continue
        lift = pr.group_lift(c, mc)
        if lift is None or lift <= 1:              # it does not work better for them
            continue
        p = pr.group_p(c, mc, "greater")
        if p is None:
            continue
        cand[key], facts[key] = p, (mc, text, lift, int(mc.sum()), len(c), int(mu.sum()), len(u))
    info["time_tested"] = len(cand)
    accepted = bh_accept(cand)

    def _add(key: str, proven: bool) -> None:
        p = cand[key]
        mc, text, lift, kc, nc, ku, nu = facts[key]
        saw = (f"Your competitor's posts made {text} ({where} time) get {vs_others(lift)}. "
               f"Your competitor: {count_text(kc, nc, 'posts', 'their')} were made then. You: {count_text(ku, nu)}.")
        top = c[mc].sort_values("results", ascending=False).head(3)
        mine = u.sort_values("results", ascending=False).head(2)
        numbers = [
            {"label": f"Recent posts made {text}", "you": f"{ku} of {nu}", "competitor": f"{kc} of {nc}", "typical": None},
            {"label": "Likes + comments on those posts", "you": None, "competitor": vs_others(lift, short=True), "typical": None},
        ]
        if proven:
            gaps.append(_gap(
                pair.project_id, f"Post {text}: it works for your competitor, you rarely post then", saw,
                pair.why(f"Try this: post {text} for two weeks and see if those posts get more likes and comments."),
                "content", pair.how_sure("High" if p < P_STRONG else "Medium"),
                _evidence(top, pair.who, pair.ca) + _evidence(mine, pair.me, pair.ua),
                {"kind": "timing", "who": pair.who, "context": pair.context,
                 "examples": [pr.example(r, "competitor") for _, r in top.iterrows()] + [pr.example(r, "you") for _, r in mine.iterrows()],
                 "numbers": numbers,
                 "technical": [f"Mann-Whitney test on their own posts: {_p(p)} after correcting for testing {len(cand)} times "
                               f"(shown only below {P_SHOWN}). Times are {where} time ({tz})."]}))
        else:
            gaps.append(_gap(
                pair.project_id, f"Worth trying: posting {text}",
                saw + NOT_PROVEN,
                f"Try this: post {text} for two weeks and see if those posts get more likes and comments.",
                "content", "Low", _evidence(top, pair.who, pair.ca),
                {"kind": "timing", "who": pair.who, "context": pair.context, "unproven": True,
                 "examples": [pr.example(r, "competitor") for _, r in top.iterrows()], "numbers": numbers,
                 "technical": [f"Mann-Whitney test {_p(p)}: not significant after correcting for testing {len(cand)} times "
                               f"(a proven gap needs p below {P_SHOWN})."]}))
        info["time_gaps"] += 1

    for key in sorted(accepted, key=cand.get):
        _add(key, True)
    for key in sorted((k for k in set(cand) - accepted if cand[k] < P_SHOWN), key=cand.get)[:1]:     # only the most promising unproven time
        _add(key, False)


def _frequency(pair: Pair, u: pd.DataFrame, c: pd.DataFrame, gaps: list, info: dict) -> None:
    ru, rc = _per_week(u), _per_week(c)
    iu, ic = _intervals(u), _intervals(c)
    if ru is None or rc is None or len(iu) < pr.MIN_GROUP or len(ic) < pr.MIN_GROUP:
        return
    info["frequency"] = {"user_per_week": round(ru, 1), "competitor_per_week": round(rc, 1)}
    if rc <= ru:
        return
    p = float(mannwhitneyu(ic, iu, alternative="less")[1])
    info["frequency"]["p"] = p
    if p >= P_SHOWN:
        return
    gaps.append(_gap(
        pair.project_id, "Worth trying: post more often, like your competitor",
        f"Your competitor's recent posts: {_span(c)}. Yours: {_span(u)}. The difference is real, "
        "not chance. But posting more does not always bring more likes: on Instagram, business accounts that post "
        "more often usually get fewer likes and comments per post.",
        "Try this: post a little more often for two weeks and see if your total likes and comments go up.",
        "content", "Low", [],
        {"kind": "timing", "who": pair.who, "context": pair.context, "unproven": True, "examples": [],
         "numbers": [{"label": "Recent posts", "you": _span(u), "competitor": _span(c), "typical": None}],
         "technical": [f"Mann-Whitney test on the days between posts: {_p(p)} (their gaps are shorter). Labelled 'worth "
                       "testing' because one account's posting rate cannot show cause and effect."]}))
    info["frequency"]["gap"] = True


def _reach(pair: Pair, u: pd.DataFrame, c: pd.DataFrame, gaps: list, info: dict) -> None:
    fu, fc = pair.ua.get("followers_count"), pair.ca.get("followers_count")
    if not fu or not fc:
        info["reach"] = {"status": "skipped", "reason": "Follower counts were not scraped."}
        return

    def _reels(d: pd.DataFrame) -> pd.DataFrame:
        r = d[(d["format"] == "video / reel")].copy()
        r["views"] = pd.to_numeric(r["views"], errors="coerce")
        return r[r["views"] > 0]

    ru, rc = _reels(u), _reels(c)
    info["reach"] = {"status": "ran", "user_reels": len(ru), "competitor_reels": len(rc)}
    if len(ru) < pr.MIN_GROUP or len(rc) < pr.MIN_GROUP:
        info["reach"]["reason"] = "Too few reels with view counts on one side."
        return
    vu, vc = ru["views"] / fu, rc["views"] / fc
    if vc.median() <= vu.median():
        return
    p = float(mannwhitneyu(vc, vu, alternative="greater")[1])
    info["reach"]["p"] = p
    if p >= P_SHOWN:
        return
    top = rc.sort_values("views", ascending=False).head(3)
    low = ru.sort_values("views").head(2)
    gaps.append(_gap(
        pair.project_id, "Your competitor's reels are watched by more people, for the size of their account",
        f"For every 100 followers, a typical reel of theirs gets about {vc.median() * 100:,.0f} views. "
        f"A typical reel of yours gets about {vu.median() * 100:,.0f} views for every 100 followers.",
        pair.why("Try this: watch their most-watched reels below. Notice how they start, how long they are and what they show, then try the same in your next reels."),
        "content", pair.how_sure("High" if p < P_STRONG else "Medium"),
        _evidence(top, pair.who, pair.ca) + _evidence(low, pair.me, pair.ua),
        {"kind": "reach", "who": pair.who, "context": pair.context,
         "examples": [pr.example(r, "competitor") for _, r in top.iterrows()] + [pr.example(r, "you") for _, r in low.iterrows()],
         "numbers": [
             {"label": "Views for every 100 followers, typical reel", "you": f"{vu.median() * 100:,.0f}", "competitor": f"{vc.median() * 100:,.0f}", "typical": None},
             {"label": "Views, typical reel", "you": f"{ru['views'].median():,.0f}", "competitor": f"{rc['views'].median():,.0f}", "typical": None},
         ],
         "technical": [f"Mann-Whitney test on views per follower: {_p(p)} (shown only below {P_SHOWN})."]}))
    info["reach"]["gap"] = True


def analyze(pair: Pair, up: pd.DataFrame, cp: pd.DataFrame, tz: str) -> tuple[list[dict], dict]:
    gaps: list[dict] = []
    info: dict = {"status": "ran", "reason": "", "timezone": tz, "time_gaps": 0, "time_tested": 0, "frequency": None, "reach": None}
    u, c = _local(up, tz), _local(cp, tz)
    if len(u) < pr.MIN_GROUP or len(c) < pr.MIN_GROUP:
        info.update(status="skipped", reason="Too few dated posts on one side.")
        return gaps, info
    _posting_time(pair, u, c, tz, gaps, info)
    _frequency(pair, u, c, gaps, info)
    _reach(pair, up, cp, gaps, info)
    return gaps, info
