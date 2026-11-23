"""Shared paths, labels and platform-independent review encoding."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LABELS = {0: "No Gap", 1: "Moderate Gap", 2: "High Gap"}
NAME_TO_LABEL = {name: number for number, name in LABELS.items()}


def config():
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def review_input(review_text, category="", product_title=""):
    return f"Category: {category or 'Unknown'} | Product: {product_title or 'Unknown'} | Review: {review_text}"


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def load_predictor(device="auto"):
    """Load only fine-tuned local weights. Never silently substitute a base model."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    path = ROOT / "artifacts/model"
    if not (path / "config.json").exists():
        raise FileNotFoundError(f"Fine-tuned model missing at {path}. Run training first.")
    chosen = "cuda" if device == "auto" and torch.cuda.is_available() else ("cpu" if device == "auto" else device)
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path).to(chosen).eval()
    calibration = path / "calibration.json"
    temperature = float(json.loads(calibration.read_text())["temperature"]) if calibration.exists() else 1.0

    def predict(texts):
        if not texts:
            return []
        result = []
        for start in range(0, len(texts), 32):
            encoded = tokenizer(texts[start:start + 32], padding=True, truncation=True, max_length=256, return_tensors="pt").to(chosen)
            with torch.inference_mode():
                probabilities = (model(**encoded).logits / temperature).softmax(dim=-1).cpu().tolist()
            for probs in probabilities:
                label = max(range(3), key=lambda i: probs[i])
                result.append({"label": label, "label_name": LABELS[label], "confidence": round(probs[label], 3), "probabilities": probs})
        return result

    return predict
