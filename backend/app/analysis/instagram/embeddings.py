"""Text -> vector, for the Instagram chunks stored in Supabase (pgvector).

The model is all-MiniLM-L6-v2: 384 numbers per chunk, the same model the rest
of the project embeds with. sentence-transformers is used when installed;
otherwise the ONNX build of the same model that ships inside the `chromadb`
package computes the vectors. Only the model is borrowed from that package --
nothing is stored in Chroma. The vectors go to instagram_post_chunks.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Sequence

DIM = 384

_onnx = None
_lock = threading.Lock()


def _normalise(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [float(x) / norm for x in vector]


def embed(texts: Sequence[str]) -> list[list[float]]:
    """Unit-length 384-number vectors, one per text."""
    texts = [t or "" for t in texts]
    if not texts:
        return []

    from app.api.v1.agents.ecommerce_preprocess import embed_texts

    vectors = embed_texts(list(texts))  # sentence-transformers, when installed
    if vectors is None:
        global _onnx
        with _lock:
            if _onnx is None:
                from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

                _onnx = ONNXMiniLM_L6_V2()
        vectors = [list(map(float, v)) for v in _onnx(list(texts))]
    return [_normalise(v) for v in vectors]
