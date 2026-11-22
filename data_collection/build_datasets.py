"""Builds the measured datasets from data/posts.csv and data/profiles.csv.

  ../backend/.venv/bin/python build_datasets.py

Writes:
  datasets/posts_dataset.csv      one row per post: features + measured labels (engagement %, lift)
  datasets/accounts_dataset.csv   one row per shop: habits + measured engagement %
  datasets/hashtags_dataset.csv   one row per hashtag: how often used, lift of posts that use it
  datasets/OptiStratix_jewellery_datasets.xlsx   the same three, one sheet each, plus a README sheet

Every label is MEASURED from Instagram's own counts; the "source" columns say so. Caption features are simple text
checks (marked as such); model-made labels (content type, picture tags) are added later by their own scripts.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA, OUT = HERE / "data", HERE / "datasets"
TZ = "Asia/Karachi"

PRICE = re.compile(r"(?:\brs\.?\s?\d|\bpkr\s?\d|\d[\d,]*\s?(?:rs|pkr|/-)\b|price\s*[:\-]?\s*\d)", re.I)
ORDER = re.compile(r"\b(?:dm|inbox|whats\s?app|watsapp|wa\.me|order|call|book now|link in bio|cod|cash on delivery)\b", re.I)
PHONE = re.compile(r"(?:\+?92|0)3\d{2}[\s-]?\d{7}")
OFFER = re.compile(r"\b(?:sale|off|discount|offer|deal|free delivery|flat \d+)\b", re.I)
URDU_SCRIPT = re.compile(r"[؀-ۿ]")
ROMAN_URDU = re.compile(r"\b(?:hai|hain|kar|karein|karen|ke|ki|ka|aur|liye|abhi|mein|apna|apni|sirf|bohat|bht|jaldi|khareedain)\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
SLOTS = {"morning": (5, 12), "afternoon": (12, 17), "evening": (17, 21), "night": (21, 5)}
FORMATS = {"image": "photo", "sidecar": "carousel", "video": "reel"}


def _slot(h: int) -> str:
    for name, (a, b) in SLOTS.items():
        if (a <= h < b) if a < b else (h >= a or h < b):
            return name
    return "night"


def _language(text: str) -> str:
    if URDU_SCRIPT.search(text):
        return "urdu_script"
    if len(ROMAN_URDU.findall(text)) >= 2:
        return "roman_urdu"
    return "english" if re.search(r"[a-zA-Z]{3,}", text) else "none"


def posts_dataset(scraped_at: pd.Timestamp) -> pd.DataFrame:
    p = pd.read_csv(DATA / "posts.csv")
    d = pd.DataFrame({"handle": p["handle"], "shortcode": p["post_url"].str.rstrip("/").str.split("/").str[-1],
                      "post_url": p["post_url"]})
    when = pd.to_datetime(p["posted_at"], utc=True, errors="coerce")
    local = when.dt.tz_convert(TZ)
    d["posted_at"] = p["posted_at"]
    d["format"] = p["media_type"].str.lower().map(FORMATS).fillna("other")
    d["slides"] = p["media_count"]
    d["hour_pk"], d["part_of_day"] = local.dt.hour, local.dt.hour.map(_slot)
    d["weekend"] = local.dt.day_of_week >= 5
    d["age_days"] = ((scraped_at - when).dt.total_seconds() / 86400).round(2)
    cap = p["caption"].fillna("").astype(str)
    d["caption_chars"], d["caption_words"] = cap.str.len(), cap.str.split().str.len().fillna(0).astype(int)
    d["first_line_chars"] = cap.str.split("\n").str[0].str.len()
    d["emoji_count"] = cap.map(lambda t: len(EMOJI.findall(t)))
    d["has_question"] = cap.str.contains(r"\?")
    d["price_in_caption"] = cap.str.contains(PRICE)
    d["order_cta_in_caption"] = cap.str.contains(ORDER)
    d["phone_in_caption"] = cap.str.contains(PHONE)
    d["offer_words_in_caption"] = cap.str.contains(OFFER)
    d["caption_language"] = cap.map(_language)
    d["hashtag_count"] = p["hashtag_count"].fillna(0).astype(int)
    d["hashtags"] = p["hashtags"].fillna("")
    d["is_collab"] = p["owner_username"].fillna("").str.lower() != p["handle"].str.lower()
    d["caption"] = cap
    d["caption_features_source"] = "text_rules"
    # ---- measured labels
    likes = pd.to_numeric(p["likes"], errors="coerce")
    likes = likes.where(likes >= 0)                                     # negative = likes hidden by the shop
    comments = pd.to_numeric(p["comments"], errors="coerce").fillna(0).clip(lower=0)
    d["followers"], d["likes"], d["comments"] = p["followers"], likes, comments
    d["views"] = pd.to_numeric(p["views"], errors="coerce")
    d["engagement_pct"] = ((likes + comments) / p["followers"] * 100).round(4)
    d["views_per_follower"] = (d["views"] / p["followers"]).round(4)
    usual = d.groupby("handle")["engagement_pct"].transform("median")
    d["lift"] = (d["engagement_pct"] / usual).round(4)                  # 1.0 = the shop's usual post
    # Posts under a day old are still collecting likes (their median lift is far below 1 in this data): kept in the
    # file, flagged, and left out of training.
    d["young_post"] = d["age_days"] < 1
    d["label_source"] = "measured"
    return d


def accounts_dataset(posts: pd.DataFrame) -> pd.DataFrame:
    prof = pd.read_csv(DATA / "profiles.csv")
    prof = prof[prof["handle"].isin(posts["handle"])]
    g = posts.groupby("handle")
    when = pd.to_datetime(posts["posted_at"], utc=True, errors="coerce")
    span_days = when.groupby(posts["handle"]).agg(lambda s: (s.max() - s.min()).total_seconds() / 86400)
    acc = pd.DataFrame({
        "posts_read": g.size(),
        "engagement_pct_mean": g["engagement_pct"].mean().round(4),
        "engagement_pct_median": g["engagement_pct"].median().round(4),
        "posts_per_week": ((g.size() - 1) / (span_days / 7)).round(2),
        "share_reels": g["format"].apply(lambda s: (s == "reel").mean()).round(3),
        "share_carousels": g["format"].apply(lambda s: (s == "carousel").mean()).round(3),
        "share_photos": g["format"].apply(lambda s: (s == "photo").mean()).round(3),
        "avg_hashtags": g["hashtag_count"].mean().round(2),
        "share_price_in_caption": g["price_in_caption"].mean().round(3),
        "share_order_cta": g["order_cta_in_caption"].mean().round(3),
        "share_offer_words": g["offer_words_in_caption"].mean().round(3),
        "avg_caption_words": g["caption_words"].mean().round(1),
        "reel_views_per_follower_median": g["views_per_follower"].median().round(4),
    }).reset_index()
    acc = prof[["handle", "full_name", "followers", "following", "posts_total", "highlights", "external_url", "category"]].merge(acc, on="handle")
    acc["has_link_in_bio"] = acc["external_url"].notna()
    acc["label_source"] = "measured"
    return acc


def hashtags_dataset(posts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in posts.iterrows():
        for tag in str(r["hashtags"]).split():
            rows.append({"hashtag": tag.lower().lstrip("#"), "handle": r["handle"], "lift": r["lift"]})
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    agg = t.groupby("hashtag").agg(uses=("lift", "size"), shops=("handle", "nunique"), median_lift=("lift", "median")).reset_index()
    return agg.sort_values(["shops", "uses"], ascending=False)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    raw = sorted((DATA / "raw").glob("posts_*.json"))
    scraped_at = pd.Timestamp(raw[-1].stem.split("_")[-1], tz="UTC") if raw else pd.Timestamp.now(tz="UTC")
    posts = posts_dataset(scraped_at)
    # Very new posts are still collecting likes. Show, from the data itself, how lift grows with age.
    bins = pd.cut(posts["age_days"], [0, 1, 2, 3, 7, 30, 10_000], right=False)
    print("Median lift by post age (days):")
    print(posts.groupby(bins, observed=True)["lift"].agg(["count", "median"]).round(2).to_string())
    accounts = accounts_dataset(posts)
    tags = hashtags_dataset(posts)
    posts.to_csv(OUT / "posts_dataset.csv", index=False)
    accounts.to_csv(OUT / "accounts_dataset.csv", index=False)
    tags.to_csv(OUT / "hashtags_dataset.csv", index=False)
    readme = pd.DataFrame({"sheet": ["posts", "accounts", "hashtags"], "rows": [len(posts), len(accounts), len(tags)], "what": [
        "one row per post. Labels: engagement_pct = (likes + comments) / followers x 100; lift = engagement_pct / the shop's median post (1.0 = usual). Measured.",
        "one row per shop: profile facts and habits from its 30 posts; engagement_pct_mean/median measured.",
        "one row per hashtag: uses, number of shops using it, median lift of posts with it. Measured.",
    ]})
    with pd.ExcelWriter(OUT / "OptiStratix_jewellery_datasets.xlsx") as xl:
        readme.to_excel(xl, sheet_name="README", index=False)
        posts.to_excel(xl, sheet_name="posts", index=False)
        accounts.to_excel(xl, sheet_name="accounts", index=False)
        tags.to_excel(xl, sheet_name="hashtags", index=False)
    print(f"posts: {len(posts)} rows · accounts: {len(accounts)} · hashtags: {len(tags)}")
    print(accounts[["handle", "followers", "engagement_pct_median", "posts_per_week", "share_reels"]].to_string(index=False))


if __name__ == "__main__":
    main()
