"""Layer 3: what the posts are about, and which hashtags do well.

Topics come from the topic model trained on public business captions (topics.py). Hashtags are read
straight from the captions. Both are compared with the same tests as the post formats, and when many
topics or hashtags are tested at once the Benjamini-Hochberg correction removes the ones that pass by luck.
"""
from __future__ import annotations

import pandas as pd

from app.core.config import get_settings

from . import post_results as pr, topics
from .features import HASHTAG
from .gap_common import NOT_PROVEN, P_SHOWN, P_STRONG, Pair, _evidence, _gap, _p, bh_accept, count_text, more_text, vs_others

TOP_TAGS = 5            # at most this many hashtags are named in one gap


def _tag_sets(df: pd.DataFrame) -> pd.Series:
    return df["caption"].fillna("").map(lambda t: {m.lower() for m in HASHTAG.findall(t)})


def _best(df: pd.DataFrame, mask: pd.Series, n: int, ascending: bool = False) -> pd.DataFrame:
    return df[mask].sort_values("results", ascending=ascending).head(n)


def _examples(pair: Pair, comp_posts: pd.DataFrame, my_posts: pd.DataFrame):
    ex = [pr.example(r, "competitor") for _, r in comp_posts.iterrows()] + [pr.example(r, "you") for _, r in my_posts.iterrows()]
    ev = _evidence(comp_posts, pair.who, pair.ca) + _evidence(my_posts, pair.me, pair.ua)
    return ex, ev


