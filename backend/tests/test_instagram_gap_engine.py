"""The Instagram gap engine: similar-account comparison, tested format gaps, plain-language output."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from app.analysis.instagram import engine, explain, peer, post_results as pr
from app.models.gap import Gap
from app.services.repository import MemoryRepository


def _rows(role, cid, name, plan, n=30, followers=2000, website=False):
    out = []
    for i in range(n):
        fmt, likes, comments = plan(i)
        out.append({
            "id": f"{role}{i}", "role": role, "competitor_id": cid, "source_id": f"s{role}{i}",
            "post_url": f"https://instagram.com/p/{role}{i}/", "media_url": f"https://cdn.example/{role}{i}.jpg",
            "profile_url": f"https://instagram.com/{name}/", "submitted_url": f"https://instagram.com/{name}/",
            "profile_username": name, "caption": f"post {i} #gold" if i % 2 else f"DM us to order {i}?",
            "posted_at": f"2023-0{1 + i // 10}-{1 + i % 28:02d}T10:00:00+00:00", "media_type": fmt,
            "like_count": likes, "comment_count": comments,
            "profile_stats": {"followers_count": followers, "following_count": 300, "posts_count": 200,
                              "biography": "Jewellery shop", "external_url": "https://shop.pk" if website else None,
                              "highlights_count": 3},
            "scraped_at": "2023-09-15T00:00:00+00:00",
        })
    return out


def _built(n=30):
    comp = _rows("competitor", "c1", "rival", lambda i: ("Sidecar", 300, 20) if i < 12 else ("Image", 110, 8), n, website=True)
    mine = _rows("own", None, "myshop", lambda i: ("Video", 20, 1) if i < 8 else ("Image", 100, 6), n)
    return mine + comp


@pytest.fixture(autouse=True)
def _no_model(monkeypatch):
    monkeypatch.setattr(engine, "_model", None)
    monkeypatch.setattr(engine, "MODEL_PATH", engine.MODEL_PATH.with_name("no_such_model.joblib"))


# ------------------------------------------------------------------ similar accounts
def test_the_benchmark_ships_with_three_equal_size_groups():
    assert peer.available()
    sizes = [peer.band_info(b)["n_accounts"] for b in ("small", "medium", "large")]
    assert sum(sizes) == 997 and max(sizes) - min(sizes) <= 2
    assert peer.band_of(100) == "small" and peer.band_of(2000) == "medium" and peer.band_of(10_000) == "large"


def test_percentile_is_the_share_of_similar_accounts_at_or_below():
    low = peer.percentile("feat_avg_hashtags", "medium", 0.0)
    high = peer.percentile("feat_avg_hashtags", "medium", 1000.0)
    assert 0 <= low <= 50 and high == 100.0
    assert peer.percentile("feat_avg_hashtags", "medium", None) is None
    assert peer.quarter(10) == 0 and peer.quarter(60) == 2 and peer.quarter(99) == 3


# ------------------------------------------------------------------ post results
def test_posts_are_marked_strong_normal_or_weak_against_their_own_account():
    d = pr.prepare(pd.DataFrame({
        "caption": ["a"] * 9, "posted_at": ["2023-01-01T00:00:00+00:00"] * 9, "media_type": ["Image"] * 9,
        "likes_count": [1, 2, 3, 4, 5, 6, 7, 8, 9], "comments_count": [0] * 9}))
    assert list(d["level"].iloc[:3]) == ["weak"] * 3 and list(d["level"].iloc[-3:]) == ["strong"] * 3
    hidden = pr.prepare(pd.DataFrame({"caption": ["a"], "posted_at": [None], "media_type": ["Image"],
                                      "likes_count": [-1], "comments_count": [5]}))
    assert hidden["results"].isna().all()           # hidden likes are not counted as zero


def test_format_tests_say_chance_when_it_could_be_chance():
    assert pr.more_often_p(12, 30, 0, 30) < 0.01
    assert pr.more_often_p(5, 30, 3, 30) > 0.05


# ------------------------------------------------------------------ the gaps
def test_gaps_are_plain_validated_and_come_with_example_posts():
    found, warnings, summary = engine.analyze_project("proj", _built())
    kinds = {g["details"]["kind"] for g in found}
    assert {"format", "weakness", "profile"} <= kinds
    for g in found:
        Gap.model_validate(g)                                     # the same check the API applies
        assert g["details"]["howSure"] in ("Low", "Medium", "High")
        assert g["priority"] == "medium"                          # the seller sets priorities
        assert "SHAP" not in g["description"] + g["opportunity"] and "percentile" not in g["description"]
    carousel = next(g for g in found if g["details"]["kind"] == "format")
    assert "carousels" in carousel["title"] and "12 of their last 30" in carousel["description"]
    assert carousel["details"]["examples"] and carousel["details"]["examples"][0]["imageUrl"]
    assert summary["competitors"][0]["formats"]["gaps"] == 1


def test_no_comment_gaps_any_more():
    found, _, summary = engine.analyze_project("proj", _built())
    assert all(g["category"] != "audience" for g in found)
    assert "comments" not in summary["competitors"][0]


def test_few_posts_cap_the_certainty_and_say_so():
    found, warnings, _ = engine.analyze_project("proj", _built(n=6))
    assert found and all(g["details"]["howSure"] == "Low" for g in found)
    assert any("Scrape up to 30" in w for w in warnings)


def test_missing_follower_counts_skip_the_similar_account_parts():
    rows = _built()
    for r in rows:
        r["profile_stats"] = {}
    found, warnings, _ = engine.analyze_project("proj", rows)
    assert any("Follower counts" in w for w in warnings)
    assert all(g["details"]["kind"] in ("format", "weakness") for g in found)


def test_an_equal_pair_produces_no_gaps_and_says_it_is_a_result():
    same = lambda i: ("Image", 100, 6)  # noqa: E731
    rows = _rows("own", None, "a", same) + _rows("competitor", "c1", "b", same)
    found, warnings, _ = engine.analyze_project("proj", rows)
    assert found == [] and any("clear enough to find" in w for w in warnings)


# ------------------------------------------------------------------ Explain
def test_explain_uses_the_cards_own_example_posts_and_rejects_made_up_citations():
    found, _, _ = engine.analyze_project("proj", _built())
    repo = MemoryRepository("u")
    repo.replace_gaps("proj", found)
    gap = next(g for g in found if g["details"]["kind"] == "format")

    good = lambda prompt: json.dumps({"explanation": "They post carousels [E1].", "evidence_used": ["E1"]})  # noqa: E731
    r = explain.explain_gap(repo, "proj", gap["id"], good)
    assert r["grounded"] and [e["post_url"] for e in r["evidence"]] == [x["postUrl"] for x in gap["details"]["examples"]]

    fake = lambda prompt: json.dumps({"explanation": "They ran a giveaway [E9].", "evidence_used": ["E9"]})  # noqa: E731
    r2 = explain.explain_gap(repo, "proj", gap["id"], fake)
    assert not r2["grounded"] and r2["unknown_citations"] == ["E9"]

    seen = {}
    explain.explain_gap(repo, "proj", gap["id"], lambda p: seen.setdefault("p", p) and good(p))
    assert "SHAP" in seen["p"] and "No technical words" in seen["p"]      # told not to use jargon


def test_explain_adds_retrieved_posts_and_returns_what_why_and_the_values(monkeypatch):
    rows = _built()
    found, _, _ = engine.analyze_project("proj", rows)
    repo = MemoryRepository("u")
    repo.replace_gaps("proj", found)
    repo.replace_instagram_posts("proj", [{**r, "project_id": "proj"} for r in rows])
    gap = next(g for g in found if g["details"]["kind"] == "format")
    shown = {x["postUrl"] for x in gap["details"]["examples"]}
    # a small pgvector index: one chunk per post, all at the same "meaning" as the query
    monkeypatch.setattr(explain.embeddings, "embed", lambda texts: [[1.0, 0.0] for _ in texts])
    repo.replace_instagram_chunks("proj", [
        {"id": f"{r['id']}::caption::0", "project_id": "proj", "post_id": r["id"], "source_id": r["source_id"],
         "role": r["role"], "competitor_id": r["competitor_id"], "field_type": "caption", "chunk_index": 0,
         "chunk_text": r["caption"], "post_url": r["post_url"], "embedding": [1.0, 0.0]} for r in rows])

    seen = {}

    def llm(prompt):
        seen["p"] = prompt
        return json.dumps({"found": "They post carousels in 12 of 30 posts [E1].", "why": "Their carousels got more likes [E1].",
                           "evidence_used": ["E1"]})

    r = explain.explain_gap(repo, "proj", gap["id"], llm)
    retrieved = [e for e in r["evidence"] if e["retrieved"]]
    assert retrieved and all(e["post_url"] not in shown for e in retrieved)              # new posts, not repeats
    assert {e["side"] for e in retrieved} == {"competitor", "you"}                          # both sides searched
    assert all(e["likes"] is not None for e in retrieved)                                   # real values, from the posts
    assert r["found"] and r["why"] and r["grounded"] and r["values"] == gap["details"]["numbers"]
    assert '"why"' in seen["p"] and "likes" in seen["p"]


def test_explain_still_works_when_the_search_fails(monkeypatch):
    found, _, _ = engine.analyze_project("proj", _built())
    repo = MemoryRepository("u")
    repo.replace_gaps("proj", found)
    gap = next(g for g in found if g["details"]["kind"] == "format")

    def broken(_):
        raise RuntimeError("no index")

    monkeypatch.setattr(explain.embeddings, "embed", broken)
    r = explain.explain_gap(repo, "proj", gap["id"], lambda p: json.dumps({"found": "a [E1]", "why": "b", "evidence_used": ["E1"]}))
    assert r["grounded"] and not any(e["retrieved"] for e in r["evidence"])


# ------------------------------------------------------------------ PDF report
def test_the_gap_report_is_a_pdf_with_the_saved_explanation_and_only_kept_gaps_when_asked(monkeypatch):
    from app.services import gap_report

    rows = _built()
    found, _, _ = engine.analyze_project("proj", rows)
    repo = MemoryRepository("u")
    repo.replace_gaps("proj", found)
    monkeypatch.setattr(explain.embeddings, "embed", lambda texts: [[1.0, 0.0] for _ in texts])
    gap = next(g for g in found if g["details"]["kind"] == "format")
    explain.explain_gap(repo, "proj", gap["id"], lambda p: json.dumps(
        {"found": "They post carousels much more [E1].", "why": "Their carousels got more likes [E1].", "evidence_used": ["E1"]}))
    saved = next(g for g in repo.list_gaps("proj") if g["id"] == gap["id"])
    assert saved["details"]["explanation"]["why"].startswith("Their carousels")       # Explain is kept for the PDF

    monkeypatch.setattr(gap_report, "_picture", lambda url: None)                     # no network in tests
    pdf = gap_report.render_gaps_pdf(repo, {"id": "proj", "name": "AB Wholesale"}, repo.list_gaps("proj"), "all")
    assert pdf.startswith(b"%PDF") and len(pdf) > 2000

    repo.update_gap("proj", gap["id"], {"decision": "accepted"})
    kept = gap_report.select_gaps(repo.list_gaps("proj"), "kept")
    assert [g["id"] for g in kept] == [gap["id"]]
    assert gap_report.render_gaps_pdf(repo, {"id": "proj", "name": "x"}, repo.list_gaps("proj"), "kept").startswith(b"%PDF")


def test_emoji_are_removed_from_report_text():
    from app.services.gap_report import _clean
    assert _clean("Order now 🔥✨ <b>") == "Order now  &lt;b&gt;"


# ------------------------------------------------------------------ general reasons from the checked knowledge base
def test_a_carousel_gap_gets_the_checked_carousel_fact_and_a_photo_gap_gets_none(monkeypatch):
    from app.analysis.instagram import knowledge

    monkeypatch.setattr(knowledge.embeddings, "embed", lambda texts: [[1.0, 0.0] for _ in texts])
    carousel = {"title": "Your competitor posts carousels much more often than you do.", "details": {"kind": "format"}}
    facts = knowledge.retrieve(carousel)
    assert facts and facts[0]["id"] == "K1" and "swipe" in facts[0]["text"] and facts[0]["url"].startswith("https://")
    photo = {"title": "Worth testing: photos", "details": {"kind": "format"}}
    assert knowledge.retrieve(photo) == []                       # no checked source for photos: no general reason
    assert all(f["source"] and f["url"] for f in knowledge.facts())


def test_a_general_reason_without_a_checked_fact_is_removed():
    ev = [{"id": "E1"}]
    kb = [{"id": "K1", "text": "x", "source": "s", "url": "u"}]
    ok = explain.parse_and_check(json.dumps({"found": "a", "why": "b [E1]", "general": "Carousels show more [K1]."}), ev, kb)
    assert ok["general"] and ok["knowledge_used"] == ["K1"] and ok["grounded"]
    made_up = explain.parse_and_check(json.dumps({"found": "a", "why": "b [E1]", "general": "Carousels go viral."}), ev, kb)
    assert made_up["general"] == ""                              # the LLM cannot add general claims of its own
    fake_k = explain.parse_and_check(json.dumps({"found": "a", "why": "b [E1]", "general": "x [K7]"}), ev, kb)
    assert fake_k["general"] == "" and "K7" in fake_k["unknown_citations"] and not fake_k["grounded"]


def test_the_explain_prompt_gives_no_suggestion_to_copy(monkeypatch):
    found, _, _ = engine.analyze_project("proj", _built())
    repo = MemoryRepository("u")
    repo.replace_gaps("proj", found)
    monkeypatch.setattr(explain.embeddings, "embed", lambda texts: [[1.0, 0.0] for _ in texts])
    gap = next(g for g in found if g["details"]["kind"] == "format")
    seen = {}
    explain.explain_gap(repo, "proj", gap["id"], lambda p: seen.setdefault("p", p) and json.dumps(
        {"found": "a", "why": "b [E1]", "general": "c [K1]"}))
    assert gap["opportunity"] not in seen["p"] and "IDEA" not in seen["p"] and "no advice" in seen["p"]
    assert "[K1]" in seen["p"] and "GENERAL KNOWLEDGE" in seen["p"]


def test_the_report_carries_the_platform_logo():
    from app.services import gap_report
    assert gap_report.LOGO.exists() and gap_report.LOGO.suffix == ".png"
