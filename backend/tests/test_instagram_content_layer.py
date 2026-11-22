"""Layer 6: caption type, picture tags and reel openings (the measuring models are replaced by ready columns)."""

from __future__ import annotations

import pandas as pd
import pytest

from app.analysis.instagram import content_layer as cl, post_results as pr
from app.analysis.instagram.gap_common import Pair

EVIDENCE = {"traits": {
    "face": {"measure": "likes and comments", "verdict": "helps (proven)", "effect_x": 1.37, "shops_tested": 27, "shops_where_better": 20},
    "reel_face": {"measure": "views", "verdict": "helps (proven)", "effect_x": 1.74, "shops_tested": 22, "shops_where_better": 20},
    "price": {"measure": "likes and comments", "verdict": "too few shops to test", "effect_x": None, "shops_tested": 4},
}}


@pytest.fixture(autouse=True)
def _evidence(monkeypatch):
    monkeypatch.setitem(cl._cache, "evidence", EVIDENCE)
    monkeypatch.setattr(cl, "status", lambda: {"captions": {"available": True}, "pictures": {"available": True},
                                               "reels": {"available": True}})


def _frame(n: int, media_type: str, likes, **cols) -> pd.DataFrame:
    d = pd.DataFrame([{"id": f"p{i}", "source_id": f"s{i}", "caption": "x", "posted_at": f"2026-09-{i % 28 + 1:02d}T10:00:00Z",
                       "post_url": f"https://instagram.com/p/x{i}/", "media_url": f"https://cdn.test/{i}.jpg", "media_type": media_type,
                       "likes_count": likes(i) if callable(likes) else likes, "comments_count": 0} for i in range(n)])
    d = pr.prepare(d)
    for c, v in cols.items():
        d[c] = [v(i) if callable(v) else v for i in range(n)]
    return d


def _pair() -> Pair:
    acc = lambda name: {"username": name, "profile_url": f"https://instagram.com/{name}/", "followers_count": 5000}  # noqa: E731
    return Pair(project_id="p1", me="me", who="rival", ua=acc("me"), ca=acc("rival"), context="behind", few=False)


def _run(up, cp):
    return cl.analyze(_pair(), up, cp, {}, {})


def test_face_gap_when_they_show_faces_and_it_is_proven_across_shops():
    rival = _frame(30, "image", lambda i: 100, face=lambda i: i % 3 != 0)        # 20 of 30 with a face
    me = _frame(30, "image", 100, face=False)
    gaps, info = _run(me, rival)
    face = [g for g in gaps if g["details"]["kind"] == "picture"]
    assert len(face) == 1 and not face[0]["details"].get("unproven")
    assert face[0]["title"].startswith("Show a person") and "about 40% more likes and comments" in face[0]["description"]
    assert "20 of their last 30 posts" in face[0]["description"] and "none of your last 30 posts" in face[0]["description"]


def test_no_gap_when_you_already_do_it_as_often():
    rival = _frame(30, "image", 100, face=lambda i: i % 2 == 0)
    me = _frame(30, "image", 100, face=lambda i: i % 2 == 0)
    gaps, _ = _run(me, rival)
    assert not [g for g in gaps if g["details"]["kind"] == "picture"]


def test_caption_trait_that_works_for_them_is_a_gap():
    # their 15 captions with a price get 5x the likes; you never write the price; no cross-shop evidence
    rival = _frame(30, "image", lambda i: 500 if i < 15 else 100, cap_price=lambda i: i < 15)
    me = _frame(30, "image", 100, cap_price=False)
    gaps, _ = _run(me, rival)
    cap = [g for g in gaps if g["details"]["kind"] == "caption"]
    assert len(cap) == 1 and not cap[0]["details"].get("unproven") and "price" in cap[0]["title"]


def test_a_small_difference_is_not_shown():
    # they write prices a bit more often than you (10 vs 5 of 30), slightly better results: could be chance, not shown
    rival = _frame(30, "image", lambda i: 120 if i % 3 == 0 else 100, cap_price=lambda i: i % 3 == 0)
    me = _frame(30, "image", 100, cap_price=lambda i: i % 6 == 0)
    gaps, _ = _run(me, rival)
    assert not [g for g in gaps if g["details"]["kind"] == "caption"]


def test_reel_opening_uses_reels_only():
    rival = pd.concat([_frame(20, "video", 300, face_in_first_3s=lambda i: i < 14), _frame(10, "image", 100)], ignore_index=True)
    me = pd.concat([_frame(20, "video", 300, face_in_first_3s=False), _frame(10, "image", 100)], ignore_index=True)
    gaps, _ = _run(me, rival)
    reel = [g for g in gaps if g["details"]["kind"] == "reel"]
    assert len(reel) == 1 and "14 of their last 20 reels" in reel[0]["description"] and reel[0]["title"].startswith("Start reels with a person")


def test_numeric_reel_traits_compare_with_the_competitor_usual():
    cuts = lambda i: 4.0 if i < 10 else 1.0                                     # noqa: E731
    rival = _frame(20, "video", lambda i: 600 if i < 10 else 100, cuts_per_10s=cuts, duration_s=20.0)
    me = _frame(20, "video", 100, cuts_per_10s=0.5, duration_s=20.0)
    gaps, _ = _run(me, rival)
    assert any("shorter shots" in g["title"] or "editing" in g["title"] for g in gaps)


def test_layer_is_skipped_without_models(monkeypatch):
    monkeypatch.setattr(cl, "status", lambda: {"captions": {"available": False}, "pictures": {"available": False},
                                               "reels": {"available": False}})
    gaps, info = _run(_frame(10, "image", 100), _frame(10, "image", 100))
    assert gaps == [] and info["status"] == "not_available"


def test_market_gap_when_you_are_below_the_typical_jewellery_shop_even_if_the_competitor_is_weaker(monkeypatch):
    monkeypatch.setitem(cl._cache, "evidence", {**EVIDENCE, "typical": {"face": {"typical_share": 0.2, "shops": 82}}})
    rival = _frame(30, "image", 100, face=False)                                 # the competitor never shows a face
    me = _frame(30, "image", 100, face=lambda i: i == 0)                         # you: 1 of 30, below 20%
    gaps, info = _run(me, rival)
    market = [g for g in gaps if g["details"].get("market")]
    assert len(market) == 1 and market[0]["title"] == "Show a person with your jewellery"
    assert "1 of your last 30 posts" in market[0]["description"]
    assert info["market_gaps"] == 1


def test_strengths_and_full_comparison_are_reported(monkeypatch):
    monkeypatch.setitem(cl._cache, "evidence", {**EVIDENCE, "typical": {"face": {"typical_share": 0.05, "shops": 82}}})
    rival = _frame(30, "image", 100, face=False)
    me = _frame(30, "image", 100, face=lambda i: i < 15)                         # you show faces, they do not
    gaps, info = _run(me, rival)
    assert not [g for g in gaps if g["details"]["kind"] == "picture"]
    assert any("you already do this" in s["label"] for s in info["strengths"])
    row = next(r for r in info["comparison"] if r["key"] == "face")
    assert row["group"] == "doing_well" and row["you_text"] == "15 of your last 30 posts"
    assert row["competitor_text"] == "None of their last 30 posts" and "40% more" in row["why"]
