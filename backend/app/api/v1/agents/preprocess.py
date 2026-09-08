"""Stage 3: preprocessing, chunking and embedding.

MOCK IMPLEMENTATION. Chunks the excerpt text for real and writes it to the
project's Chroma collection when Chroma is installed, but uses Chroma's default
embedding function rather than OpenAI embeddings. The chunking is genuine, so
the collection is queryable; only the embedding model is a stand-in.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.vectorstore import chroma

logger = logging.getLogger("optistratix.agents.preprocess")

CHUNK_SIZE = 480
CHUNK_OVERLAP = 60


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Splits on a sliding window, preferring to break at a sentence end.

    Overlap keeps a claim that straddles a boundary retrievable from either
    side, which matters because every gap has to cite a passage.
    """
    if not text:
        return []
    if len(text) <= size:
        return [text]

    # Clamp the overlap so each step advances by at least half a window.
    # Without this, an overlap close to `size` degrades to one chunk per
    # character on long input.
    overlap = max(0, min(overlap, size // 2))

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # Prefer a sentence boundary within the last quarter of the window.
            boundary = text.rfind(". ", start + int(size * 0.75), end)
            if boundary != -1:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


class MockPreprocessAgent(BaseAgent):
    name = "Preprocessing"
    stage = 3
    is_live = False

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        project_id: str = context["project_id"]
        sources: list[dict[str, Any]] = context.get("sources", [])

        await asyncio.sleep(0.8)

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for source in sources:
            text = f"{source.get('title', '')}\n\n{source.get('excerpt', '')}"
            for index, chunk in enumerate(chunk_text(text)):
                ids.append(f"{source['id']}::{index}")
                documents.append(chunk)
                metadatas.append(
                    {
                        "project_id": project_id,
                        "source_id": source["id"],
                        "source_url": source.get("url", ""),
                        "source_title": source.get("title", ""),
                        "kind": source.get("kind", "landing_page"),
                        "chunk_index": index,
                    }
                )

        stored = 0
        try:
            stored = chroma.add_chunks(project_id, ids, documents, metadatas)
        except Exception as exc:  # noqa: BLE001 - the pipeline continues without vectors
            logger.warning("Could not write to Chroma for %s: %s", project_id, exc)

        warnings: list[str] = []
        if stored == 0 and ids:
            warnings.append(
                "Chroma is unavailable, so chunks were counted but not persisted. "
                "Retrieval will fall back to the stored excerpts."
            )

        return AgentResult(
            payload={"chunk_count": len(ids), "stored": stored},
            items_processed=len(ids),
            duration_ms=self._elapsed_ms(started),
            tokens_used=61_400,
            cost_usd=0.184,
            warnings=warnings,
        )
