"""The team's Daraz review model, loaded once: sentiment (positive / neutral / negative) and reasons
(Quality, Delivery, Packaging, Seller...) for each review. Two fine-tuned XLM-RoBERTa models, used as they are.

Measured by the team on 5,138 unseen Daraz reviews: sentiment macro-F1 0.77 (0.85 on Roman Urdu reviews);
reasons are shown only when the model is at least 95% sure (about 76% of shown reasons are right, but only about
1 in 4 real reasons is found). So "what customers say" lists the clear reasons only, never a complete list.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger("optistratix.analysis.daraz")
_cache: dict[str, Any] = {}


def available() -> bool:
    d = Path(get_settings().daraz_review_model_dir)
    return (d / "review_analyzer.py").exists() and (d / "sentiment_model" / "model.safetensors").exists()


def _analyzer():
    if "az" not in _cache:
        d = Path(get_settings().daraz_review_model_dir)
        sys.path.insert(0, str(d))
        from review_analyzer import ReviewAnalyzer  # the team's file, unchanged

        _cache["az"] = ReviewAnalyzer(d)
    return _cache["az"]


REASONS_DIR = Path(__file__).parent / "models" / "review_reasons"


def jewellery_model_available() -> bool:
    return (REASONS_DIR / "reasons.joblib").exists() or (REASONS_DIR / "head.pt").exists()


def _team_vectors(texts: list[str]):
    """Sentence vectors from the team model's encoder (already loaded for sentiment, so no extra memory):
    mean pooling over the last layer, max 128 tokens - exactly as in training (train_review_model.py)."""
    import numpy as np
    import torch

    tok, model, dev = _analyzer()._asp[1]
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            b = tok(texts[i:i + 32], padding=True, truncation=True, max_length=128, return_tensors="pt").to(dev)
            h = model.base_model(**b).last_hidden_state
            m = b["attention_mask"].unsqueeze(-1).float()
            out.append(((h * m).sum(1) / m.sum(1)).cpu().numpy())
    return np.vstack(out)


def _reason_probs(texts: list[str]):
    """Our Model A (jewellery reasons, trained on 800 labelled Daraz jewellery reviews): one probability per reason."""
    if "reasons" not in _cache:
        if (REASONS_DIR / "reasons.joblib").exists():
            import joblib  # SAFETY: our own trained file (train_review_model.py), never a downloaded one

            _cache["reasons"] = ("bundle", joblib.load(REASONS_DIR / "reasons.joblib"))
        else:
            import torch
            from transformers import AutoModel, AutoTokenizer

            saved = torch.load(REASONS_DIR / "head.pt", map_location="cpu")
            enc = AutoModel.from_pretrained(REASONS_DIR).eval()
            head = torch.nn.Linear(enc.config.hidden_size, len(saved["labels"]))
            head.load_state_dict(saved["head"])
            _cache["reasons"] = ("finetuned", (AutoTokenizer.from_pretrained(REASONS_DIR), enc, head.eval(), saved["labels"]))
    kind, obj = _cache["reasons"]
    if kind == "bundle":
        from scipy.sparse import hstack

        parts = []
        if obj.get("tfidf"):
            w, c, clf = obj["tfidf"]
            parts.append(clf.predict_proba(hstack([w.transform(texts), c.transform(texts)]).tocsr()))
        if obj.get("xlmr_lr") is not None:
            parts.append(obj["xlmr_lr"].predict_proba(_team_vectors(texts)))
        return sum(parts) / len(parts), obj["labels"], obj.get("threshold", 0.5)
    import numpy as np
    import torch

    tok, enc, head, labels = obj
    rows = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            b = tok(texts[i:i + 32], padding=True, truncation=True, max_length=128, return_tensors="pt")
            h, m = enc(**b).last_hidden_state, b["attention_mask"].unsqueeze(-1).float()
            rows.append(torch.sigmoid(head((h * m).sum(1) / m.sum(1))).numpy())
    return np.vstack(rows), labels, 0.5


def jewellery_reasons(texts: list[str]) -> list[list[dict[str, Any]]]:
    prob, labels, threshold = _reason_probs(texts)
    out = []
    for row in prob:
        rs = [{"aspect": lab[:-1], "polarity": "positive" if lab.endswith("+") else "negative",
               "confidence": round(float(p), 3)} for lab, p in zip(labels, row) if p >= threshold]
        out.append(sorted(rs, key=lambda r: -r["confidence"]))
    return out


def analyse(texts: list[str]) -> list[dict[str, Any]]:
    """One result per text: {"sentiment": ..., "reasons": [{"aspect", "polarity", "confidence"}]}.

    Sentiment: the team's model. Reasons: our jewellery model (Model A) when it is installed, else the team's."""
    texts = [t for t in texts if t and t.strip()]
    if not texts or not available():
        return []
    try:
        result = _analyzer().analyze(texts)["per_review"]
        if jewellery_model_available():
            for r, reasons in zip(result, jewellery_reasons([r["review"] for r in result])):
                r["reasons"] = reasons
                r["reason_model"] = "jewellery (Model A)"
        return result
    except Exception as exc:  # noqa: BLE001 - reviews are one layer; the others still run
        logger.warning("Review model failed: %s", exc)
        return []
