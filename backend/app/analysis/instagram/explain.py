"""Grounded explanation of one gap: retrieval from pgvector, then the LLM.

  1. The gap's own facts (numbers, SHAP values) come from the gaps table.
  2. The question "why is this a gap?" is embedded and the closest post chunks
     are retrieved from instagram_post_chunks -- separately for the competitor
     and for the user, so the two sides are never mixed up.
  3. The LLM explains the gap using ONLY those facts and numbered evidence, and
     must cite it as [E1], [E2]...
  4. Code checks every citation points at evidence that was really given; an
     answer citing anything else is marked ungrounded.

The LLM does not decide whether something is a gap; the model and rules did
that in stage 4. It only explains, from evidence it is shown.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from app.core.errors import ConflictError, NotFoundError

from . import embeddings

logger = logging.getLogger("optistratix.analysis.explain")

CHUNKS_PER_SIDE = 3
SEARCH_POOL = 60   # retrieve wide, then keep only posts of the right format

FORMAT_OF = {"image": "photo", "video": "video / reel", "sidecar": "carousel"}


def _post_format(post: dict[str, Any]) -> str:
    return FORMAT_OF.get(str(post.get("media_type") or "").lower(), "other")


def _gap_format(gap: dict[str, Any]) -> str | None:
    """'Use of carousel posts: ...' -> 'carousel' (None for other gaps)."""
    m = re.match(r"Use of (.+?) posts:", gap.get("title") or "")
    return m.group(1) if m else None


# ------------------------------------------------------------------ index
def build_chunk_rows(project_id: str, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The chunks to embed for a project's posts (caption, hashtags, comments)."""
    from app.api.v1.agents.ecommerce_preprocess import chunk_text

    pending: list[dict[str, Any]] = []
    for post in posts:
        fields = post.get("text_fields") or {}
        if not fields:  # older rows: rebuild the fields from the columns
            tags = post.get("hashtags") or []
            fields = {"caption": post.get("caption") or "",
                      "hashtags": " ".join(f"#{t}" for t in tags) if isinstance(tags, list) else str(tags)}
        for field_type, text in fields.items():
            for index, chunk in enumerate(chunk_text(text or "")):
                pending.append({
                    "id": f"{post['id']}::{field_type}::{index}",
                    "project_id": project_id,
                    "post_id": post["id"],
                    "source_id": post.get("source_id"),
                    "role": post.get("role"),
                    "competitor_id": post.get("competitor_id"),
                    "field_type": field_type,
                    "chunk_index": index,
                    "chunk_text": chunk,
                    "post_url": post.get("post_url") or "",
                })
    return pending


def index_posts(repo, project_id: str, posts: list[dict[str, Any]] | None = None) -> int:
    """Embeds the project's posts into pgvector. Returns how many chunks were stored."""
    posts = posts if posts is not None else repo.list_instagram_posts(project_id)
    rows = build_chunk_rows(project_id, posts)
    vectors = embeddings.embed([r["chunk_text"] for r in rows])
    for row, vector in zip(rows, vectors):
        row["embedding"] = vector
    repo.replace_instagram_chunks(project_id, rows)
    return len(rows)


# ------------------------------------------------------------------ prompt
def _points(x: float) -> str:
    return f"{x * 100:+.1f} points"


def build_prompt(gap: dict[str, Any], evidence: list[dict[str, Any]], formats: str = "") -> str:
    ev = "\n".join(
        f"[{e['id']}] ({e['side']}, {e.get('format') or 'post'}) {e['text']}" for e in evidence
    ) or "(no evidence found)"
    return f"""You explain why a point was flagged as a gap between a business's Instagram account (the user) and a competitor.

GAP: {gap['title']}
FACTS (from our analysis; numbers are exact):
{gap['description']}

{formats}
EVIDENCE (real scraped posts and comments; each is labelled with its format; the only other facts you may use):
{ev}

RULES
1. Use ONLY the facts and evidence above. Do not invent numbers, posts or claims.
2. Cite the evidence you use as [E1], [E2]. If no evidence supports a point, leave the point out.
3. This is a pattern in data, not proof of cause. Say so.
4. Do NOT give advice or a strategy. Only explain why this was flagged.
5. Plain, simple words. At most 120 words.

Return ONLY JSON: {{"explanation": "...", "evidence_used": ["E1", "E2"]}}"""