def analyze(pair: Pair, up: pd.DataFrame, cp: pd.DataFrame):
    gaps, strengths = [], []
    info = {"status": "skipped", "reason": "", "gaps": 0, "weak_spots": 0, "hashtag_gaps": 0,
            "coverage": {}, "topics": {"user": {}, "competitor": {}}}

    # ------------------------------------------------------------ topics
    if get_settings().instagram_topics and topics.available():
        for d in (up, cp):
            ids = topics.assign(d["caption"].tolist())
            d["topic"] = ids
        up_known, cp_known = up["topic"].notna(), cp["topic"].notna()
        info["coverage"] = {"user": f"{int(up_known.sum())} of {len(up)}", "competitor": f"{int(cp_known.sum())} of {len(cp)}"}
        info["status"] = "ran"
        for key, d, known in (("user", up, up_known), ("competitor", cp, cp_known)):
            if known.any():
                share = d.loc[known, "topic"].astype(int).map(lambda i: topics.info(i)["name"]).value_counts(normalize=True)
                info["topics"][key] = {k: round(float(v), 3) for k, v in share.items()}
        n_u, n_c = int(up_known.sum()), int(cp_known.sum())
        usable = [t for t in sorted(set(up.loc[up_known, "topic"].astype(int)) | set(cp.loc[cp_known, "topic"].astype(int)))
                  if not topics.info(t)["generic"]]

        # --- the competitor posts about it more often, and it works for them
        more_p, lifts = {}, {}
        for t in usable:
            k_c, k_u = int((cp["topic"] == t).sum()), int((up["topic"] == t).sum())
            if n_u == 0 or n_c == 0 or k_c < pr.MIN_GROUP or k_c / n_c <= k_u / n_u:
                continue
            lift = pr.group_lift(cp, cp["topic"] == t)
            if lift is not None and lift < 1:
                continue
            more_p[str(t)] = pr.more_often_p(k_c, n_c, k_u, n_u)
            lifts[str(t)] = lift
        for key in sorted(bh_accept(more_p), key=lambda k: more_p[k]):
            t = int(key); meta = topics.info(t); name = meta["name"]
            k_c, k_u = int((cp["topic"] == t).sum()), int((up["topic"] == t).sum())
            saw = f"Your competitor: {count_text(k_c, n_c, 'posts', 'their')} are about this. You: {count_text(k_u, n_u)}."
            if lifts[key] is not None:
                saw += f" Their posts on it get {vs_others(lifts[key])}."
            if meta["terms"]:
                saw += f" Posts like this often use words such as: {', '.join(meta['terms'][:4])}."
            comp_posts = _best(cp, cp["topic"] == t, 3)
            my_posts = up.sort_values("results", ascending=False).head(2)
            ex, ev = _examples(pair, comp_posts, my_posts)
            gaps.append(_gap(
                pair.project_id, f"Post more about \"{name}\": your competitor does, you rarely do", saw,
                pair.why("Try this: make a few posts on this theme over the next two weeks and see how they do against your usual posts."), "content",
                pair.how_sure("High" if more_p[key] < P_STRONG else "Medium"), ev,
                {"kind": "topic", "who": pair.who, "context": pair.context, "examples": ex,
                 "numbers": [{"label": f"Posts about this theme", "you": f"{k_u} of {n_u}", "competitor": f"{k_c} of {n_c}", "typical": None}],
                 "technical": [f"Topic found by a model trained on public business captions; Fisher exact test {_p(more_p[key])} after correcting for testing {len(more_p)} themes (shown only below {P_SHOWN}).",
                               f"Posts where no theme could be read are left out ({info['coverage']['competitor']} and {info['coverage']['user']} could be read)."]}))
            info["gaps"] += 1

        # --- your own themes: weak spots and strengths
        def family(alternative: str):
            ps = {}
            for t in usable:
                if int((up["topic"] == t).sum()) >= pr.MIN_GROUP:
                    p = pr.group_p(up, up["topic"] == t, alternative)
                    if p is not None:
                        ps[str(t)] = p
            return ps, bh_accept(ps)

        weak_ps, weak_ok = family("less")
        for key in sorted(weak_ok, key=lambda k: weak_ps[k]):
            t = int(key); name = topics.info(t)["name"]
            mask = up["topic"] == t
            med, other = float(up.loc[mask, "results"].median()), float(up.loc[~mask, "results"].median())
            low = _best(up, mask, 3, ascending=True)
            gaps.append(_gap(
                pair.project_id, f"Your posts about \"{name}\" get fewer likes and comments than your other posts",
                f"A typical post of yours gets about {other:,.0f} likes and comments. Your posts on this theme get about {med:,.0f}.",
                "This comes from your own results, not from the competitor. Think about posting less on this theme, or changing how you do it.",
                "content", pair.how_sure("High" if weak_ps[key] < P_STRONG else "Medium", uses_context=False), _evidence(low, pair.me, pair.ua),
                {"kind": "weakness", "who": pair.me, "context": pair.context, "examples": [pr.example(r, "you") for _, r in low.iterrows()],
                 "numbers": [{"label": "Typical likes + comments", "you": f"{med:,.0f} (this theme) vs {other:,.0f} (other posts)", "competitor": None, "typical": None}],
                 "technical": [f"Mann-Whitney test {_p(weak_ps[key])} after correcting for testing {len(weak_ps)} themes."]}))
            info["weak_spots"] += 1
        good_ps, good_ok = family("greater")
        for key in sorted(good_ok, key=lambda k: good_ps[k]):
            t = int(key); mask = up["topic"] == t
            strengths.append({"kind": "topic", "label": f"Posts about \"{topics.info(t)['name']}\"",
                              "detail": f"They get about {up.loc[mask, 'results'].median():,.0f} likes and comments, against {up.loc[~mask, 'results'].median():,.0f} for your other posts."})
    elif not get_settings().instagram_topics:
        info["status"] = "off"
        info["reason"] = ("Turned off: the topic model can only read English captions, so it would miss most "
                          "Roman Urdu posts.")
    else:
        info["reason"] = "The topic model (topic_model.joblib) was not found."

    # ------------------------------------------------------------ hashtags
    up_tags, cp_tags = _tag_sets(up), _tag_sets(cp)
    all_tags = set().union(*cp_tags) if len(cp_tags) else set()
    cand_p, cand_lift = {}, {}
    for tag in all_tags:
        mask = cp_tags.map(lambda s, tag=tag: tag in s)
        if int((up_tags.map(lambda s, tag=tag: tag in s)).sum()) > 0:
            continue                                   # you already use it
        p = pr.group_p(cp, mask, "greater")
        lift = pr.group_lift(cp, mask)
        if p is not None and lift is not None and lift > 1:
            cand_p[tag], cand_lift[tag] = p, lift
    accepted = sorted(bh_accept(cand_p), key=lambda t: cand_p[t])[:TOP_TAGS]
    if accepted:
        mask_any = cp_tags.map(lambda s: any(t in s for t in accepted))
        comp_posts = _best(cp, mask_any, 3)
        my_posts = up.sort_values("results", ascending=False).head(2)
        ex, ev = _examples(pair, comp_posts, my_posts)
        listing = ", ".join(accepted)
        saw = ("Posts by your competitor that use these hashtags get more likes and comments than their other posts: "
               + "; ".join(f"{t} ({more_text(cand_lift[t])})" for t in accepted) + ". You have not used any of them.")
        gaps.append(_gap(
            pair.project_id, f"Try these hashtags: {listing}", saw,
            pair.why("Try this: add these hashtags to a few posts where they fit and see if those posts get more likes and comments."), "social_engagement",
            pair.how_sure("High" if min(cand_p[t] for t in accepted) < P_STRONG else "Medium"), ev,
            {"kind": "hashtag", "who": pair.who, "context": pair.context, "examples": ex,
             "numbers": [{"label": "Hashtags", "you": "not used", "competitor": listing, "typical": None}],
             "technical": [f"Each hashtag used in at least {pr.MIN_GROUP} of their posts was tested (Mann-Whitney), then corrected for testing {len(cand_p)} hashtags (shown only below {P_SHOWN})."]}))
        info["hashtag_gaps"] = 1
    elif any(p < P_SHOWN for p in cand_p.values()):
        # Not proven yet: their posts with these tags did better than their others, but with this many posts it could
        # still be chance. Shown with "Low" certainty and labelled, so the seller has something to TEST.
        maybe = sorted((t for t in cand_p if cand_p[t] < P_SHOWN), key=lambda t: cand_p[t])[:TOP_TAGS]
        mask_any = cp_tags.map(lambda s: any(t in s for t in maybe))
        comp_posts = _best(cp, mask_any, 3)
        listing = ", ".join(maybe)
        saw = ("Their posts with these hashtags got more likes and comments than their other posts: "
               + "; ".join(f"{t} ({more_text(cand_lift[t])})" for t in maybe)
               + ". You have not used them." + NOT_PROVEN)
        gaps.append(_gap(
            pair.project_id, f"Worth trying: hashtags {listing}", saw,
            "Try this: add these hashtags to a few posts where they fit and see if those posts get more likes and comments.",
            "social_engagement", "Low", _evidence(comp_posts, pair.who, pair.ca),
            {"kind": "hashtag", "who": pair.who, "context": pair.context, "unproven": True,
             "examples": [pr.example(r, "competitor") for _, r in comp_posts.iterrows()],
             "numbers": [{"label": "Hashtags", "you": "not used", "competitor": listing, "typical": None}],
             "technical": [f"Mann-Whitney tests, smallest {_p(min(cand_p.values()))}: none significant after correcting for "
                           f"{len(cand_p)} hashtags (a proven gap needs p below {P_SHOWN})."]}))
        info["hashtag_worth_testing"] = 1
    # your own best hashtags
    mine = {}
    for tag in set().union(*up_tags) if len(up_tags) else set():
        mask = up_tags.map(lambda s, tag=tag: tag in s)
        p = pr.group_p(up, mask, "greater")
        if p is not None:
            mine[tag] = p
    for tag in sorted(bh_accept(mine), key=lambda t: mine[t])[:TOP_TAGS]:
        mask = up_tags.map(lambda s, tag=tag: tag in s)
        strengths.append({"kind": "hashtag", "label": f"Posts with {tag}",
                          "detail": f"They get about {up.loc[mask, 'results'].median():,.0f} likes and comments, against {up.loc[~mask, 'results'].median():,.0f} for your other posts."})
    return gaps, strengths, info
