"""Stage 3: chunking and embedding for e-commerce comparisons.

LIVE IMPLEMENTATION. Embeds the real scraped text, not an excerpt.

What makes this different from the general preprocessor is that a product
listing is not one block of prose: a description, a spec table and a wall of
customer reviews answer completely different questions. So each text field is
chunked and tagged separately, which is what lets stage 4 retrieve, say, only
review chunks when it is reasoning about social proof.

Chunk ids and sizes match the standalone scraper's (1100 chars, 150 overlap,
12 chunks per field maximum), so retrieval behaves the same after the
migration as it did before it.

Embeddings come from all-MiniLM-L6-v2 running locally, again matching the
original. If sentence-transformers is not installed the agent falls back to
Chroma's built-in embedder rather than failing the run.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from app.api.v1.agents.base import AgentResult, BaseAgent
from app.core.config import settings
from app.vectorstore import chroma

logger = logging.getLogger("optistratix.agents.preprocess.ecommerce")

CHUNK_SIZE = 1100
CHUNK_OVERLAP = 150
MAX_CHUNKS_PER_FIELD = 12

_model_lock = threading.Lock()
_model: Any = None


def chunk_text(
    text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Splits on paragraph/sentence boundaries where possible.

    The cap on chunks per field is what stops a listing with 40 pasted reviews
    from dominating the whole collection.
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text) and len(chunks) < MAX_CHUNKS_PER_FIELD:
        end = min(start + size, len(text))
        if end < len(text):
            window = text[start:end]
            for separator in ("\n\n", "\n", ". ", " "):
                cut = window.rfind(separator)
                # Only honour a boundary past the halfway mark; otherwise a
                # single early newline would produce a stream of tiny chunks.
                if cut > size * 0.5:
                    end = start + cut + len(separator)
                    break
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


#: Set once the model is known to be unavailable, so a failed load is not
#: retried on every stage-3 run.
_model_unavailable = False


def _get_model() -> Any:
    """Loads all-MiniLM-L6-v2 once, lazily. None when unavailable.

    Every failure mode is treated the same -- fall back to Chroma's built-in
    embedder, which is the *same model* served through ONNX, so retrieval
    quality is unchanged either way. That matters because this import fails in
    more ways than a missing package: torch ships native libraries that an OS
    application-control policy can block, raising OSError rather than
    ImportError. Catching only ImportError would turn that into a failed
    pipeline stage instead of a warning.
    """
    global _model, _model_unavailable
    if _model is not None or _model_unavailable:
        return _model
    with _model_lock:
        if _model is None and not _model_unavailable:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model all-MiniLM-L6-v2 ...")
                _model = SentenceTransformer(
                    "all-MiniLM-L6-v2", cache_folder=settings.embedding_cache_path
                )
                logger.info("Embedding model ready.")
            except Exception as exc:  # noqa: BLE001 - any failure means fall back
                _model_unavailable = True
                logger.warning(
                    "sentence-transformers unavailable (%s: %s); using Chroma's built-in "
                    "all-MiniLM-L6-v2 instead",
                    exc.__class__.__name__,
                    exc,
                )
                return None
    return _model


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Returns normalised vectors, or None to let Chroma embed instead."""
    if not texts:
        return None
    model = _get_model()
    if model is None:
        return None
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [list(map(float, vector)) for vector in vectors]


class EcommercePreprocessAgent(BaseAgent):
    name = "Preprocessing (e-commerce)"
    stage = 3
    is_live = True

    async def run(self, context: dict[str, Any]) -> AgentResult:
        started = time.perf_counter()
        project_id: str = context["project_id"]
        products: list[dict[str, Any]] = context.get("ecommerce_products", [])

        if not products:
            return AgentResult(
                payload={"chunk_count": 0, "stored": 0},
                items_processed=0,
                duration_ms=self._elapsed_ms(started),
                warnings=["No scraped products to embed."],
            )

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        per_product: dict[str, int] = {}

        for product in products:
            product_id = product["id"]
            before = len(ids)

            for field_type, text in (product.get("text_fields") or {}).items():
                for index, chunk in enumerate(chunk_text(text)):
                    ids.append(f"{product_id}::{field_type}::{index}")
                    documents.append(chunk)
                    metadatas.append({
                        "project_id": project_id,
                        "product_id": product_id,
                        # source_id is what the Insight Agent cites, so evidence
                        # resolves to a row the sources screen already shows.
                        "source_id": product.get("source_id") or "",
                        "source_url": product.get("url", ""),
                        "source_title": product.get("product_name", ""),
                        "kind": "ecommerce_product",
                        "platform": product.get("platform", ""),
                        "role": product.get("role", ""),
                        "field_type": field_type,
                        "chunk_index": index,
                    })

            per_product[product_id] = len(ids) - before

        # Embedding is CPU-bound; keep the event loop free for other requests.
        embeddings = await asyncio.to_thread(embed_texts, documents)

        stored = 0
        warnings: list[str] = []
        try:
            stored = chroma.add_chunks(project_id, ids, documents, metadatas, embeddings)
        except Exception as exc:  # noqa: BLE001 - the pipeline continues without vectors
            logger.warning("Could not write to Chroma for %s: %s", project_id, exc)

        if stored == 0 and ids:
            warnings.append(
                "Chroma is unavailable, so chunks were counted but not persisted. "
                "Comparison will fall back to the structured metadata alone."
            )
            # Nothing is retrievable, so no listing should claim embedded chunks.
            per_product = {product_id: 0 for product_id in per_product}
        if embeddings is None and ids:
            warnings.append(
                "sentence-transformers was unavailable, so Chroma's built-in embedder was "
                "used. It is the same all-MiniLM-L6-v2 model, so retrieval is unaffected."
            )

        logger.info("Embedded %d chunks across %d products for %s", len(ids), len(products), project_id)

        return AgentResult(
            payload={"chunk_count": len(ids), "stored": stored},
            artifacts={"product_chunk_counts": per_product},
            items_processed=len(ids),
            duration_ms=self._elapsed_ms(started),
            # Local model, no API spend.
            tokens_used=None,
            cost_usd=None,
            warnings=warnings,
        )
