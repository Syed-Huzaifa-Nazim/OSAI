"""
features.py -- turns ONE scraped Instagram account into ONE row of numbers.

Used for BOTH training and the live system, so the model always gets the
same kind of numbers it was trained on.

Input names follow your database:
  account : dict / row from  instagram_accounts
            (biography, followers_count, follows_count, posts_count,
             is_verified, website, highlights_count, category, last_scraped_at)
  posts   : DataFrame from   instagram_posts
            (caption, posted_at)   -- likes/comments are NOT used as inputs
"""
import re
import numpy as np
import pandas as pd

LATEST_N = 12      # the model was trained on ~12 latest posts per account

CTA_WORDS = re.compile(
    r"\b(link in bio|dm us|dm me|shop now|order now|order today|book now|call us|"
    r"contact us|sign up|subscribe|follow us|click|visit|buy now|use code|discount|"
    r"swipe up|tag a friend|comment below|whatsapp|learn more|join)\b", re.I)
HASHTAG = re.compile(r"#\w+")

# the 5 business categories the model learned (everything else = "other")
KNOWN_CATEGORIES = [
    "Creators & Celebrities",
    "General Interest",
    "Lifestyle Services",
    "Personal Goods & General Merchandise Stores",
    "Professional Services",
]

# the exact inputs (and order) the model is trained on
FEATURE_COLUMNS = [
    "feat_followers", "feat_following", "feat_total_posts", "feat_follow_ratio",
    "feat_is_verified", "feat_has_website", "feat_bio_length", "feat_bio_has_cta",
    "feat_highlights_count", "feat_posts_per_week", "feat_gap_std_days",
    "feat_days_since_last_post", "feat_avg_caption_length", "feat_avg_hashtags",
    "feat_pct_posts_with_hashtags", "feat_pct_captions_with_cta",
    "feat_pct_captions_with_question",
] + [f"feat_cat_{c}" for c in KNOWN_CATEGORIES] + ["feat_cat_other"]


def _is_filled(x):
    return x is not None and not (isinstance(x, float) and np.isnan(x)) and str(x).strip() != ""


def account_features(account, posts, ref_date=None):
    """Returns a one-row DataFrame with FEATURE_COLUMNS."""
    d = posts.copy()

    # ---- dates: bad/placeholder dates (before 2010, e.g. 1970) count as missing
    when = pd.to_datetime(d["posted_at"], errors="coerce", utc=True)
    when = when.where(when.dt.year >= 2010)
    d["when"] = when

    # ---- keep the latest posts only (same as training)
    d = d.sort_values("when", ascending=False, na_position="last", kind="stable").head(LATEST_N)
    if len(d) < 3:
        raise ValueError("Need at least 3 posts to analyze an account.")

    if ref_date is None:
        ref_date = account.get("last_scraped_at") or pd.Timestamp.now(tz="UTC")
    ref_date = pd.to_datetime(ref_date, utc=True)

    # missing counts become NaN instead of crashing
    followers = pd.to_numeric(account.get("followers_count"), errors="coerce")
    following = pd.to_numeric(account.get("follows_count"), errors="coerce")
    total_posts = pd.to_numeric(account.get("posts_count"), errors="coerce")
    bio = account.get("biography")
    bio = "" if bio is None or (isinstance(bio, float) and np.isnan(bio)) else str(bio)

    row = {
        "feat_followers": followers,
        "feat_following": following,
        "feat_total_posts": total_posts,
        "feat_follow_ratio": followers / max(following, 1) if pd.notna(following) else np.nan,
        "feat_is_verified": int(account.get("is_verified") is True or str(account.get("is_verified")).lower() == "true"),
        "feat_has_website": int(_is_filled(account.get("website"))),
        "feat_bio_length": len(bio),
        "feat_bio_has_cta": int(bool(CTA_WORDS.search(bio))),
        "feat_highlights_count": pd.to_numeric(account.get("highlights_count"), errors="coerce"),
    }

    # ---- business category -> one yes/no column per known category
    cat = account.get("category")
    cat = str(cat).replace("&amp;", "&").strip().lower() if _is_filled(cat) else ""
    matched = next((k for k in KNOWN_CATEGORIES if k.lower() == cat), None)
    for k in KNOWN_CATEGORIES:
        row[f"feat_cat_{k}"] = int(k == matched)
    row["feat_cat_other"] = int(matched is None)

    # ---- posting rhythm (needs at least 3 real dates)
    dts = d["when"].dropna().sort_values()
    if len(dts) >= 3:
        span_days = (dts.max() - dts.min()).total_seconds() / 86400
        gaps = dts.diff().dropna().dt.total_seconds() / 86400
        row["feat_posts_per_week"] = (len(dts) - 1) / (span_days / 7) if span_days >= 1 else np.nan
        row["feat_gap_std_days"] = gaps.std()
        row["feat_days_since_last_post"] = (ref_date - dts.max()).total_seconds() / 86400
    else:
        row["feat_posts_per_week"] = np.nan
        row["feat_gap_std_days"] = np.nan
        row["feat_days_since_last_post"] = np.nan

    # ---- what the captions look like
    caps = d["caption"].fillna("").astype(str)
    tag_counts = caps.apply(lambda t: len(HASHTAG.findall(t)))
    row["feat_avg_caption_length"] = caps.str.len().mean()
    row["feat_avg_hashtags"] = tag_counts.mean()
    row["feat_pct_posts_with_hashtags"] = (tag_counts > 0).mean()
    row["feat_pct_captions_with_cta"] = caps.apply(lambda t: bool(CTA_WORDS.search(t))).mean()
    row["feat_pct_captions_with_question"] = caps.str.contains(r"\?").mean()

    return pd.DataFrame([row])[FEATURE_COLUMNS]