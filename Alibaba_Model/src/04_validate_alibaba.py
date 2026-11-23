"""Evaluate saved weights against untouched, imbalanced Alibaba reviews."""
from __future__ import annotations

import json

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.feature_extraction.text import TfidfVectorizer

from common import ROOT, LABELS, NAME_TO_LABEL, load_predictor, review_input, save_json


def run(device="auto"):
    frame = pd.read_csv(ROOT / "data/alibaba_validation/alibaba_reviews_validation.csv").fillna("")
    frame["true_label"] = frame.gap_severity_label.map(NAME_TO_LABEL)
    if frame.true_label.isna().any():
        raise ValueError("Validation CSV contains unknown gap_severity_label values")
    inputs = [review_input(row.review_text, row.top_category, row.title) for row in frame.itertuples()]
    predictions = load_predictor(device)(inputs)
    frame["predicted_label"] = [p["label"] for p in predictions]
    frame["predicted_name"] = [p["label_name"] for p in predictions]
    frame["confidence"] = [p["confidence"] for p in predictions]
    frame["correct"] = frame.true_label == frame.predicted_label
    truth = frame.true_label.astype(int)
    predicted = frame.predicted_label.astype(int)
    gap_mask = truth.isin([1, 2])
    report = {"rows": len(frame), "accuracy": accuracy_score(truth, predicted),
              "macro_f1": f1_score(truth, predicted, average="macro", labels=[0, 1, 2], zero_division=0),
              "binary_gap_recall": float(predicted[gap_mask].isin([1, 2]).mean()) if gap_mask.any() else None,
              "gap_rows": int(gap_mask.sum()),
              "mean_confidence_correct": float(frame.loc[frame.correct, "confidence"].mean()) if frame.correct.any() else None,
              "mean_confidence_incorrect": float(frame.loc[~frame.correct, "confidence"].mean()) if (~frame.correct).any() else None,
              "per_class": classification_report(truth, predicted, labels=[0, 1, 2], target_names=list(LABELS.values()), output_dict=True, zero_division=0)}
    output = ROOT / "artifacts/reports"
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "alibaba_predictions.csv", index=False)
    inspection = frame.loc[gap_mask, ["review_text", "gap_severity_label", "predicted_name", "confidence"]].copy()
    if not inspection.empty:
        try:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(2, 3))
            matrix = vectorizer.fit_transform(inspection.review_text.astype(str))
            names = vectorizer.get_feature_names_out()
            inspection["pain_phrase"] = [names[matrix.getrow(i).toarray().argmax()] for i in range(len(inspection))]
        except ValueError:
            inspection["pain_phrase"] = "none extracted"
    lines = ["# Alibaba cross-domain validation", "", f"Rows: {len(frame)}; gap rows: {report['gap_rows']}.",
             f"Accuracy: {report['accuracy']:.3f}; macro F1: {report['macro_f1']:.3f}; binary gap recall: {report['binary_gap_recall']:.3f}.",
             f"Mean confidence, correct: {report['mean_confidence_correct']}; incorrect: {report['mean_confidence_incorrect']}.",
             "", "## All Alibaba gap reviews", "", "| Review | True | Predicted | Confidence | Extracted phrase |", "|---|---|---|---:|---|"]
    for row in inspection.itertuples():
        quote = str(row.review_text).replace("|", "\\|").replace("\n", " ")[:250]
        lines.append(f"| {quote} | {row.gap_severity_label} | {row.predicted_name} | {row.confidence:.3f} | {row.pain_phrase} |")
    lines += ["", "## Full classification report", "", "```json", json.dumps(report["per_class"], indent=2), "```"]
    (output / "alibaba_validation_report.md").write_text("\n".join(lines), encoding="utf-8")
    save_json(output / "alibaba_validation_metrics.json", report)
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
