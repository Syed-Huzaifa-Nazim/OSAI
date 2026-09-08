"""ChromaDB access (stage 3).

One collection per project, named ``project_<id>``, so a retrieval can never
reach across projects. Chroma is imported lazily: it pulls in a large
dependency tree, and the API is fully usable in demo mode without it.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger("optistratix.vectorstore")

_client: Any = None


def _slug(project_id: str) -> str:
    """Chroma collection names allow [a-zA-Z0-9._-] and must be 3-63 chars."""
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "-", project_id)
    return f"project-{cleaned}"[:63]


def get_client() -> Any:
    """Returns the persistent Chroma client, or None when unavailable."""
    global _client
    if _client is not None:
        return _client

    try:
        import chromadb  # imported here so the package stays optional
    except ImportError:
        logger.warning("chromadb is not installed; vector features are disabled")
        return None

    _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    logger.info("Chroma persisting to %s", settings.chroma_persist_dir)
    return _client


def get_collection(project_id: str) -> Any:
    """Gets or creates this project's collection."""
    client = get_client()
    if client is None:
        return None
    return client.get_or_create_collection(
        name=_slug(project_id),
        metadata={"project_id": project_id, "hnsw:space": "cosine"},
    )


def add_chunks(
    project_id: str,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, Any]],
    embeddings: list[list[float]] | None = None,
) -> int:
    """Writes chunks for one project. Returns how many were stored."""
    collection = get_collection(project_id)
    if collection is None:
        return 0

    kwargs: dict[str, Any] = {"ids": ids, "documents": documents, "metadatas": metadatas}
    if embeddings is not None:
        kwargs["embeddings"] = embeddings
    collection.add(**kwargs)
    return len(ids)


def query(project_id: str, text: str, n_results: int = 8) -> list[dict[str, Any]]:
    """Similarity search within one project's collection."""
    collection = get_collection(project_id)
    if collection is None:
        return []

    result = collection.query(query_texts=[text], n_results=n_results)
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    return [
        {
            "document": document,
            "metadata": metadata,
            # Cosine distance -> similarity, so callers get "higher is better".
            "relevance": max(0.0, 1.0 - float(distance)),
        }
        for document, metadata, distance in zip(documents, metadatas, distances)
    ]


def delete_collection(project_id: str) -> None:
    """Drops a project's collection, e.g. on pipeline reset or project delete."""
    client = get_client()
    if client is None:
        return
    try:
        client.delete_collection(_slug(project_id))
    except Exception:  # noqa: BLE001 - deleting a missing collection is fine
        logger.debug("No collection to delete for project %s", project_id)
