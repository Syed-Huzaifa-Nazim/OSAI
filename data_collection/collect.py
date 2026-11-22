"""Collects the jewellery-SME Instagram dataset with Apify, reusing the app's own scraper code (backend).

Two steps, so Apify credit is only spent on shops that qualify:

  python collect.py profiles   # step A: one cheap run reads every candidate's profile -> data/profiles.csv
  python collect.py posts      # step B: up to 30 posts of each shop that passes the SME rules -> data/posts.csv

Run with the backend's Python (it has apify-client and pandas):
  cd Development/data_collection && ../backend/.venv/bin/python collect.py profiles

SME rules (decided with the project owner):
  followers 1,000 to 100,000 · public · at least 30 posts · posted in the last 30 days.
Every raw Apify item is kept in data/raw/ so the dataset can be rebuilt and checked.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.scrapers.instagram import client, extract  # noqa: E402  (the app's own Apify + extraction code)
from app.scrapers.instagram import selectors as S  # noqa: E402

DATA, RAW = HERE / "data", HERE / "data" / "raw"
MIN_FOLLOWERS, MAX_FOLLOWERS = 1_000, 100_000     # nano + micro accounts: the SME range
MIN_POSTS = 30
ACTIVE_DAYS = 30
POSTS_PER_SHOP = 30


def _url(handle: str) -> str:
    return f"https://www.instagram.com/{handle.strip().strip('@').strip('/')}/"


def _save_raw(name: str, items: list) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    (RAW / f"{name}_{stamp}.json").write_text(json.dumps(items, ensure_ascii=False, default=str))


# Round 2 used: artificialjewellerypakistan, jewellerypakistan, pakistanijewelry, jewellerykarachi, jewellerylahore,
# bridaljewellerypakistan. Round 3: pakistanijewellery, jewelleryonlinepakistan, earringspakistan, banglespakistan,
# jewelleryislamabad, silverjewellerypakistan, goldplatedjewellerypakistan, kundanjewellerypakistan. Round 4:
HASHTAGS = ["jewellerypk", "jewelrypakistan", "jhumkapakistan", "necklacepakistan", "bridaljewellerykarachi",
            "artificialjewellerykarachi", "jewelleryrawalpindi", "jewelleryfaisalabad"]
DISCOVER_PER_TAG = 40
# Signs that a profile is a Pakistani seller: a .pk handle, a Pakistani city or country in the bio, or a Pakistani phone number.
PK_SIGNS = ("pakistan", "karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "multan", "peshawar", "hyderabad",
            "quetta", "sialkot", "gujranwala", "+92", "🇵🇰", "cod all over", "all over pakistan", "nationwide")
PK_PHONE = __import__("re").compile(r"(?:\+?92|\b0)3\d{2}[\s-]?\d{7}")
MIN_USUAL_INTERACTIONS = 10   # below this, a post's lift is mostly counting noise (relative noise > ~30%)


def discover() -> None:
    """Finds active shops from recent posts under Pakistani jewellery hashtags; adds new handles to candidates.csv."""
    urls = [f"https://www.instagram.com/explore/tags/{t}/" for t in HASHTAGS]
    print(f"Reading up to {DISCOVER_PER_TAG} recent posts under {len(urls)} hashtags ...")
    items = client._run_actor(client._client(), {"directUrls": urls, "resultsType": S.RESULTS_TYPE_MORE_POSTS,
                                                 "resultsLimit": DISCOVER_PER_TAG})
    _save_raw("discover", items)
    owners = pd.Series([(i.get("ownerUsername") or "").lower() for i in items if isinstance(i, dict)]).replace("", pd.NA).dropna()
    cands = pd.read_csv(HERE / "candidates.csv")
    known = set(cands["handle"].str.lower())
    new = sorted(set(owners) - known)
    pd.concat([cands, pd.DataFrame({"handle": new, "found_via": "hashtag posts", "note": ""})]).to_csv(HERE / "candidates.csv", index=False)
    print(f"Posts read: {len(items)} · different accounts: {owners.nunique()} · new candidates added: {len(new)}")


def profiles() -> None:
    cands = pd.read_csv(HERE / "candidates.csv")
    done = set(pd.read_csv(DATA / "profiles.csv")["handle"].str.lower()) if (DATA / "profiles.csv").exists() else set()
    cands = cands[~cands["handle"].str.lower().isin(done)]          # only profiles not checked before
    urls = [_url(h) for h in cands["handle"]]
    print(f"Reading {len(urls)} profiles in one Apify run ...")
    items = client._run_actor(client._client(), {"directUrls": urls, "resultsType": S.RESULTS_TYPE_POSTS, "resultsLimit": 1})
    _save_raw("profiles", items)
    now = datetime.now(timezone.utc)
    rows = []
    for item in items:
        if not isinstance(item, dict) or not item.get("username"):
            continue
        stats = extract.profile_stats([item])
        latest = [p.get("timestamp") for p in item.get("latestPosts") or [] if p.get("timestamp")]
        last_post = max(latest) if latest else None
        last_dt = pd.to_datetime(last_post, utc=True, errors="coerce") if last_post else None
        followers, n_posts = stats.get("followers_count"), stats.get("posts_count")
        reasons = []
        if item.get("private"):
            reasons.append("private")
        if followers is None or not (MIN_FOLLOWERS <= followers <= MAX_FOLLOWERS):
            reasons.append(f"followers {followers}")
        if n_posts is None or n_posts < MIN_POSTS:
            reasons.append(f"posts {n_posts}")
        if last_dt is None or pd.isna(last_dt) or last_dt < now - timedelta(days=ACTIVE_DAYS):
            reasons.append(f"last post {str(last_post)[:10] if last_post else 'unknown'}")
        bio = f"{item.get('username', '')} {stats.get('biography', '')} {stats.get('full_name', '')}".lower()
        pakistani = item["username"].lower().endswith(".pk") or any(s in bio for s in PK_SIGNS) or bool(PK_PHONE.search(bio))
        if not pakistani:
            reasons.append("no Pakistan sign in profile")
        # a shop, not a blogger, creator or personal page (from the account's own Instagram category and name)
        kind = f"{stats.get('category') or ''} {item['username']}".lower()
        if any(w in kind for w in ("blog", "vlog", "creator", "influencer", "public figure", "personal", "artist", "ugc", "digital")):
            reasons.append(f"not a shop ({stats.get('category') or item['username']})")
        # engagement check on the latest posts the profile run already returned (no extra cost)
        inter = [(p.get("likesCount") or 0) + (p.get("commentsCount") or 0) for p in item.get("latestPosts") or []
                 if isinstance(p.get("likesCount"), int) and p.get("likesCount") >= 0]
        usual = float(pd.Series(inter).median()) if inter else None
        if usual is None or usual < MIN_USUAL_INTERACTIONS:
            reasons.append(f"usual post gets {usual if usual is not None else 'unknown'} likes+comments")
        rows.append({
            "handle": item["username"], "full_name": stats.get("full_name"), "followers": followers,
            "following": stats.get("following_count"), "posts_total": n_posts, "is_verified": stats.get("is_verified"),
            "category": stats.get("category"), "external_url": stats.get("external_url"),
            "highlights": stats.get("highlights_count"), "biography": stats.get("biography"),
            "last_post": last_post, "pakistan_sign": pakistani, "usual_interactions_latest12": usual,
            "sme_pass": not reasons, "fail_reasons": "; ".join(reasons),
        })
    out = pd.DataFrame(rows)
    DATA.mkdir(exist_ok=True)
    if (DATA / "profiles.csv").exists():                              # keep earlier checks, add the new ones
        out = pd.concat([pd.read_csv(DATA / "profiles.csv"), out], ignore_index=True)
    out = out.sort_values(["sme_pass", "followers"], ascending=[False, False])
    out.to_csv(DATA / "profiles.csv", index=False)
    missing = sorted(set(h.strip("@") for h in cands["handle"]) - set(out["handle"]))
    print(f"Profiles read: {len(out)} · pass the SME rules: {int(out['sme_pass'].sum())}")
    if missing:
        print("Not returned by Apify (wrong handle, deleted or blocked):", ", ".join(missing))
    print(out[["handle", "followers", "posts_total", "last_post", "sme_pass", "fail_reasons"]].to_string(index=False))


EXCLUDED = {"noor.mood2", "shop.scarletpk", "ambreezajewellerystudio", "afreen__sadique_khan_official", "us_jewellery_s", "roseblooms.pk",
            "sufyaninchina", "nikah_mubarak786", "in_food_coma", "noorulhudakazmii", "wajeehashah_creations", "mehrusheikh.06",
            "kxmpakistan", "resin_hub16"}   # not a shop / not clearly a Pakistani jewellery shop


def posts(max_shops: int, per_shop: int = POSTS_PER_SHOP) -> None:
    prof = pd.read_csv(DATA / "profiles.csv")
    have = set(pd.read_csv(DATA / "posts.csv")["handle"].str.lower()) if (DATA / "posts.csv").exists() else set()
    shops = prof[prof["sme_pass"] & ~prof["handle"].str.lower().isin(have | EXCLUDED)].head(max_shops)
    urls = [_url(h) for h in shops["handle"]]
    print(f"Reading up to {per_shop} posts from {len(urls)} new SME shops in one Apify run ...")
    items = client._run_actor(client._client(), {"directUrls": urls, "resultsType": S.RESULTS_TYPE_MORE_POSTS,
                                                 "resultsLimit": per_shop})
    _save_raw("posts", items)
    followers = dict(zip(prof["handle"].str.lower(), prof["followers"]))
    rows = []
    for input_url, post in client.iter_posts(items):
        rec = extract.extract_post(input_url or "", post)
        if not rec:
            continue
        handle = (input_url or "").rstrip("/").split("/")[-1].lower() or (rec.get("owner_username") or "").lower()
        media = rec.get("media") or []
        rows.append({
            "handle": handle, "post_url": rec.get("post_url"), "posted_at": rec.get("posted_at"),
            "media_type": rec.get("media_type"), "media_count": rec.get("media_count"),
            "likes": rec.get("like_count"), "comments": rec.get("comment_count"), "views": rec.get("video_view_count"),
            "caption": rec.get("caption"), "hashtags": " ".join(rec.get("hashtags") or []), "hashtag_count": rec.get("hashtag_count"),
            "is_sponsored": rec.get("is_sponsored"), "owner_username": rec.get("owner_username"),
            "media_url": rec.get("media_url"), "thumbnail_url": (media[0].get("thumbnail_url") if media else None),
            "followers": followers.get(handle),
        })
    df = pd.DataFrame(rows).drop_duplicates(subset=["post_url"])
    per = df.groupby("handle").size()
    print(f"Posts read: {len(df)} from {per.size} shops · per shop: min {per.min()}, median {int(per.median())}, max {per.max()}")
    if (DATA / "posts.csv").exists():                                  # add to the posts already collected
        df = pd.concat([pd.read_csv(DATA / "posts.csv"), df], ignore_index=True).drop_duplicates(subset=["post_url"])
    df.to_csv(DATA / "posts.csv", index=False)
    print(f"posts.csv now has {len(df)} posts from {df['handle'].nunique()} shops")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    if step == "discover":
        discover()
    elif step == "profiles":
        profiles()
    elif step == "posts":
        posts(int(sys.argv[2]) if len(sys.argv) > 2 else 20, int(sys.argv[3]) if len(sys.argv) > 3 else POSTS_PER_SHOP)
    else:
        print(__doc__)
