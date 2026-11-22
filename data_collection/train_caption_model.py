"""Model C: what a caption is about (several labels per caption), trained on labels/captions_labels.csv.

  .venv/bin/python train_caption_model.py [finetune_model] [--reuse]   (--reuse: rescore from saved fold predictions)

Labels: drafted by Claude from CAPTION_LABEL_GUIDE.md; a random 100 checked by a person (no errors found). giveaway (2)
and styling_tips (0) are too rare to learn and are left out. All methods are scored on the same captions with the same
5 shop-grouped folds (a shop's captions are never in both training and test), leaving out the LLM's few-shot examples:
  1. keyword rules                     (no training: a word list per label)
  2. TF-IDF + logistic regression      (classic text classifier, trained)
  3. multilingual sentence embeddings + logistic regression  (frozen pretrained encoder, trained head)
  4. fine-tuned multilingual transformer  (all weights trained; CPU)
  5. LLM zero-shot / few-shot          (reports/caption_llm_*.csv from caption_llm_baseline.py; no training)
Scores: micro-F1 (all labels pooled), macro-F1 (every label counts the same), and on the 100 person-checked captions.
Writes reports/model_c_results.csv, reports/model_c_per_label.csv, models/caption_model/ and
datasets/captions_predicted.csv (every post's caption labelled by the best trained model).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold
from sklearn.multiclass import OneVsRestClassifier
from scipy.sparse import hstack

HERE = Path(__file__).resolve().parent
REPORTS, MODELS = HERE / "reports", HERE / "models"
LABELS = ["offer", "new_arrival", "price", "call_to_order", "product_details", "review", "behind_the_scenes",
          "event_season", "other"]
ENCODER = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RULES = {
    "offer": r"\bsale\b|\b\d+\s?%|\boff\b|discount|\bdeals?\b|flat\s?\d|free (?:delivery|shipping)|buy \d+ get|bundle",
    "new_arrival": r"new (?:arrival|collection|in\b|drop|design)|just (?:in|dropped|launched|landed)|restock|back in stock|launch",
    "price": r"\b(?:rs|pkr)\.?\s?\d|\d[\d,]{2,}\s?(?:/-|rs\b|pkr)|price\s*[:\-]?\s*\d",
    "call_to_order": r"\bdm\b|inbox|whats\s?app|order (?:now|via|on|through)|link in bio|\bcod\b|cash on delivery|\+?92\s?3|\b03\d{2}|shop now|website|\.pk\b|\.com\b|to order",
    "product_details": r"silver|gold|plated|\b925\b|stone|zircon|kundan|brass|stainless|tarnish|waterproof|\bsize|colou?rs?\b|adjustable|handmade|crafted|pearl|polki|meenakari|material|finish",
    "review": r"review|feedback|happy (?:customer|client)|customer love|delivered to|thank you for (?:your|ordering|trusting)",
    "behind_the_scenes": r"packing|packed|behind the scenes|\bbts\b|our team|workshop|making of|how (?:it'?s|we) made",
    "event_season": r"\beid\b|wedding|bridal|valentine|mehndi|nikah|barat|walima|ramadan|ramzan|14 august|independence|christmas|new year|festive|shaadi|winter|summer|mother'?s day",
}


def load() -> pd.DataFrame:
    l = pd.read_csv(HERE / "labels" / "captions_labels.csv")
    posts = pd.read_csv(HERE / "data" / "posts.csv")[["caption", "handle"]].drop_duplicates("caption")
    l = l.merge(posts, left_on="caption_full", right_on="caption", how="left", suffixes=("", "_p")).drop(columns="caption_p")
    l["caption"] = l["caption"].fillna("").astype(str)
    for lab in LABELS:
        l[lab] = l["labels_draft"].str.split("|").apply(lambda x, lab=lab: int(lab in x))
    return l


def at_least_one(prob: np.ndarray) -> np.ndarray:
    """Labels with probability >= 0.5; a caption with none gets its most likely label."""
    y = (prob >= 0.5).astype(int)
    none = y.sum(1) == 0
    y[none, prob[none].argmax(1)] = 1
    return y


def rules(texts: pd.Series) -> np.ndarray:
    y = np.array([[int(bool(re.search(RULES[lab], t, re.I))) for lab in LABELS[:-1]] for t in texts])
    return np.hstack([y, (y.sum(1) == 0)[:, None].astype(int)])          # "other" = nothing matched


def tfidf_lr(tr: pd.Series, te: pd.Series, Y: np.ndarray) -> np.ndarray:
    w = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    c = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    Xtr = hstack([w.fit_transform(tr), c.fit_transform(tr)]).tocsr()
    Xte = hstack([w.transform(te), c.transform(te)]).tocsr()
    clf = OneVsRestClassifier(LogisticRegression(max_iter=3000, class_weight="balanced", C=4.0)).fit(Xtr, Y)
    return clf.predict_proba(Xte)


def embed(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(ENCODER, device="cpu").encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)


def emb_lr(Etr: np.ndarray, Ete: np.ndarray, Y: np.ndarray) -> np.ndarray:
    clf = OneVsRestClassifier(LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0)).fit(Etr, Y)
    return clf.predict_proba(Ete)


def finetune(tr: list[str], Y: np.ndarray, te: list[str], name: str, epochs: int = 10, save: Path | None = None) -> np.ndarray:
    """All weights of a pretrained multilingual encoder trained for the labels (mean pooling + linear layer, BCE loss).

    Rare labels are weighted like the other trained methods (class_weight="balanced"): positive weight = negatives /
    positives per label. The new output layer learns faster (1e-3) than the pretrained encoder (4e-5)."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    torch.manual_seed(0)
    tok = AutoTokenizer.from_pretrained(name)
    enc = AutoModel.from_pretrained(name)
    head = torch.nn.Linear(enc.config.hidden_size, Y.shape[1])
    params = list(enc.parameters()) + list(head.parameters())
    opt = torch.optim.AdamW([{"params": enc.parameters(), "lr": 4e-5}, {"params": head.parameters(), "lr": 1e-3}], weight_decay=0.01)
    steps = epochs * ((len(tr) + 15) // 16)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / (0.1 * steps)) * max(0.0, (steps - s) / steps))
    pos = Y.sum(0).clip(min=1)
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor((len(Y) - pos) / pos, dtype=torch.float32))

    def forward(texts: list[str]):
        b = tok(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
        h = enc(**b).last_hidden_state
        m = b["attention_mask"].unsqueeze(-1).float()
        return head((h * m).sum(1) / m.sum(1))

    Yt = torch.tensor(Y, dtype=torch.float32)
    rng = np.random.default_rng(0)
    enc.train()
    for _ in range(epochs):
        order = rng.permutation(len(tr))
        for i in range(0, len(tr), 16):
            idx = order[i:i + 16]
            loss = lossf(forward([tr[j] for j in idx]), Yt[idx])
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            sched.step()
    enc.eval()
    with torch.no_grad():
        prob = torch.cat([torch.sigmoid(forward(te[i:i + 64])) for i in range(0, len(te), 64)]).numpy()
    if save is not None:
        save.mkdir(parents=True, exist_ok=True)
        enc.save_pretrained(save)
        tok.save_pretrained(save)
        torch.save({"head": head.state_dict(), "labels": LABELS}, save / "head.pt")
    return prob


def score(name: str, Y: np.ndarray, P: np.ndarray, mask: np.ndarray, checked: np.ndarray) -> dict:
    m, c = mask, mask & checked
    return {"method": name, "micro_f1": round(f1_score(Y[m], P[m], average="micro"), 3),
            "macro_f1": round(f1_score(Y[m], P[m], average="macro", zero_division=0), 3),
            "exact_match": round(float((Y[m] == P[m]).all(1).mean()), 3),
            "micro_f1_on_person_checked": round(f1_score(Y[c], P[c], average="micro"), 3),
            "n_scored": int(m.sum()), "n_person_checked": int(c.sum())}


def main(ft_model: str = ENCODER, reuse: bool = False) -> None:
    l = load()
    Y = l[LABELS].to_numpy()
    texts, groups = l["caption"], l["handle"].to_numpy()
    shots_file = REPORTS / "caption_few_shot_ids.txt"
    shots = set(shots_file.read_text().split()) if shots_file.exists() else set()
    mask = ~l["caption_id"].isin(shots).to_numpy()
    checked = l["checked_by_person"].to_numpy(bool)
    print(f"{len(l)} captions · {l.handle.nunique()} shops · scored on {mask.sum()} (few-shot examples left out)", flush=True)

    E = embed(texts.tolist())
    P = {k: np.zeros_like(Y) for k in ("TF-IDF + logistic regression", "multilingual embeddings + logistic regression",
                                       "fine-tuned multilingual transformer")}
    cache = REPORTS / "model_c_cv_predictions.npz"          # fold predictions, so scores can be redone without retraining
    if reuse and cache.exists():
        z = np.load(cache, allow_pickle=True)
        P = {k: z[k] for k in z.files}
    else:
        for f, (tr, te) in enumerate(GroupKFold(n_splits=5).split(texts, Y, groups), 1):
            P["TF-IDF + logistic regression"][te] = at_least_one(tfidf_lr(texts.iloc[tr], texts.iloc[te], Y[tr]))
            P["multilingual embeddings + logistic regression"][te] = at_least_one(emb_lr(E[tr], E[te], Y[tr]))
            P["fine-tuned multilingual transformer"][te] = at_least_one(
                finetune(texts.iloc[tr].tolist(), Y[tr], texts.iloc[te].tolist(), ft_model))
            print(f"  fold {f}/5 done", flush=True)
        REPORTS.mkdir(exist_ok=True)
        np.savez(cache, **P)

    rows = [score("majority (always product_details + call_to_order)", Y,
                  np.tile((Y.mean(0) >= 0.5).astype(int) | (np.arange(len(LABELS)) == Y.sum(0).argmax()), (len(Y), 1)), mask, checked),
            score("keyword rules", Y, rules(texts), mask, checked)]
    rows += [score(k, Y, v, mask, checked) for k, v in P.items()]
    for mode in ("zero", "few"):
        f = REPORTS / f"caption_llm_{mode}.csv"
        if f.exists():
            llm = l[["caption_id"]].merge(pd.read_csv(f), on="caption_id", how="left")
            got = llm["labels_llm"].notna().to_numpy()
            Pl = np.array([[int(lab in str(s).split("|")) for lab in LABELS] for s in llm["labels_llm"].fillna("")])
            rows.append(score(f"LLM {mode}-shot ({llm['model'].dropna().iloc[0]})", Y, Pl, mask & got, checked))
    res = pd.DataFrame(rows)
    REPORTS.mkdir(exist_ok=True)
    res.to_csv(REPORTS / "model_c_results.csv", index=False)
    print(res.to_string(index=False))

    per = pd.DataFrame({"label": LABELS, "captions_with_label": Y.sum(0)})
    for k, v in P.items():
        per[k] = [round(f1_score(Y[mask, j], v[mask, j], zero_division=0), 3) for j in range(len(LABELS))]
    per["keyword rules"] = [round(f1_score(Y[mask, j], rules(texts)[mask, j], zero_division=0), 3) for j in range(len(LABELS))]
    per.to_csv(REPORTS / "model_c_per_label.csv", index=False)
    print(per.to_string(index=False))

    if reuse:
        return
    # the trained model used from here on: the best trained method by micro-F1, refit on all captions
    trained = res[res["method"].isin(P)].sort_values("micro_f1", ascending=False)
    best = trained.iloc[0]["method"]
    posts = pd.read_csv(HERE / "datasets" / "posts_dataset.csv")[["shortcode", "handle", "caption"]]
    allcap = posts["caption"].fillna("").astype(str).str.replace(r"#\S+", "", regex=True).str.strip()
    if best == "fine-tuned multilingual transformer":
        prob = finetune(texts.tolist(), Y, allcap.tolist(), ft_model, save=MODELS / "caption_model")
    elif best == "TF-IDF + logistic regression":
        prob = tfidf_lr(texts, allcap, Y)
    else:
        prob = emb_lr(E, embed(allcap.tolist()), Y)
    pred = at_least_one(prob)
    out = posts[["shortcode", "handle"]].copy()
    out["caption_labels_model"] = ["|".join(lab for lab, v in zip(LABELS, row) if v) for row in pred]
    for j, lab in enumerate(LABELS):
        out[f"is_{lab}"] = pred[:, j]
    out["model"] = best
    out.to_csv(HERE / "datasets" / "captions_predicted.csv", index=False)
    print(f"\nbest trained: {best} -> datasets/captions_predicted.csv ({len(out)} posts)")


if __name__ == "__main__":
    main(next((a for a in sys.argv[1:] if a != "--reuse"), ENCODER), "--reuse" in sys.argv)
