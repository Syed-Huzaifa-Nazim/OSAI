"""Stage 3: chunking and embedding for website and social comparisons.

LIVE IMPLEMENTATION. Embeds the real scraped text, not an excerpt.

Each document -- a crawled page, or a post -- arrives with its text already
split by field: a page's body, its headings and its metadata; a post's caption,
its hashtags and its comments. Every field is chunked and tagged separately, so
retrieval can be scoped to one of them rather than searching everything at
once. That is the same treatment a product listing gets in
``ecommerce_preprocess``, and the chunker and embedder are literally the same
ones, so retrieval behaves identically across all four scrapers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.api.v1.agents.ecommerce_preprocess import chunk_text, embed_texts
from app.vectorstore import chroma

logger = logging.getLogger("optistratix.agents.preprocess.source")


class SourcePreprocessAgent(BaseAgent):
    name = "Preprocessing (website/social)"
    stage = 3
    is_live = True

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        project_id: str = context["project_id"]
        documents: list[dict[str, Any]] = context.get("source_documents", [])

        if not documents:
            return AgentResult(
                payload={"chunk_count": 0, "stored": 0},
                items_processed=0,
                duration_ms=self._elapsed_ms(started),
                warnings=["No scraped pages or posts to embed."],
            )

        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []
        per_source: dict[str, int] = {}

        for document in documents:
            document_id = document["id"]
            source_id = document.get("source_id") or ""
            before = len(ids)

            for field_type, text in (document.get("text_fields") or {}).items():
                for index, chunk in enumerate(chunk_text(text)):
                    ids.append(f"{document_id}::{field_type}::{index}")
                    texts.append(chunk)
                    metadatas.append({
                        "project_id": project_id,
                        # What the Insight Agent cites, so evidence resolves to a
                        # row the sources screen already shows.
                        "source_id": source_id,
                        "document_id": document_id,
                        "source_url": document.get("page_url") or document.get("post_url") or "",
                        # A page has a title; a post has its caption instead.
                        "source_title": (document.get("title") or document.get("caption") or "")[:200],
                        "kind": document.get("kind", ""),
                        "role": document.get("role", ""),
                        # Which competitor this passage belongs to, so a
                        # comparison against one of several stays scoped to it.
                        "competitor_id": document.get("competitor_id") or "",
                        "field_type": field_type,
                        "chunk_index": index,
                    })

            if source_id:
                per_source[source_id] = per_source.get(source_id, 0) + (len(ids) - before)

        # Instagram posts are stored in Supabase (pgvector, table
        # instagram_post_chunks), not in Chroma: the Explain step searches them
        # there. The pipeline writes the rows returned in the artifacts.
        if all(document.get("kind") == "instagram" for document in documents):
            return await self._instagram_to_pgvector(started, ids, texts, metadatas, per_source)

        # Embedding is CPU-bound; keep the event loop free for other requests.
        embeddings = await asyncio.to_thread(embed_texts, texts)

        stored = 0
        warnings: list[str] = []
        try:
            stored = chroma.add_chunks(project_id, ids, texts, metadatas, embeddings)
        except Exception as exc:  # noqa: BLE001 - the run continues without vectors
            logger.warning("Could not write to Chroma for %s: %s", project_id, exc)

        if stored == 0 and ids:
            warnings.append(
                "Chroma is unavailable, so chunks were counted but not persisted."
            )
            # Nothing is retrievable, so no source should claim embedded chunks.
            per_source = {source_id: 0 for source_id in per_source}
        if embeddings is None and ids:
            warnings.append(
                "sentence-transformers was unavailable, so Chroma's built-in embedder was "
                "used. It is the same all-MiniLM-L6-v2 model, so retrieval is unaffected."
            )

        logger.info(
            "Embedded %d chunks across %d documents for %s", len(ids), len(documents), project_id
        )

        return AgentResult(
            payload={"chunk_count": len(ids), "stored": stored},
            artifacts={"source_chunk_counts": per_source},
            items_processed=len(ids),
            duration_ms=self._elapsed_ms(started),
            tokens_used=None,
            cost_usd=None,
            warnings=warnings,
        )


    async def _instagram_to_pgvector(
        self,
        started: float,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
        per_source: dict[str, int],
    ) -> AgentResult:
        from app.analysis.instagram import embeddings as pg_embeddings

        warnings: list[str] = []
        try:
            vectors = await asyncio.to_thread(pg_embeddings.embed, texts)
        except Exception as exc:  # noqa: BLE001 - scraping must not fail on this
            logger.warning("Could not embed Instagram chunks: %s", exc)
            vectors = []
            warnings.append(
                f"Posts were stored, but could not be embedded for search ({exc}). "
                "The Explain step will try again."
            )
        rows = [
            {
                "id": chunk_id,
                "project_id": meta["project_id"],
                "post_id": meta["document_id"],
                "source_id": meta.get("source_id") or None,
                "role": meta.get("role") or None,
                "competitor_id": meta.get("competitor_id") or None,
                "field_type": meta.get("field_type") or "",
                "chunk_index": meta.get("chunk_index", 0),
                "chunk_text": text,
                "post_url": meta.get("source_url") or "",
                "embedding": vector,
            }
            for chunk_id, text, meta, vector in zip(ids, texts, metadatas, vectors)
        ]
        if not rows:
            per_source = {source_id: 0 for source_id in per_source}
        return AgentResult(
            payload={"chunk_count": len(ids), "stored": len(rows)},
            artifacts={"instagram_chunks": rows, "source_chunk_counts": per_source},
            items_processed=len(rows),
            duration_ms=self._elapsed_ms(started),
            tokens_used=None,
            cost_usd=None,
            warnings=warnings,
        )


__all__ = ["SourcePreprocessAgent"]