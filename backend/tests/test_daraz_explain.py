"""Daraz Explain: grounded in the card's reviews/listings plus retrieved listing text; invented citations removed."""
from __future__ import annotations

import json

from app.analysis.daraz import explain


class Repo:
    def __init__(self, gap):
        self.gap, self.saved = gap, None

    def list_gaps(self, project_id):
        return [self.gap]

    def update_gap(self, project_id, gap_id, patch):
        self.saved = patch


GAP = {"id": "g1", "title": "Some of your buyers complain about size",
       "description": "5 of your last 40 reviews complain about size.",
       "evidence": [{"source_title": "Your review", "source_url": "https://daraz.pk/i1", "quote": "size chota hai"}],
       "details": {"kind": "daraz_reviews", "unproven": True, "howSure": "Low",
                   "numbers": [{"label": "Reviews about size", "you": "5 of 40", "competitor": "4 of 40", "typical": None}],
                   "examples": [{"who": "you", "postUrl": "https://daraz.pk/i1", "imageUrl": "https://img/1.jpg"}]}}


def test_explain_is_grounded_and_drops_invented_citations(monkeypatch):
    from app.vectorstore import chroma

    monkeypatch.setattr(chroma, "query", lambda *a, **k: [
        {"document": "Length 4 cm, light weight", "metadata": {"field_type": "description", "role": k["where"]["role"],
                                                               "source_url": "https://daraz.pk/i1"}, "relevance": 0.7}])
    seen = {}

    def llm(prompt):
        seen["prompt"] = prompt
        return json.dumps({"found": "5 of 40 vs 4 of 40.", "why": "Buyers say it is small [E1] [E9].",
                           "evidence_used": ["E1", "E9"]})

    repo = Repo(GAP)
    out = explain.explain_gap(repo, "p", "g1", llm)
    assert out["evidence"][0]["format"] == "review" and out["evidence"][0]["side"] == "you"
    assert any(e["retrieved"] for e in out["evidence"]), "listing text is retrieved for both sides"
    assert out["evidence_used"] == ["E1"] and out["unknown_citations"] == ["E9"] and not out["grounded"]
    assert "WORTH FIXING" in seen["prompt"] and "size chota hai" in seen["prompt"]
    assert repo.saved["details"]["explanation"]["found"] == "5 of 40 vs 4 of 40."
