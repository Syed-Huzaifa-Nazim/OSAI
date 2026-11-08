"""
comment_gaps.py -- comment-mood gaps.

Why an LLM (Gemini) and not a small sentiment model?
Your real comments mix emoji-only comments, French, English and Roman Urdu/Punjabi
("ini mehnat nal msa chalda hun..."). Small sentiment models fail on Roman Urdu.

Steps:
  1. Comments that are ONLY @mentions ("@name") are friend-tags, not opinions.
     They are counted separately and NOT scored.
  2. The remaining comments are labelled positive / negative / neutral by the LLM.
  3. If the competitor's share of positive comments is clearly higher than the
     user's (or the user has clearly more negative ones), it is a gap.

Input:  lists of comment texts (instagram_comments.comment_text) for each account.
        call_llm(prompt) -> str   (the same function used by explain_gap.py)
"""
import json
import re

TAG_ONLY = re.compile(r"(\s*@[\w.]+\s*)+")
BATCH = 40
MIN_SCORED = 20          # need at least 20 scorable comments per account
POSITIVE_DIFF = 0.15
NEGATIVE_DIFF = 0.15
LABELS = ("positive", "negative", "neutral")


def is_tag_only(text):
    return bool(TAG_ONLY.fullmatch(text or ""))


def _prompt(batch):
    numbered = "\n".join(f"{i + 1}. {c[:300]}" for i, c in enumerate(batch))
    return f"""Label the sentiment of each Instagram comment as exactly one of: positive, negative, neutral.
Comments may be in any language, including Roman Urdu/Punjabi/Hindi, French, English, or only emojis.
Emoji-only comments: judge by the emotion of the emoji (laughing/heart/clapping = positive, angry/disgust = negative).
Return ONLY a JSON list of {len(batch)} strings, in the same order as the comments. No other text.

{numbered}"""


def label_comments(comments, call_llm):
    """Returns a list of labels (or None where the answer was unusable), same length as comments."""
    out = []
    for start in range(0, len(comments), BATCH):
        batch = comments[start:start + BATCH]
        raw = call_llm(_prompt(batch))
        m = re.search(r"\[.*\]", raw, re.S)
        try:
            labels = json.loads(m.group(0)) if m else []
        except json.JSONDecodeError:
            labels = []
        labels = [str(x).strip().lower() for x in labels]
        if len(labels) != len(batch):             # LLM lost count -> do not guess
            labels = [None] * len(batch)
        out += [x if x in LABELS else None for x in labels]
    return out


def summarize(comments, call_llm):
    comments = [c for c in comments if c and str(c).strip()]
    tags = [c for c in comments if is_tag_only(c)]
    text = [c for c in comments if not is_tag_only(c)]
    labels = [x for x in label_comments(text, call_llm) if x is not None]
    n = len(labels)
    share = lambda k: (labels.count(k) / n) if n else None
    return {
        "n_comments": len(comments),
        "n_tag_only": len(tags),
        "tag_share": len(tags) / len(comments) if comments else None,   # info only, not a gap
        "n_scored": n,
        "positive": share("positive"),
        "negative": share("negative"),
        "neutral": share("neutral"),
    }


def find_comment_gaps(user_comments, comp_comments, call_llm):
    u, c = summarize(user_comments, call_llm), summarize(comp_comments, call_llm)
    result = {"user": u, "competitor": c, "gaps": [], "note": None}

    if u["n_scored"] < MIN_SCORED or c["n_scored"] < MIN_SCORED:
        result["note"] = (f"Not enough comments to judge (need {MIN_SCORED} scorable comments each; "
                          f"user has {u['n_scored']}, competitor has {c['n_scored']}).")
        return result

    if c["positive"] - u["positive"] >= POSITIVE_DIFF:
        result["gaps"].append({
            "type": "content", "feature": "comment_positive",
            "label": "Share of positive comments",
            "user_value": u["positive"], "competitor_value": c["positive"],
            "unit": "share of comments", "gap_size": c["positive"] - u["positive"],
            "kind": "competitor higher",
        })
    if u["negative"] - c["negative"] >= NEGATIVE_DIFF:
        result["gaps"].append({
            "type": "content", "feature": "comment_negative",
            "label": "Share of negative comments",
            "user_value": u["negative"], "competitor_value": c["negative"],
            "unit": "share of comments", "gap_size": u["negative"] - c["negative"],
            "kind": "user higher",
        })
    result["gaps"].sort(key=lambda g: g["gap_size"], reverse=True)
    return result
