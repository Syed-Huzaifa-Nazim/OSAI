"""Grounded explanation of one Daraz gap, in plain words (retrieval-augmented: RAG), like Instagram's Explain.

What the LLM is given, and nothing else:
  1. FACTS from the Daraz Gap Engine: the finding, its exact numbers (you / competitor / top 20 listings) and how sure
     we are. These come from the gaps table, never from the LLM.
  2. EVIDENCE from Daraz itself:
       a) what the card already holds: the buyers' reviews it quotes, or the top listings it shows, and
       b) the text closest in meaning to the gap, RETRIEVED from the project's vector store (both listings' title,
          description, specifications and reviews, embedded in stage 3), separately for you and your competitor.
The LLM writes two short parts -- what we found, and why it matters to buyers -- citing evidence as [E1], [E2].
Code then checks every citation (instagram.explain.parse_and_check); anything not given is removed and the answer is
marked "treat with care". The LLM never decides what is a gap: stage 4 did that.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.analysis.instagram.explain import _save, parse_and_check
from app.core.errors import ConflictError, NotFoundError

logger = logging.getLogger("optistratix.analysis.daraz.explain")

RETRIEVED_PER_SIDE = 2
#: Listing text worth showing (offers, category and the "no return policy found" placeholder are not).
USEFUL_FIELDS = {"title", "description", "specs", "review"}


def _snippet(text: str) -> str:
    """A piece from the middle of a text: a retrieved chunk containing it repeats evidence already given."""
    t = " ".join(text.split())
    return t[len(t) // 2 - 20: len(t) // 2 + 20] if len(t) > 60 else t
FIELD_NAME = {"title": "title", "description": "description", "specs": "specifications", "review": "reviews",
              "promo_tags": "offers", "policy_text": "return policy", "category": "category"}


def _card_evidence(gap: dict[str, Any]) -> list[dict[str, Any]]:
    """The reviews the card quotes, or the top listings it shows (with their pictures)."""
    details = gap.get("details") or {}
    out: list[dict[str, Any]] = []
    if details.get("kind") == "daraz_reviews":
        image = next((e.get("imageUrl") for e in details.get("examples") or [] if e.get("imageUrl")), "")
        for e in gap.get("evidence") or []:
            if not e.get("quote"):
                continue
            mine = str(e.get("source_title") or "").lower().startswith("your")
            out.append({"side": "you" if mine else "competitor", "format": "review", "field_type": "review",
                        "text": e["quote"][:400], "post_url": e.get("source_url") or "", "image_url": image})
    else:
        for ex in details.get("examples") or []:
            out.append({"side": "competitor", "format": "listing", "field_type": "top listing",
                        "text": (ex.get("caption") or "")[:400], "post_url": ex.get("postUrl") or "",
                        "image_url": ex.get("imageUrl") or ""})
    return out


def _retrieve(project_id: str, gap: dict[str, Any], have: set[str]) -> list[dict[str, Any]]:
    """Listing text closest in meaning to the gap, per side, from the project's vector store (stage 3)."""
    try:
        from app.vectorstore import chroma

        query = f"{gap['title']}. {gap['description']}"
        out: list[dict[str, Any]] = []
        for side, role in (("you", "own"), ("competitor", "competitor")):
            kept = 0
            for h in chroma.query(project_id, query, n_results=8, where={"role": role}):
                text = (h.get("document") or "").strip()
                meta = h.get("metadata") or {}
                if (not text or kept >= RETRIEVED_PER_SIDE or meta.get("field_type") not in USEFUL_FIELDS
                        or any(snippet in " ".join(text.split()) for snippet in have)):
                    continue                 # empty, enough already, a placeholder field, or a review already shown
                have.add(_snippet(text))
                kept += 1
                field = str(meta.get("field_type") or "listing")
                out.append({"side": side, "format": "review" if field == "review" else "listing",
                            "field_type": FIELD_NAME.get(field, field), "text": text[:400], "retrieved": True,
                            "post_url": meta.get("source_url") or "", "image_url": "",
                            "similarity": round(float(h.get("relevance") or 0.0), 3)})
        return out
    except Exception as exc:  # noqa: BLE001 - retrieval is extra context, never a reason to fail
        logger.warning("Retrieval for Daraz gap %s skipped: %s", gap.get("id"), exc)
        return []


def build_prompt(gap: dict[str, Any], details: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    lines = []
    for e in evidence:
        whose = "your" if e["side"] == "you" else "your competitor's"
        what = ("buyer's review" if e["format"] == "review" and not e.get("retrieved")
                else f"listing {e['field_type']}" if e["format"] == "listing" and e.get("retrieved")
                else "top listing for the same search" if e["format"] == "listing" else f"listing {e['field_type']}")
        label = what if what.startswith("top") else f"{whose} {what}"
        lines.append(f"[{e['id']}] ({label}) {e['text']}")
    numbers = "\n".join(
        f"- {n['label']}: you {n.get('you') or '-'}, competitor {n.get('competitor') or '-'}"
        + (f", top 20 listings for the same search {n['typical']}" if n.get("typical") else "")
        for n in details.get("numbers") or []) or "(none)"
    worth = ("WORTH FIXING, NOT A PROVEN GAP: the owner's own buyers say this, but not more often than the "
             "competitor's buyers. Say so in the numbers part." if details.get("unproven") else "")
    return f"""You help the owner of a small Daraz shop, who is not technical, understand ONE finding about their listing compared with a competitor's.

FINDING: {gap['title']}
FACTS (exact, from our analysis): {gap['description']}
NUMBERS (exact):
{numbers}
{worth}
EVIDENCE (real text from Daraz: reviews and listings):
{chr(10).join(lines) or '(none)'}

Write two short parts:
- "found": what the numbers show, with the exact values. One sentence.
- "why": why this matters to buyers choosing between listings on Daraz, shown by the evidence (what buyers wrote, or
  what the top listings do). One or two sentences. Cite evidence as [E1], [E2].

RULES
1. Use ONLY the information above. Never invent numbers, reviews, products or facts.
2. Do NOT tell the owner what to do: no advice, no "try", no "you should".
3. Reviews may be in Roman Urdu: give their meaning in simple English, do not quote them word for word.
4. No technical words (no model, statistics, p-value, dataset, benchmark, correlation, percentile).
5. At most 70 words in total.

Return ONLY JSON: {{"found": "...", "why": "...", "evidence_used": ["E1"]}}"""


def explain_gap(repo, project_id: str, gap_id: str, call_llm: Callable[[str], str] | None) -> dict[str, Any]:
    if call_llm is None:
        raise ConflictError("Explanations need an LLM. Add GROQ_API_KEY to backend/.env and restart.")
    gap = next((g for g in repo.list_gaps(project_id) if g.get("id") == gap_id), None)
    if gap is None:
        raise NotFoundError(f"Gap {gap_id} was not found")
    details = gap.get("details") or {}
    evidence = _card_evidence(gap)
    evidence += _retrieve(project_id, gap, {_snippet(e["text"]) for e in evidence})
    for i, e in enumerate(evidence):
        e.update(id=f"E{i + 1}", date=None, likes=None, comments=None)
        e.setdefault("retrieved", False)
        e.setdefault("similarity", 1.0)
    result = parse_and_check(call_llm(build_prompt(gap, details, evidence)), evidence, [])
    result.update(gap_id=gap_id, evidence=evidence, knowledge=[], general="", values=details.get("numbers") or [],
                  how_sure=details.get("howSure"), unproven=bool(details.get("unproven")))
    _save(repo, project_id, gap, result)
    return result
