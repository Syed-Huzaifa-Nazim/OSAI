"""What is a post about? Uses the topic model trained on the public business captions (train_topics.py).

A post gets a topic only if at least MIN_WORDS words of its caption are in the model's vocabulary;
otherwise it gets none, and the app says how many posts could be read. Captions in languages the
model was not trained on mostly get none. That is a limit, not an error.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger("optistratix.analysis.topics")
HERE = Path(__file__).parent
MIN_WORDS = 2          # words found in the vocabulary before a topic is trusted
_model: dict[str, Any] | None = None
_names: dict[str, Any] | None = None


def _load():
    global _model, _names
    if _model is None:
        p = HERE / "topic_model.joblib"
        try:
            _model = joblib.load(p) if p.exists() else {}
        except Exception as exc:  # noqa: BLE001 - a model saved by another scikit-learn version can fail to load
            logger.warning("topic_model.joblib could not be loaded (%s). Retrain it with: "
                           "python -m app.analysis.instagram.train_topics --profiles <profiles csv>", exc)
            _model = {}
        n = HERE / "topic_names.json"
        _names = json.loads(n.read_text())["topics"] if n.exists() else {}
    return _model, _names


def available() -> bool:
    return bool(_load()[0])


def info(topic_id: int) -> dict[str, Any]:
    names = _load()[1]
    t = names.get(str(topic_id), {})
    return {"name": t.get("name", f"Topic {topic_id}"), "generic": bool(t.get("generic")), "terms": t.get("terms", [])}


def assign(captions: list[str]) -> list[int | None]:
    """One topic id (or None) per caption."""
    model, _ = _load()
    if not model:
        return [None] * len(captions)
    cleaned = [re.sub(r"https?://\S+|@\w+", " ", c or "") for c in captions]
    X = model["vectorizer"].transform(cleaned)
    W = model["nmf"].transform(X)
    words = np.asarray((X > 0).sum(axis=1)).ravel()
    out: list[int | None] = []
    for row, n in zip(W, words):
        out.append(None if n < MIN_WORDS or row.sum() == 0 else int(row.argmax()))
    return out
