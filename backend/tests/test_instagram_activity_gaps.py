"""Layer 5: posting time, how often each account posts, and how far its reels reach."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from app.analysis.instagram import activity_gaps, post_results as pr
from app.analysis.instagram.gap_common import Pair

TZ = "Asia/Karachi"          # UTC+5
START = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _frame(rows: list[dict]) -> pd.DataFrame:
    d = pd.DataFrame([{
        "id": f"p{i}", "source_id": f"s{i}", "caption": "New arrivals", "post_url": f"https://instagram.com/p/x{i}/",
        "media_url": f"https://cdn.test/{i}.jpg", "comments_count": 2, **r} for i, r in enumerate(rows)])
    return pr.prepare(d)


def _posts(n: int, every_days: float, hour_utc, likes, media_type="image", views=None) -> pd.DataFrame:
    rows = []
    for i in range(n):
        when = START + timedelta(days=i * every_days, hours=hour_utc(i) if callable(hour_utc) else hour_utc)
        rows.append({"posted_at": when.isoformat(), "media_type": media_type, "likes_count": likes(i) if callable(likes) else likes,
                     "views": views(i) if callable(views) else views})
    return _frame(rows)


def _pair(followers_u=2000, followers_c=2000) -> Pair:
    acc = lambda name, f: {"username": name, "profile_url": f"https://instagram.com/{name}/", "followers_count": f}  # noqa: E731
    return Pair(project_id="p1", me="me", who="rival", ua=acc("me", followers_u), ca=acc("rival", followers_c),
                context="behind", few=False)


def _kinds(gaps):
    return [(g["details"]["kind"], g["details"].get("unproven", False), g["title"]) for g in gaps]


def test_their_evening_posts_do_better_and_you_never_post_then():
    # 14:00 UTC = 7 pm Pakistan (evening); 05:00 UTC = 10 am (morning). Their evening posts get 5x the likes.
    rival = _posts(30, 1, lambda i: 14 if i % 2 else 5, lambda i: 500 if i % 2 else 100)
    me = _posts(30, 1, 5, 100)
    gaps, info = activity_gaps.analyze(_pair(), me, rival, TZ)
    timing = [g for g in gaps if g["details"]["kind"] == "timing" and not g["details"].get("unproven")]
    assert timing, _kinds(gaps)
    assert "in the evening (5 pm to 9 pm)" in timing[0]["title"]
    assert "Pakistan time" in timing[0]["description"]
    assert timing[0]["details"]["numbers"][0] == {"label": "Recent posts made in the evening (5 pm to 9 pm)",
                                                 "you": "0 of 30", "competitor": "15 of 30", "typical": None}
    assert info["time_gaps"] >= 1


def test_no_time_gap_when_you_already_post_at_that_time():
    rival = _posts(30, 1, lambda i: 14 if i % 2 else 5, lambda i: 500 if i % 2 else 100)
    me = _posts(30, 1, 14, 100)                       # you post every evening already
    gaps, _ = activity_gaps.analyze(_pair(), me, rival, TZ)
    assert not [g for g in gaps if "evening" in g["title"]]


def test_posting_more_often_is_only_ever_worth_testing():
    rival = _posts(30, 1, 5, 100)                    # every day
    me = _posts(30, 7, 5, 100)                       # once a week
    gaps, info = activity_gaps.analyze(_pair(), me, rival, TZ)
    freq = [g for g in gaps if "post more often" in g["title"]]
    assert len(freq) == 1
    assert freq[0]["details"]["unproven"] is True and freq[0]["details"]["howSure"] == "Low"
    assert "post more often usually get fewer likes" in freq[0]["description"]
    assert info["frequency"]["competitor_per_week"] == 7.0 and info["frequency"]["user_per_week"] == 1.0


def test_no_frequency_gap_when_you_post_as_often():
    rival = _posts(30, 1, 5, 100)
    me = _posts(30, 1, 5, 100)
    gaps, _ = activity_gaps.analyze(_pair(), me, rival, TZ)
    assert not [g for g in gaps if "post more often" in g["title"]]


def test_reels_that_reach_more_people_per_follower():
    rival = _posts(30, 1, 5, 100, media_type="video", views=lambda i: 6000 + i * 10)   # ~3 views per follower
    me = _posts(30, 1, 5, 100, media_type="video", views=lambda i: 900 + i * 10)       # ~0.5 views per follower
    gaps, info = activity_gaps.analyze(_pair(2000, 2000), me, rival, TZ)
    reach = [g for g in gaps if g["details"]["kind"] == "reach"]
    assert len(reach) == 1 and info["reach"]["gap"] is True
    assert reach[0]["details"]["numbers"][0]["label"] == "Views for every 100 followers, typical reel"


def test_a_bigger_account_does_not_win_reach_just_for_being_bigger():
    # They get 5x the views but have 5x the followers: the same views per follower, so no gap.
    rival = _posts(30, 1, 5, 100, media_type="video", views=lambda i: 5000 + i * 50)
    me = _posts(30, 1, 5, 100, media_type="video", views=lambda i: 1000 + i * 10)
    gaps, _ = activity_gaps.analyze(_pair(1000, 5000), me, rival, TZ)
    assert not [g for g in gaps if g["details"]["kind"] == "reach"]


def test_too_few_dated_posts_skips_the_layer():
    gaps, info = activity_gaps.analyze(_pair(), _posts(2, 1, 5, 100), _posts(2, 1, 5, 100), TZ)
    assert gaps == [] and info["status"] == "skipped"
