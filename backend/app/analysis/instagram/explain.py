"""Grounded explanation of one gap, in plain words (retrieval-augmented: RAG).

What the LLM is given, and nothing else:
  1. FACTS from our analysis: what was found, its exact numbers (you / competitor / typical), how sure we are,
     and whether it is proven or only worth testing. These come from the gaps table, never from the LLM.
  2. EVIDENCE: real scraped posts with their real likes, comments and dates --
       a) the example posts the card already shows (picked by rule in stage 4), and
       b) the posts closest in meaning to the gap, RETRIEVED from pgvector (instagram_post_chunks), separately
          for the competitor and for the user, so the two sides are never mixed up.
The LLM writes two short parts -- what we found, and why this gap exists -- citing posts as [E1], [E2].
Code then checks every citation points at evidence that was really given; anything else is removed and the
answer is marked "treat with care". The LLM never decides what is a gap: the statistics in stage 4 did that.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from app.core.errors import ConflictError, NotFoundError

from . import embeddings, knowledge

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


def build_plain_prompt(gap: dict[str, Any], details: dict[str, Any], evidence: list[dict[str, Any]],
                       knowledge: list[dict[str, Any]] | None = None) -> str:
    """Prompt for a shop owner with no technical background: the numbers, why it is a gap, and why this kind of
    difference can matter (from checked facts only). No advice: actions belong to the strategy stage."""
    lines = []
    for e in evidence:
        bits = ["your post" if e["side"] == "you" else "competitor's post", e.get("format") or "post"]
        if e.get("date"):
            bits.append(e["date"])
        if e.get("likes") is not None:
            bits.append(f"{e['likes']} likes")
        if e.get("comments") is not None:
            bits.append(f"{e['comments']} comments")
        lines.append(f"[{e['id']}] ({', '.join(bits)}) {e['text'] or '(no caption)'}")
    numbers = "\n".join(
        f"- {n['label']}: you {n.get('you') or '-'}, competitor {n.get('competitor') or '-'}"
        + (f", typical for similar accounts {n['typical']}" if n.get("typical") else "")
        for n in details.get("numbers") or []
    ) or "(none)"
    proof = ("NOT PROVEN YET: with this many posts it could still be chance. Say so in the numbers part."
             if details.get("unproven") else "")
    kb = "\n".join(f"[{k['id']}] {k['text']}" for k in knowledge or []) or "(none)"
    return f"""You help the owner of a small shop who is not technical understand ONE finding about their Instagram compared with a competitor.

FINDING: {gap['title']}
FACTS (exact, from our analysis): {gap['description']}
NUMBERS (exact):
{numbers}
{proof}
POSTS (real posts, with their real likes and comments):
{chr(10).join(lines) or '(none)'}
GENERAL KNOWLEDGE (checked facts from trusted sources):
{kb}

Write three short parts:
- "found": what the numbers show, with the exact values. One sentence.
- "why": why this counts as a gap, from the posts: how the competitor's posts of this kind did, compared with their other
  posts or with the user's posts. One or two sentences. Cite posts as [E1], [E2].
- "general": one sentence on why this kind of difference can matter for a shop, using ONLY the GENERAL KNOWLEDGE above,
  cited as [K1]. You may connect it to what the posts show is being sold. If there is no general knowledge, or none fits,
  return "".

RULES
1. Use ONLY the information above. Never invent numbers, posts, products or facts.
2. Do NOT tell the owner what to do: no advice, no "try", no "you should". Actions are planned later, in the strategy.
3. Do not repeat the finding word for word.
4. No technical words (no model, percentile, statistics, p-value, SHAP, benchmark, correlation, dataset).
5. At most 80 words in total.
6. Do not compare the likes of single posts (like "your post got 1 like, theirs got 2"): a few likes say nothing. Talk
   about the pattern, and write multiples in words: "about 40% more likes", not "1.4x".
7. Say "jewellery shops on Instagram" for the wider market. Never give how many shops or accounts were studied.

Return ONLY JSON: {{"found": "...", "why": "...", "general": "...", "evidence_used": ["E1"], "knowledge_used": ["K1"]}}"""


def parse_and_check(raw: str, evidence: list[dict[str, Any]],
                    knowledge: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Parses the answer and drops citations to posts or facts that were never given.

    The general part must rest on a checked fact: if it cites none that was given, it is removed, so the LLM cannot
    add general claims of its own.
    """
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        data = json.loads(m.group(0)) if m else {"explanation": raw or "", "evidence_used": []}
    except json.JSONDecodeError:
        data = {"explanation": raw or "", "evidence_used": []}
    valid_e = {e["id"] for e in evidence}
    valid_k = {k["id"] for k in knowledge or []}
    found, why = str(data.get("found") or ""), str(data.get("why") or "")
    raw_general = str(data.get("general") or "")
    general_k = set(re.findall(r"\[(K\d+)\]", raw_general))
    general = raw_general if general_k & valid_k else ""
    text = str(data.get("explanation") or " ".join(t for t in (found, why, general) if t))
    cited_e = set(re.findall(r"\[(E\d+)\]", f"{text} {found} {why}")) | {
        str(c) for c in data.get("evidence_used") or [] if str(c).startswith("E")}
    cited_k = set(re.findall(r"\[(K\d+)\]", f"{text} {raw_general}")) | {
        str(c) for c in data.get("knowledge_used") or [] if str(c).startswith("K")}
    unknown = sorted((cited_e - valid_e) | (cited_k - valid_k))
    return {
        "explanation": text,
        "found": found,
        "why": why,
        "general": general,
        "evidence_used": sorted(cited_e & valid_e, key=lambda s: int(s[1:])),
        "knowledge_used": sorted(cited_k & valid_k, key=lambda s: int(s[1:])),
        "unknown_citations": unknown,
        "grounded": not unknown and bool(cited_e & valid_e),
    }