def parse_and_check(raw: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Parses the answer and drops citations to evidence that was never given."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        data = json.loads(m.group(0)) if m else {"explanation": raw or "", "evidence_used": []}
    except json.JSONDecodeError:
        data = {"explanation": raw or "", "evidence_used": []}
    valid = {e["id"] for e in evidence}
    text = str(data.get("explanation") or "")
    cited = set(re.findall(r"\[(E\d+)\]", text)) | {str(c) for c in data.get("evidence_used") or []}
    unknown = sorted(cited - valid)
    return {
        "explanation": text,
        "evidence_used": sorted(cited & valid, key=lambda s: int(s[1:])),
        "unknown_citations": unknown,
        "grounded": not unknown and bool(cited & valid),
    }


# ------------------------------------------------------------------ main
def explain_gap(repo, project_id: str, gap_id: str, call_llm: Callable[[str], str] | None) -> dict[str, Any]:
    if call_llm is None:
        raise ConflictError("Explanations need an LLM. Add GROQ_API_KEY to backend/.env and restart.")

    gap = next((g for g in repo.list_gaps(project_id) if g.get("id") == gap_id), None)
    if gap is None:
        raise NotFoundError(f"Gap {gap_id} was not found")

    posts = repo.list_instagram_posts(project_id)
    if not posts:
        raise ConflictError("This project has no scraped posts to explain from.")

    # Which competitor this gap is about: from the posts it already cites.
    by_source = {p.get("source_id"): p for p in posts}
    competitor_id = next(
        (by_source[e["source_id"]].get("competitor_id") for e in gap.get("evidence") or []
         if e.get("source_id") in by_source and by_source[e["source_id"]].get("role") == "competitor"),
        None,
    )

    query = embeddings.embed([f"{gap['title']}. {gap['description']}"])[0]
    fmt = _gap_format(gap)
    post_by_id = {p["id"]: p for p in posts}

    def search(role: str, comp: str | None) -> list[dict[str, Any]]:
        hits = repo.match_instagram_chunks(
            project_id, query, role=role, competitor_id=comp, count=SEARCH_POOL,
        )
        if fmt and role == "competitor":
            # A format gap is evidenced only by the competitor's posts OF THAT FORMAT.
            hits = [h for h in hits if _post_format(post_by_id.get(h.get("post_id"), {})) == fmt]
            if not hits:  # those posts have no caption text: cite the posts themselves
                hits = [
                    {"post_id": p["id"], "field_type": "post", "post_url": p.get("post_url") or "",
                     "chunk_text": (p.get("caption") or "(no caption)").strip(), "similarity": 0.0}
                    for p in posts
                    if p.get("role") == "competitor" and (comp is None or p.get("competitor_id") == comp)
                    and _post_format(p) == fmt
                ]
        # One evidence item per post: a post's caption and hashtags are separate
        # chunks, and showing both would list the same post twice.
        unique, seen = [], set()
        for h in hits:
            if h.get("post_id") in seen:
                continue
            seen.add(h.get("post_id"))
            unique.append(h)
        return unique[:CHUNKS_PER_SIDE]

    competitor_hits, own_hits = search("competitor", competitor_id), search("own", None)
    if not competitor_hits and not own_hits:
        # Posts scraped before pgvector indexing existed: index them now, once.
        logger.info("No pgvector chunks for %s yet; indexing its posts", project_id)
        index_posts(repo, project_id, posts)
        competitor_hits, own_hits = search("competitor", competitor_id), search("own", None)

    evidence: list[dict[str, Any]] = []
    for side, hits in (("competitor", competitor_hits), ("you", own_hits)):
        for hit in hits:
            evidence.append({
                "id": f"E{len(evidence) + 1}",
                "side": side,
                "field_type": hit.get("field_type") or "",
                "text": (hit.get("chunk_text") or "")[:400],
                "post_url": hit.get("post_url") or "",
                "similarity": round(float(hit.get("similarity") or 0.0), 3),
                "format": _post_format(post_by_id.get(hit.get("post_id"), {})),
            })

    # Exact format counts, so the LLM never has to guess what kind of posts these are.
    def mix(rows: list[dict[str, Any]]) -> str:
        counts: dict[str, int] = {}
        for r in rows:
            counts[_post_format(r)] = counts.get(_post_format(r), 0) + 1
        return ", ".join(f"{n} {k}" for k, n in sorted(counts.items())) or "none"

    own = [p for p in posts if p.get("role") == "own"]
    comp_rows = [p for p in posts if p.get("role") == "competitor"
                 and (competitor_id is None or p.get("competitor_id") == competitor_id)]
    formats = f"POST FORMATS (exact counts): competitor: {mix(comp_rows)}. You: {mix(own)}.\n"

    result = parse_and_check(call_llm(build_prompt(gap, evidence, formats)), evidence)
    result.update(gap_id=gap_id, evidence=evidence)
    return result