"""Fine-tune DistilBERT and evaluate once on a product-disjoint test set."""
from __future__ import annotations

import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import torch
import numpy as np
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, classification_report, confusion_matrix, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, EarlyStoppingCallback, Trainer, TrainingArguments

from common import ROOT, LABELS, config, review_input, save_json


class ReviewDataset(torch.utils.data.Dataset):
    def __init__(self, frame, tokenizer, max_length):
        self.encoded = tokenizer([review_input(row.review_text, row.category, row.product_title) for row in frame.itertuples()],
                                 truncation=True, padding=True, max_length=max_length)
        self.labels = frame.label.astype(int).tolist()

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, index):
        return {**{key: torch.tensor(value[index]) for key, value in self.encoded.items()}, "labels": torch.tensor(self.labels[index])}


def metrics(pred):
    predictions = pred.predictions.argmax(axis=-1)
    return {"accuracy": accuracy_score(pred.label_ids, predictions), "macro_f1": f1_score(pred.label_ids, predictions, average="macro")}


def run(device="auto"):
    settings = config()
    frames = {split: pd.read_csv(ROOT / f"data/processed/{split}.csv").fillna("") for split in ("train", "val", "test")}
    tokenizer = AutoTokenizer.from_pretrained(settings["model_name"])
    datasets = {name: ReviewDataset(frame, tokenizer, settings["max_length"]) for name, frame in frames.items()}
    model = AutoModelForSequenceClassification.from_pretrained(settings["model_name"], num_labels=3,
        id2label={i: LABELS[i] for i in LABELS}, label2id={v: k for k, v in LABELS.items()})
    output = ROOT / "artifacts/model"
    reports = ROOT / "artifacts/reports"
    output.mkdir(parents=True, exist_ok=True); reports.mkdir(parents=True, exist_ok=True)
    use_cuda = torch.cuda.is_available() if device == "auto" else device == "cuda"
    args = TrainingArguments(output_dir=str(output / "checkpoints"), learning_rate=settings["learning_rate"],
        per_device_train_batch_size=settings["batch_size"], per_device_eval_batch_size=settings["batch_size"],
        num_train_epochs=settings["epochs"], weight_decay=settings["weight_decay"], warmup_ratio=settings["warmup_ratio"],
        eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True, metric_for_best_model="macro_f1",
        greater_is_better=True, save_total_limit=2, seed=settings["seed"], fp16=use_cuda,
        use_cpu=not use_cuda, report_to="none")
    trainer = Trainer(model=model, args=args, train_dataset=datasets["train"], eval_dataset=datasets["val"],
                      compute_metrics=metrics, callbacks=[EarlyStoppingCallback(early_stopping_patience=1)])
    trainer.train()
    val_result = trainer.predict(datasets["val"])
    logits = val_result.predictions
    labels = frames["val"].label.astype(int).to_numpy()
    candidates = np.linspace(.5, 3.0, 51)
    def nll(temperature):
        scaled = logits / temperature
        scaled = scaled - scaled.max(axis=1, keepdims=True)
        log_probs = scaled - np.log(np.exp(scaled).sum(axis=1, keepdims=True))
        return -log_probs[np.arange(len(labels)), labels].mean()
    temperature = float(min(candidates, key=nll))
    result = trainer.predict(datasets["test"])
    predicted = result.predictions.argmax(axis=-1)
    truth = frames["test"].label.astype(int).to_numpy()
    scores = {"accuracy": accuracy_score(truth, predicted), "macro_f1": f1_score(truth, predicted, average="macro"),
              "weighted_f1": f1_score(truth, predicted, average="weighted"),
              "per_class": classification_report(truth, predicted, labels=[0, 1, 2], target_names=list(LABELS.values()), output_dict=True, zero_division=0),
              "best_checkpoint": trainer.state.best_model_checkpoint, "epochs_completed": trainer.state.epoch,
              "calibration_temperature": temperature, "validation_nll": float(nll(temperature)),
              "train_rows": len(frames["train"]), "val_rows": len(frames["val"]), "test_rows": len(frames["test"])}
    save_json(reports / "training_metrics.json", scores)
    ConfusionMatrixDisplay(confusion_matrix(truth, predicted, labels=[0, 1, 2]), display_labels=list(LABELS.values())).plot(cmap="Blues")
    plt.tight_layout(); plt.savefig(reports / "confusion_matrix.png"); plt.close()
    trainer.save_model(output); tokenizer.save_pretrained(output)
    save_json(output / "label_map.json", LABELS)
    save_json(output / "calibration.json", {"temperature": temperature, "fitted_on": "Amazon validation"})
    return scores


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    print(json.dumps(run(parser.parse_args().device), indent=2))

