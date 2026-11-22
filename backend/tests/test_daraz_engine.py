"""The Daraz Gap Engine keeps only concrete, proven, actionable gaps."""
from __future__ import annotations

import pytest

from app.analysis.daraz import engine

EVIDENCE = {
    "levers": {
        "image_count|rank": {"outcome": "search rank", "lever": "image_count", "kind": "number", "proven": True,
                             "direction": "more is better", "words_tested": 25, "words_positive": 19,
                             "median_rho": 0.21, "p_corrected": 0.004},
        "free_shipping|rank": {"outcome": "search rank", "lever": "free_shipping", "kind": "yesno", "proven": True,
                               "direction": "more is better", "words_tested": 24, "words_positive": 18,
                               "median_rho": 0.15, "p_corrected": 0.02},
        "variant_count|rank": {"outcome": "search rank", "lever": "variant_count", "kind": "number", "proven": False,
                               "direction": "more is better", "words_tested": 25, "words_positive": 13,
                               "median_rho": 0.01, "p_corrected": 0.8},
    },
    "benchmarks": {
        "kundan set": {"image_count": {"median": 7, "q1": 5, "q3": 9, "n": 20},
                       "variant_count": {"median": 4, "q1": 2, "q3": 6, "n": 20},
                       "free_shipping": {"share": 0.7, "n": 20}, "title_words_majority": ["kundan", "set"]},
        "_all": {"image_count": {"median": 6, "q1": 4, "q3": 8, "n": 500}},
    },
}


@pytest.fixture(autouse=True)
def fake_evidence(monkeypatch):
    monkeypatch.setattr(engine, "evidence", lambda: EVIDENCE)


def listing(**kw):
    base = {"item_id": "1", "url": "https://www.daraz.pk/products/x-i1.html", "title": "Kundan set for women",
            "price": 900.0, "discount_pct": 0, "image_count": 6, "variant_count": 1, "free_shipping": True,
            "rank": 30, "sold": None, "review_count": 0, "rating": None, "analysed_reviews": []}
    return {**base, **kw}


def live(n=40):
    return [{"rank": i, "item_id": str(100 + i), "name": f"Kundan set {i}", "item_url": f"https://daraz.pk/i{i}",
             "price": 800.0 + i, "discount_pct": 30.0, "free_shipping": True, "voucher": False, "coins": False,
             "daraz_choice": False, "sponsored": False} for i in range(1, n + 1)]


def test_results_are_never_gaps():
    me = listing(review_count=0, rating=None, sold=None, rank=None)
    rival = listing(item_id="2", review_count=120, rating=4.6, sold=340, rank=3)
    gaps, info = engine.analyze("p", me, rival, "kundan set", live())
    text = " ".join(g["title"].lower() for g in gaps)
    assert "review" not in text and "rating" not in text and "sold" not in text
    assert info["standing"]["competitor"]["reviews"] == 120 and info["standing"]["you"]["reviews"] == 0


def test_a_proven_lever_outside_the_top_listings_range_is_a_gap_with_a_target():
    gaps, _ = engine.analyze("p", listing(image_count=2), listing(item_id="2", image_count=8), "kundan set", live())
    photo = [g for g in gaps if g["details"]["kind"] == "daraz_photos"]
    assert len(photo) == 1
    assert "5 to 9" in photo[0]["description"] and photo[0]["opportunity"].startswith("Try this:")
    assert photo[0]["evidence"], "top listings are shown as examples"


def test_inside_the_normal_range_is_not_a_gap():
    gaps, info = engine.analyze("p", listing(image_count=6), listing(item_id="2", image_count=9), "kundan set", live())
    assert not [g for g in gaps if g["details"]["kind"] == "daraz_photos"]
    assert any(r["key"] == "image_count" and r["group"] == "competitor_does" for r in info["comparison"])


def test_an_unproven_lever_never_makes_a_gap():
    gaps, _ = engine.analyze("p", listing(variant_count=0), listing(item_id="2", variant_count=12), "kundan set", live())
    assert not [g for g in gaps if "option" in g["title"].lower()]


def test_competitor_complaints_are_an_opening_even_without_own_reviews():
    bad = [{"review": f"plating gone {i}", "sentiment": "negative",
            "reasons": [{"aspect": "Quality", "polarity": "negative", "confidence": 0.97}]} for i in range(4)]
    ok = [{"review": f"nice {i}", "sentiment": "positive", "reasons": []} for i in range(8)]
    gaps, info = engine.analyze("p", listing(), listing(item_id="2", analysed_reviews=bad + ok), "kundan set", live())
    r = [g for g in gaps if g["details"]["kind"] == "daraz_reviews"]
    assert len(r) == 1 and "complain about quality" in r[0]["title"]
    assert "compared from 10 reviews" in info["reviews"]["note"]


def test_search_word_is_picked_from_the_title():
    assert engine.pick_search_word("Beautiful Kundan Set for women with tikka") == "kundan set"
    assert engine.pick_search_word("Leather wallet") is None


def test_a_lever_proven_the_unexpected_way_is_never_advice(monkeypatch):
    ev = {**EVIDENCE, "levers": {**EVIDENCE["levers"], "photo_face|sold": {
        "outcome": "number sold", "lever": "photo_face", "kind": "yesno", "proven": True, "direction": "less is better",
        "words_tested": 8, "words_positive": 0, "median_rho": -0.1, "p_corrected": 0.02}}}
    monkeypatch.setattr(engine, "evidence", lambda: ev)
    assert engine.proven("photo_face") is None
