"""What each Daraz review says: sentiment and reasons.

Sentiment: the team's fine-tuned XLM-RoBERTa (Development/Daraz_Model), used as it is. On 148 jewellery reviews
checked by a person it was right 136 times (92%).

Reasons: the team model and our Model A together (data_collection/daraz/tune_combined.py):
  1. every reason the team model gives (its own 95% rule: almost always right, but it misses most reasons);
  2. plus Model A's jewellery reasons when Model A is sure enough: cut-offs chosen on our 800 training labels
     (praise by F1; complaints by F0.5, because complaints become gaps and a wrong one costs more than a missed one);
  3. one review never gets the same reason as both praise and complaint.
Reasons are still not a complete list: "what customers say" counts the clear reasons only.
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


def _load_reasons():
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
    return _cache["reasons"]


def _reason_probs(texts: list[str]):
    """Our Model A (jewellery reasons, trained on 800 labelled Daraz jewellery reviews): one probability per reason."""
    kind, obj = _load_reasons()
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


#: The team model's reason names -> ours (same map as in training, data_collection/daraz/train_review_model.py).
TEAM_MAP = {"Quality": "quality", "Performance": "quality", "Authenticity": "quality", "Durability": "breakage",
            "As_Described": "as_pictured", "Size_Capacity": "size_fit", "Design_Comfort": "design", "Price": "price_value",
            "Delivery": "delivery", "Packaging": "packaging", "Seller": "seller"}


def _team_key(reason: dict[str, Any]) -> str | None:
    ours = TEAM_MAP.get(reason.get("aspect", ""))
    if not ours or (reason.get("aspect") == "Authenticity" and reason.get("polarity") == "positive"):
        return None
    return ours + ("+" if reason.get("polarity") == "positive" else "-")


def _cutoffs() -> dict[str, Any]:
    kind, obj = _load_reasons()
    return (obj.get("combine") or {}) if kind == "bundle" else {}


def jewellery_reasons(texts: list[str], team_reasons: list[list[dict[str, Any]]] | None = None) -> list[list[dict[str, Any]]]:
    """Reasons per review. With team_reasons (the team model's own reasons, same order) and saved cut-offs:
    the combined rule above; else Model A alone at its plain 0.5 cut-off."""
    if not texts:
        return []
    prob, labels, threshold = _reason_probs(texts)
    comb = _cutoffs() if team_reasons is not None else {}
    t_pos, t_neg = comb.get("t_praise", threshold), comb.get("t_complaint", threshold)
    out = []
    for i, row in enumerate(prob):
        p = dict(zip(labels, (float(x) for x in row)))
        team = {k for k in (_team_key(r) for r in (team_reasons[i] if comb else [])) if k in p}
        keep = team | {lab for lab, v in p.items() if v >= (t_pos if lab.endswith("+") else t_neg)}
        for lab in list(keep):                       # never both praise and complaint for one reason
            other = lab[:-1] + ("-" if lab.endswith("+") else "+")
            if lab in keep and other in keep:
                if (lab in team) != (other in team):
                    keep.discard(other if lab in team else lab)
                else:
                    keep.discard(other if p[lab] >= p[other] else lab)
        rs = [{"aspect": lab[:-1], "polarity": "positive" if lab.endswith("+") else "negative",
               "confidence": round(p[lab], 3),
               "source": "both models" if lab in team and p[lab] >= (t_pos if lab.endswith("+") else t_neg)
               else ("team model" if lab in team else "Model A")} for lab in keep]
        out.append(sorted(rs, key=lambda r: -r["confidence"]))
    return out


def analyse(texts: list[str]) -> list[dict[str, Any]]:
    """One result per text: {"sentiment": ..., "reasons": [{"aspect", "polarity", "confidence", "source"}]}.

    Sentiment: the team's model. Reasons: the combined rule (module note) when Model A is installed, else the team's."""
    texts = [t for t in texts if t and t.strip()]
    if not texts or not available():
        return []
    try:
        result = _analyzer().analyze(texts)["per_review"]
        if jewellery_model_available():
            combined = jewellery_reasons([r["review"] for r in result], [r.get("reasons") or [] for r in result])
            for r, reasons in zip(result, combined):
                r["team_reasons"] = r.get("reasons") or []
                r["reasons"] = reasons
                r["reason_model"] = "team model + Model A (jewellery)" if _cutoffs() else "Model A (jewellery)"
        return result
    except Exception as exc:  # noqa: BLE001 - reviews are one layer; the others still run
        logger.warning("Review model failed: %s", exc)
        return []
