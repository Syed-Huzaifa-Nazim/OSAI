"""
content_gaps.py -- content gaps found by simple comparison (no trained model).

Step 1 of the content gaps:
  - MEDIA MIX : which formats (photo / video / carousel) the competitor uses much more
  - TREND     : whether the competitor's recent posts do better than its older
                posts, while the user's do not

Input names follow your database:
  account : dict with followers_count
  posts   : DataFrame from instagram_posts
            (media_type, likes_count, comments_count, posted_at)

Output gaps use the same fields as gaps.py, so the frontend and the Explain
button can treat both kinds the same way.
"""
import pandas as pd

# Instagram's names -> plain names ("Sidecar" = a post with several photos/videos)
FORMAT_NAMES = {"image": "photo", "video": "video / reel", "sidecar": "carousel"}

MEDIA_DIFF = 0.25        # competitor must use a format at least 25 points more often
TREND_DIFF = 0.20        # competitor's trend must beat the user's by 20 points
MIN_POSTS_TREND = 6      # need at least 6 dated posts to see a trend


def media_mix(posts):
    """Share of posts per format, e.g. {'video / reel': 0.9, 'carousel': 0.1}."""
    kinds = (posts["media_type"].fillna("other").astype(str).str.lower()
             .map(lambda x: FORMAT_NAMES.get(x, "other")))
    return kinds.value_counts(normalize=True).to_dict()


def engagement_trend(posts, followers):
    """
    Change in engagement per follower: newer half of posts vs older half.
    +0.30 = recent posts do 30% better than older ones. None if not enough data.
    """
    if not followers or followers <= 0:
        return None
    d = posts.copy()
    d["when"] = pd.to_datetime(d["posted_at"], errors="coerce", utc=True)
    d = d[d["when"].dt.year >= 2010]                         # 1970 = placeholder date
    likes = pd.to_numeric(d["likes_count"], errors="coerce")
    likes = likes.where(likes >= 0)                          # negative = hidden likes
    comments = pd.to_numeric(d["comments_count"], errors="coerce").fillna(0)
    d["rate"] = (likes + comments) / followers
    d = d.dropna(subset=["when", "rate"]).sort_values("when")
    if len(d) < MIN_POSTS_TREND:
        return None
    half = len(d) // 2
    old, new = d["rate"].iloc[:half].mean(), d["rate"].iloc[half:].mean()
    return None if old <= 0 else float(new / old - 1)


def find_content_gaps(user_account, user_posts, comp_account, comp_posts):
    gaps = []

    # ---- media mix: formats the competitor uses much more than the user
    u_mix, c_mix = media_mix(user_posts), media_mix(comp_posts)
    for fmt in sorted(set(u_mix) | set(c_mix)):
        if fmt == "other":
            continue
        u, c = u_mix.get(fmt, 0.0), c_mix.get(fmt, 0.0)
        if c - u >= MEDIA_DIFF:
            gaps.append({
                "type": "content",
                "feature": f"media_{fmt}",
                "label": f"Use of {fmt} posts",
                "user_value": u,
                "competitor_value": c,
                "unit": "share of posts",
                "gap_size": c - u,
                "kind": "difference",      # not 'better/worse': it only shows what the competitor does more
            })

    # ---- trend: competitor's recent posts doing better, user's not
    u_t = engagement_trend(user_posts, user_account.get("followers_count"))
    c_t = engagement_trend(comp_posts, comp_account.get("followers_count"))
    if u_t is not None and c_t is not None and c_t > 0 and c_t - u_t >= TREND_DIFF:
        gaps.append({
            "type": "content",
            "feature": "engagement_trend",
            "label": "Engagement trend (recent posts vs older posts)",
            "user_value": u_t,
            "competitor_value": c_t,
            "unit": "change in engagement per follower",
            "gap_size": c_t - u_t,
            "kind": "competitor improving",
        })

    gaps.sort(key=lambda g: g["gap_size"], reverse=True)
    return gaps
