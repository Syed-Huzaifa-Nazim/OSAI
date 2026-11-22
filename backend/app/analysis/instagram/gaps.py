"""
gaps.py -- finds the gaps between the user's account and a competitor's account.

How it works (simple version):
  1. The trained model grades both accounts (bad / average / good).
  2. SHAP tells, for each account, how much EACH habit pushed its score
     up (+) or down (-).   Score = the model's chance that the account is "good".
  3. A habit is a GAP when it helps the competitor MORE than it helps the user.
       gap size = competitor's SHAP  -  user's SHAP
  4. Gaps are ranked by size. Only habits the owner can change are checked.

Nothing here is hard-coded as "more posts = better". The direction
(higher or lower is better) comes from what the model learned.
"""
import numpy as np
import pandas as pd
import shap

from .features import FEATURE_COLUMNS

# Habits the owner can actually change. (Followers, total posts, verified badge
# and category are not quick habits, so they are not reported as gaps.)
ACTIONABLE = {
    "feat_posts_per_week": "Posting frequency (posts per week)",
    "feat_gap_std_days": "Posting consistency (variation between posts, in days)",
    "feat_days_since_last_post": "Recency (days since last post)",
    "feat_avg_caption_length": "Caption length (characters)",
    "feat_avg_hashtags": "Hashtags per post",
    "feat_pct_posts_with_hashtags": "Share of posts that use hashtags",
    "feat_pct_captions_with_cta": "Share of captions with a call to action",
    "feat_pct_captions_with_question": "Share of captions that ask a question",
    "feat_bio_length": "Bio length (characters)",
    "feat_bio_has_cta": "Call to action in the bio",
    "feat_has_website": "Website link in the profile",
    "feat_highlights_count": "Story highlights",
}

MIN_GAP = 0.01      # ignore differences smaller than 1 percentage point of "good" chance
TOP_K = 5           # how many gaps to show
CLEAR_DIFF = 0.10   # competitor must be at least 10 points more likely to be 'good'

_explainer_cache = {}


def _explainer(model):
    if id(model) not in _explainer_cache:
        _explainer_cache[id(model)] = shap.TreeExplainer(model)
    return _explainer_cache[id(model)]


def _shap_for_good(model, row):
    """SHAP values of one account for the class 'good' -> Series indexed by feature."""
    ex = _explainer(model)
    sv = np.array(ex.shap_values(row[FEATURE_COLUMNS]))        # (1, features, classes)
    good = list(model.classes_).index("good")
    return pd.Series(sv[0, :, good], index=FEATURE_COLUMNS), float(np.array(ex.expected_value)[good])


def grade_account(model, row):
    p = model.predict_proba(row[FEATURE_COLUMNS])[0]
    best = int(np.argmax(p))
    return {"grade": str(model.classes_[best]),
            "confidence": float(p[best]),
            "probabilities": {str(c): float(x) for c, x in zip(model.classes_, p)}}


# Names for the features that are not habits (shown, never reported as gaps).
OTHER_LABELS = {
    "feat_followers": "Followers",
    "feat_following": "Following",
    "feat_total_posts": "Total posts",
    "feat_follow_ratio": "Followers per following",
    "feat_is_verified": "Verified badge",
}


def feature_label(feat):
    if feat in ACTIONABLE:
        return ACTIONABLE[feat]
    if feat in OTHER_LABELS:
        return OTHER_LABELS[feat]
    if feat.startswith("feat_cat_"):
        return "Category: " + feat.replace("feat_cat_", "").replace("_", " ")
    return feat


def drivers(model, row, top_k=5):
    """What moved this account's chance of 'good', habit by habit (TreeSHAP).

    Returns the starting point (the average account's chance of 'good') and the
    top_k features with the largest push up or down, in probability points.
    Starting point + all pushes = the model's chance of 'good' for this account.
    """
    sv, base = _shap_for_good(model, row)
    top = sv.abs().sort_values(ascending=False).index[:top_k]
    return {
        "base_good_chance": base,
        "items": [
            {
                "feature": feat,
                "label": feature_label(feat),
                "value": None if pd.isna(row[feat].iloc[0]) else float(row[feat].iloc[0]),
                "shap": float(sv[feat]),
                "actionable": feat in ACTIONABLE,
            }
            for feat in top
        ],
    }


def find_gaps(model, user_row, comp_row, top_k=TOP_K, min_gap=MIN_GAP):
    """user_row / comp_row: one-row DataFrames from features.account_features()."""
    sv_u, _ = _shap_for_good(model, user_row)
    sv_c, _ = _shap_for_good(model, comp_row)

    gaps = []
    for feat, label in ACTIONABLE.items():
        u_val, c_val = user_row[feat].iloc[0], comp_row[feat].iloc[0]
        if pd.isna(u_val) or pd.isna(c_val):
            continue                                   # could not be measured for one of them
        size = sv_c[feat] - sv_u[feat]
        if size < min_gap:
            continue
        gaps.append({
            "feature": feat,
            "label": label,
            "user_value": float(u_val),
            "competitor_value": float(c_val),
            "user_shap": float(sv_u[feat]),            # + helps the user, - hurts the user
            "competitor_shap": float(sv_c[feat]),
            "gap_size": float(size),                   # how much more it helps the competitor
            "kind": "hurts you" if sv_u[feat] < 0 else "helps you less",
        })
    gaps.sort(key=lambda g: g["gap_size"], reverse=True)

    user_g, comp_g = grade_account(model, user_row), grade_account(model, comp_row)
    diff = comp_g["probabilities"]["good"] - user_g["probabilities"]["good"]
    return {
        "user": user_g,
        "competitor": comp_g,
        # how much more likely the competitor is to be "good" than the user.
        # If this is small, the two accounts are close and gaps are weak evidence.
        "good_chance_difference": diff,
        "clear_difference": bool(diff >= CLEAR_DIFF),
        "gaps": gaps[:top_k],
    }
