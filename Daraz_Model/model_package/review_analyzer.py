"""Review analyzer: the file the integrating developer uses.

    from review_analyzer import ReviewAnalyzer
    az = ReviewAnalyzer("model_package")           # folder produced by train_all.py
    result = az.analyze(["delivery bohat late thi", "quality is great", ...])

`result` is a plain JSON-serialisable dict:
{
  "summary": {"total": 50, "positive": {"count": 31, "percent": 62.0},
              "negative": {...}, "neutral": {...}},
  "reasons": {
     "negative": [ {"aspect": "Delivery", "reviews": 9, "percent_of_reviews": 18.0,
                    "evidence": [ {"review": "parcel 10 din late aya", "confidence": 0.93}, ... ]}, ... ],
     "positive": [ ... ]
  },
  "per_review": [ {"review": "...", "sentiment": "negative", "sentiment_confidence": 0.91,
                   "reasons": [{"aspect": "Delivery", "polarity": "negative", "confidence": 0.93}]}, ... ]
}
Percentages are shares of the reviews that were passed in. Evidence = the user's own comments, ranked by the
model's confidence for that reason (identical texts are shown once).
Needs: numpy, joblib, scikit-learn (same version as in config.json). Transformer backends also need torch + transformers.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

SENT_NAMES = {-1: "negative", 0: "neutral", 1: "positive"}


def format_report(result: dict) -> str:
    """Human-readable text version of analyze()'s result (for quick manual checking)."""
    s = result["summary"]
    if not s.get("total"):
        return "No reviews."
    lines = [f"Reviews analysed: {s['total']}",
             f"Positive {s['positive']['percent']}% | Negative {s['negative']['percent']}% | "
             f"Neutral {s['neutral']['percent']}%"]
    for pol in ("negative", "positive"):
        lines.append(f"\n{pol.upper()} reasons:")
        if not result["reasons"][pol]:
            lines.append("  (none found with enough confidence)")
        for r in result["reasons"][pol]:
            lines.append(f"  {r['aspect']}: {r['reviews']} review(s) ({r['percent_of_reviews']}%)")
            for e in r["evidence"]:
                lines.append(f"      [{e['confidence']}] {e['review']}")
    lines.append("\nPER REVIEW:")
    for p in result["per_review"]:
        rs = ", ".join(f"{x['aspect']}({'+' if x['polarity'] == 'positive' else '-'})" for x in p["reasons"]) or "-"
        lines.append(f"  [{p['sentiment']} {p['sentiment_confidence']}] {p['review']}\n      reasons: {rs}")
    return "\n".join(lines)


class ReviewAnalyzer:
    def __init__(self, model_dir: str | Path):
        self.dir = Path(model_dir)
        self.cfg = json.loads((self.dir / "config.json").read_text(encoding="utf-8"))
        self.aspects: list[str] = self.cfg["aspects"]
        # precision-oriented threshold (validation precision >= 80%): used for reasons and evidence
        self.threshold: float = float(self.cfg["aspect"].get("precision_threshold", self.cfg["aspect"]["threshold"]))
        self._sent = self._load(self.cfg["sentiment"])
        self._asp = self._load(self.cfg["aspect"])

    # ------------------------------------------------------------------ loading / prediction backends
    def _load(self, spec: dict):
        path = self.dir / spec["path"]
        if spec["backend"] == "sklearn":
            import joblib   # SAFETY: pickle-based; only load model files produced by train_all.py (trusted, own artifact)
            return ("sklearn", joblib.load(path))
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(path)
        model = AutoModelForSequenceClassification.from_pretrained(path).eval()
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        return ("transformer", (tok, model.to(dev), dev))

    def _proba(self, backend, texts: list[str], kind: str) -> np.ndarray:
        name, obj = backend
        if name == "sklearn":
            p = obj.predict_proba(texts)
            return np.asarray(p)
        import torch
        tok, model, dev = obj
        out = []
        with torch.no_grad():
            for i in range(0, len(texts), 64):
                enc = tok(texts[i:i + 64], truncation=True, max_length=self.cfg.get("max_len", 128),
                          padding=True, return_tensors="pt").to(dev)
                logits = model(**enc).logits.float()
                p = torch.softmax(logits, -1) if kind == "sentiment" else torch.sigmoid(logits)
                out.append(p.cpu().numpy())
        return np.vstack(out)

    # ------------------------------------------------------------------ public API
    def analyze(self, reviews: list[str], evidence_per_reason: int = 3) -> dict:
        texts = [str(r).strip() for r in reviews if r is not None and str(r).strip()]
        if not texts:
            return {"summary": {"total": 0}, "reasons": {"positive": [], "negative": []}, "per_review": []}
        sp = self._proba(self._sent, texts, "sentiment")          # columns = classes -1, 0, 1
        ap = self._proba(self._asp, texts, "aspect")              # columns = aspects(pos) then aspects(neg)
        k = len(self.aspects)
        sent_idx = sp.argmax(1)
        sent_val = np.array([-1, 0, 1])[sent_idx]

        per_review = []
        for i, t in enumerate(texts):
            rs = []
            for j, a in enumerate(self.aspects):
                if ap[i, j] >= self.threshold:
                    rs.append({"aspect": a, "polarity": "positive", "confidence": round(float(ap[i, j]), 3)})
                if ap[i, k + j] >= self.threshold:
                    rs.append({"aspect": a, "polarity": "negative", "confidence": round(float(ap[i, k + j]), 3)})
            rs.sort(key=lambda r: -r["confidence"])
            per_review.append({"review": t, "sentiment": SENT_NAMES[int(sent_val[i])],
                               "sentiment_confidence": round(float(sp[i, sent_idx[i]]), 3), "reasons": rs})

        n = len(texts)
        summary = {"total": n}
        for v, name in SENT_NAMES.items():
            c = int((sent_val == v).sum())
            summary[name] = {"count": c, "percent": round(100.0 * c / n, 1)}

        reasons = {"positive": [], "negative": []}
        for pol, off in (("positive", 0), ("negative", k)):
            for j, a in enumerate(self.aspects):
                hit = np.where(ap[:, off + j] >= self.threshold)[0]
                if not len(hit):
                    continue
                seen, evidence = set(), []
                for i in hit[np.argsort(-ap[hit, off + j])]:
                    key = texts[i].casefold()
                    if key in seen:
                        continue
                    # evidence must not contradict the review's own overall sentiment (confident opposite = skip)
                    if sp[i, sent_idx[i]] >= 0.7 and sent_val[i] == (1 if pol == "negative" else -1):
                        continue
                    seen.add(key)
                    evidence.append({"review": texts[i], "confidence": round(float(ap[i, off + j]), 3)})
                    if len(evidence) == evidence_per_reason:
                        break
                reasons[pol].append({"aspect": a, "reviews": int(len(hit)),
                                     "percent_of_reviews": round(100.0 * len(hit) / n, 1), "evidence": evidence})
            reasons[pol].sort(key=lambda r: -r["reviews"])
        return {"summary": summary, "reasons": reasons, "per_review": per_review}