# ------------------------------------------------------------------ retrieval for the current gaps
RETRIEVED_PER_SIDE = 2


def _retrieve(repo, project_id: str, gap: dict[str, Any], details: dict[str, Any], have: set[str],
              start: int) -> list[dict[str, Any]]:
    """Posts closest in meaning to the gap, from pgvector, per side -- skipping posts already given.

    Retrieval adds context; it is never required. If the index is empty or the search fails, the explanation is
    written from the card's own posts only.
    """
    try:
        posts = repo.list_instagram_posts(project_id)
        by_id = {p["id"]: p for p in posts}
        query = embeddings.embed([f"{gap['title']}. {gap['description']}"])[0]
        out: list[dict[str, Any]] = []
        for side, role in (("competitor", "competitor"), ("you", "own")):
            kept = 0
            for h in repo.match_instagram_chunks(project_id, query, role=role, count=SEARCH_POOL):
                post = by_id.get(h.get("post_id"), {})
                url = h.get("post_url") or post.get("post_url") or ""
                if not url or url in have or kept >= RETRIEVED_PER_SIDE:
                    continue
                have.add(url)
                kept += 1
                out.append({
                    "id": f"E{start + len(out) + 1}", "side": side, "field_type": h.get("field_type") or "post",
                    "retrieved": True, "text": (h.get("chunk_text") or "")[:400], "post_url": url,
                    "similarity": round(float(h.get("similarity") or 0.0), 3), "format": _post_format(post),
                    "date": str(post.get("posted_at") or "")[:10] or None, "likes": post.get("like_count"),
                    "comments": post.get("comment_count"), "image_url": post.get("media_url") or "",
                })
        return out
    except Exception as exc:  # noqa: BLE001 - retrieval is extra context, never a reason to fail
        logger.warning("Retrieval for gap %s skipped: %s", gap.get("id"), exc)
        return []


def _save(repo, project_id: str, gap: dict[str, Any], result: dict[str, Any]) -> None:
    """Keeps the latest explanation on the gap (details.explanation), so the PDF report can include it.

    Saving is a convenience: if it fails, the explanation is still shown on screen.
    """
    from app.services import demo_data

    saved = {
        "found": result.get("found", ""), "why": result.get("why", ""), "general": result.get("general", ""),
        "explanation": result.get("explanation", ""), "grounded": bool(result.get("grounded")),
        "evidence_used": result.get("evidence_used", []), "knowledge_used": result.get("knowledge_used", []),
        "unknown_citations": result.get("unknown_citations", []),
        "evidence": [{k: e.get(k) for k in ("id", "side", "format", "date", "likes", "comments", "post_url", "retrieved",
                                            "image_url")}
                     | {"text": (e.get("text") or "")[:200]} for e in result.get("evidence", [])],
        "knowledge": result.get("knowledge", []),
        "at": demo_data.iso(),
    }
    try:
        repo.update_gap(project_id, gap["id"], {"details": {**(gap.get("details") or {}), "explanation": saved}})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not save the explanation of gap %s: %s", gap.get("id"), exc)


# ------------------------------------------------------------------ main
def explain_gap(repo, project_id: str, gap_id: str, call_llm: Callable[[str], str] | None) -> dict[str, Any]:
    if call_llm is None:
        raise ConflictError("Explanations need an LLM. Add GROQ_API_KEY to backend/.env and restart.")

    gap = next((g for g in repo.list_gaps(project_id) if g.get("id") == gap_id), None)
    if gap is None:
        raise NotFoundError(f"Gap {gap_id} was not found")

    # Current gaps carry their own example posts: explain from exactly those.
    details = gap.get("details") or {}
    examples = details.get("examples") or []
    if examples:
        evidence = [{
            "id": f"E{i + 1}", "side": ex.get("who", "competitor"), "field_type": "post", "retrieved": False,
            "text": (ex.get("caption") or "")[:400], "post_url": ex.get("postUrl") or "", "similarity": 1.0,
            "format": ex.get("format") or "post", "date": ex.get("date"), "likes": ex.get("likes"),
            "comments": ex.get("comments"), "image_url": ex.get("imageUrl") or "",
        } for i, ex in enumerate(examples)]
        evidence += _retrieve(repo, project_id, gap, details, {e["post_url"] for e in evidence}, len(evidence))
        from app.services.post_stills import fill_evidence, post_stills
        fill_evidence(evidence, post_stills(repo, project_id))
        facts = knowledge.retrieve(gap)
        result = parse_and_check(call_llm(build_plain_prompt(gap, details, evidence, facts)), evidence, facts)
        result.update(gap_id=gap_id, evidence=evidence, knowledge=facts, values=details.get("numbers") or [],
                      how_sure=details.get("howSure"), unproven=bool(details.get("unproven")))
        _save(repo, project_id, gap, result)
        return result

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
