"""Retrieval from the checked knowledge base (knowledge_base.json) for the Explain button.

For each gap: the facts tagged for that kind of gap are found, then ranked by meaning (the same sentence embeddings
as the post search) against the gap, and the best ones are given to the LLM as [K1], [K2]. If no fact is tagged for a
gap (for example a photo gap: no checked source was found), none is given and the explanation has no general part.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from . import embeddings

logger = logging.getLogger("optistratix.analysis.knowledge")

PATH = Path(__file__).with_name("knowledge_base.json")
TOP = 2
_facts: list[dict[str, Any]] | None = None


def facts() -> list[dict[str, Any]]:
    global _facts
    if _facts is None:
        try:
            _facts = json.loads(PATH.read_text())["facts"]
        except Exception as exc:  # noqa: BLE001 - no knowledge base: explanations simply have no general part
            logger.warning("knowledge_base.json could not be read: %s", exc)
            _facts = []
    return _facts


def gap_tags(gap: dict[str, Any]) -> set[str]:
    """Which kind of difference a gap is about, read from its kind and title."""
    d = gap.get("details") or {}
    kind, title = d.get("kind"), (gap.get("title") or "").lower()
    tags: set[str] = set()
    if kind in ("format", "weakness"):
        if "carousel" in title:
            tags.add("format:carousel")
        if re.search(r"video|reel", title):
            tags.add("format:video / reel")
        if "photo" in title:
            tags.add("format:photo")
    elif kind == "hashtag":
        tags.add("hashtag")
    elif kind == "profile":
        if "website" in title or "link" in title:
            tags.add("profile:website")
    elif kind == "media":
        if "remember" in title or "memorab" in title:
            tags.add("media:memorability")
        elif "video" in title:
            tags.add("media:video_quality")
        else:
            tags.add("media:image_quality")
    return tags


def retrieve(gap: dict[str, Any], top: int = TOP) -> list[dict[str, Any]]:
    """The checked facts for this gap, best first, as [{id: 'K1', text, source, url, verified}]."""
    tags = gap_tags(gap)
    pool = [f for f in facts() if tags & set(f.get("tags") or [])]
    if len(pool) > top:
        try:
            q, *vecs = embeddings.embed([f"{gap.get('title')}. {gap.get('description')}", *(f["text"] for f in pool)])
            score = [sum(a * b for a, b in zip(q, v)) for v in vecs]
            pool = [f for _, f in sorted(zip(score, pool), key=lambda t: -t[0])]
        except Exception as exc:  # noqa: BLE001 - keep the file's order if ranking fails
            logger.info("Knowledge ranking skipped: %s", exc)
    return [{"id": f"K{i + 1}", "text": f["text"], "source": f["source"], "url": f["url"],
             "verified": bool(f.get("verified"))} for i, f in enumerate(pool[:top])]


__all__ = ["facts", "gap_tags", "retrieve"]
