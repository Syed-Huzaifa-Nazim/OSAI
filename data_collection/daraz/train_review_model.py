"""Daraz Model A: jewellery review REASONS (what a review praises or complains about), trained on our labels.

    ../../backend/.venv/bin/python train_review_model.py            # all methods except the slow XLM-R fine-tune
    ../../backend/.venv/bin/python train_review_model.py --xlmr     # also fine-tune the team's XLM-R (slow on CPU)

Labels: labels/jewellery_review_labels.csv, 800 reviews (AI-drafted from the full text, person-checked sample),
13 jewellery reasons x praise / complaint (labels/REVIEW_LABEL_GUIDE.md). Reasons with fewer than MIN_COUNT examples
are folded into their nearest reason before training (stones- -> breakage-, stones+ / colour_fade+ -> quality+).

Methods compared, all tested on LISTINGS they never saw (5-fold GroupKFold by listing):
  majority            the two most common reasons for every review
  team model as-is    the team's XLM-R aspect model (electronics-heavy labels) mapped onto ours, its own 0.95 cut-off
  keyword rules       English + Roman Urdu word lists
  TF-IDF + LR         word and character n-grams, logistic regression per reason
  frozen XLM-R + LR   the team model's encoder unchanged, a small logistic regression per reason on top
  fine-tuned MiniLM   all weights trained (same recipe as Instagram Model C: weighted loss for rare reasons)
  fine-tuned XLM-R    the team model's encoder trained further on our reasons (--xlmr)
Writes reports/model_a_results.csv, reports/model_a_per_label.csv; the winner -> backend models/review_reasons/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold
from sklearn.multiclass import OneVsRestClassifier

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[1] / "Daraz_Model" / "model_package"
OUT_MODEL = HERE.parents[1] / "backend" / "app" / "analysis" / "daraz" / "models" / "review_reasons"
MINILM = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MIN_COUNT = 14
FOLD = {"stones-": "breakage-", "stones+": "quality+", "colour_fade+": "quality+"}

RULES = {
    "quality+": r"quality\s*(is\s*)?(very\s*)?(good|best|achi|acha|amazing|excellent|nice|10)|material\s*:?\s*(is\s*)?(good|nice|best|acha|achi|amazing|perfect|10|great)|good quality|best quality|achi quality",
    "quality-": r"(quality|material)\s*:?\s*(is\s*)?(not good|bad|low|bekar|bakwas|ghatiya|cheap|poor|worst|fazool|3rd|third)|low quality|bad quality|poor quality|cheap|fake|bekar|bakwas|ghatiya|third class",
    "design+": r"beautiful|pretty|pyar[aiy]|khoobsurat|khubsurat|cute|elegant|lovely|gorgeous|zabardast|design\s*:?\s*(is\s*)?(good|nice|best|beautiful|perfect)|style\s*:?\s*(good|nice|10|beautiful|awesome)",
    "design-": r"design\s*:?\s*(is\s*)?(not good|bad|worst|acha nahi)|style\s*:?\s*(bad|poor)",
    "as_pictured+": r"same as (shown|pic|picture)|as shown|jais[ae] (dikh|dekh)|jes[ai] (dikh|dekh|pic)|wais[ai] hi|wes[ai] hi|exactly (the )?same|same cheez",
    "as_pictured-": r"not (as|same as) (shown|pic)|different from|not like (the )?pic|picture se (different|alag)|w[ao]i?s[ai] (nahi|nhi|ni)|nahi? (mila|aya) jo|totally different",
    "wrong_or_missing-": r"wrong|missing|instead of|ordered .{0,30}(but|received|got)|mangw?ai? .{0,30}(bhej|aya|ai)|order .{0,25}(ki|kiya) .{0,30}(bhej|aya|ai)|only (got|received|one)|sirf (aik|ek|1)",
    "size_fit-": r"(too |bohat |bht |very )?(small|chot[aiy]|big|bar[aiy]|large|tight|loose)|size .{0,20}(not|nahi|ni|chot|bara|small)|fit nahi|fit nhi",
    "size_fit+": r"perfect size|size (is )?(perfect|good|theek|thik)|fit (well|ho)|fits",
    "breakage-": r"broken|broke|tooti|toota|tuti|tota|toot|damage|nikal gay?a|hook .{0,15}(missing|nahi|ni)|stone .{0,15}(gir|nikal|missing)",
    "breakage+": r"durability\s*:?\s*(is\s*)?(good|nice|10|fine|great|fantastic)|strong",
    "colour_fade-": r"black ho|kala ho|colou?r .{0,20}(utar|utr|fade|khrab|change|chala)|rang .{0,10}(utar|utr)|tarnish|fade",
    "price_value+": r"worth|reasonable|affordable|is price m|price k hisab|good price|best price|in budget|according to (the )?price",
    "price_value-": r"overpriced|expensive|mehng[aiy]|price .{0,15}(high|zyada|ziada|too much)|waste of money|paise? (zaya|waste)|money waste",
    "delivery+": r"fast delivery|delivery .{0,10}(fast|on time|jaldi|time pe|time par)|on time|jaldi (mil|aa)|quick delivery|delivered in \d",
    "delivery-": r"late|der se|delay|days baad|din (baad|bad)",
    "packaging+": r"pack(ing|aging|ed)\s*(was|is)?\s*(good|nice|achi|acha|amazing|secure|well)|safe(ly)? pack|good packing",
    "packaging-": r"pack(ing|aging)\s*(was|is)?\s*(bad|not good|bakwas|buri|poor)|no box|box nahi",
    "seller+": r"seller .{0,15}(good|cooperative|honest|nice|best|achi|acha)|thanks? (you )?(seller|saller)|recommended seller|cooperative",
    "seller-": r"fraud|scam|seller .{0,20}(not|nahi|ni|ignored|reply)|dishonest|no refund|return (nahi|ni|not)",
    "comfort+": r"light ?weight|comfortable|easy to wear|halk[ai]",
    "comfort-": r"heavy|allerg|pain|dard|itch|hurts|chubti|sharp|irritat",
}
TEAM_MAP = {"Quality": "quality", "Performance": "quality", "Authenticity": "quality", "Durability": "breakage",
            "As_Described": "as_pictured", "Size_Capacity": "size_fit", "Design_Comfort": "design", "Price": "price_value",
            "Delivery": "delivery", "Packaging": "packaging", "Seller": "seller"}


def load() -> tuple[pd.DataFrame, list[str], np.ndarray]:
    d = pd.read_csv(HERE / "labels" / "jewellery_review_labels.csv", dtype={"item_id": str})
    lab = d["labels"].fillna("none").map(lambda s: [FOLD.get(x.strip(), x.strip()) for x in s.split(";") if x.strip() and x.strip() != "none"])
    counts = pd.Series([x for xs in lab for x in xs]).value_counts()
    labels = sorted(counts[counts >= MIN_COUNT].index)
    Y = np.array([[int(l in xs) for l in labels] for xs in lab])
    return d, labels, Y


def cut(prob: np.ndarray, t: float = 0.5) -> np.ndarray:
    return (prob >= t).astype(int)


def tfidf_fit(tr, Y):
    w = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    c = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    X = hstack([w.fit_transform(tr), c.fit_transform(tr)]).tocsr()
    return w, c, OneVsRestClassifier(LogisticRegression(max_iter=3000, class_weight="balanced", C=4.0)).fit(X, Y)


def tfidf_lr(tr, te, Y):
    w, c, clf = tfidf_fit(tr, Y)
    return clf.predict_proba(hstack([w.transform(te), c.transform(te)]).tocsr())


def xlmr_lr(E, Y):
    return OneVsRestClassifier(LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0)).fit(E, Y)


def encode(texts: list[str], path: str) -> np.ndarray:
    """Mean-pooled sentence vectors from an encoder, unchanged (frozen)."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok, enc = AutoTokenizer.from_pretrained(path), AutoModel.from_pretrained(path).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 32):
            b = tok(texts[i:i + 32], padding=True, truncation=True, max_length=128, return_tensors="pt")
            h, m = enc(**b).last_hidden_state, b["attention_mask"].unsqueeze(-1).float()
            out.append(((h * m).sum(1) / m.sum(1)).numpy())
    return np.vstack(out)


def finetune(tr: list[str], Y: np.ndarray, te: list[str], name: str, epochs: int, lr_enc: float, save: Path | None = None,
             labels: list[str] | None = None) -> np.ndarray:
    """All weights trained; mean pooling + linear layer; BCE with positive weight = negatives / positives per reason."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    torch.manual_seed(0)
    torch.set_num_threads(8)
    tok, enc = AutoTokenizer.from_pretrained(name), AutoModel.from_pretrained(name)
    head = torch.nn.Linear(enc.config.hidden_size, Y.shape[1])
    params = list(enc.parameters()) + list(head.parameters())
    opt = torch.optim.AdamW([{"params": enc.parameters(), "lr": lr_enc}, {"params": head.parameters(), "lr": 1e-3}], weight_decay=0.01)
    steps = epochs * ((len(tr) + 15) // 16)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / (0.1 * steps)) * max(0.0, (steps - s) / steps))
    pos = Y.sum(0).clip(min=1)
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor((len(Y) - pos) / pos, dtype=torch.float32))

    def forward(texts):
        b = tok(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
        h, m = enc(**b).last_hidden_state, b["attention_mask"].unsqueeze(-1).float()
        return head((h * m).sum(1) / m.sum(1))

    Yt, rng = torch.tensor(Y, dtype=torch.float32), np.random.default_rng(0)
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
        prob = torch.cat([torch.sigmoid(forward(te[i:i + 64])) for i in range(0, len(te), 64)]).numpy() if te else np.zeros((0, Y.shape[1]))
    if save is not None:
        save.mkdir(parents=True, exist_ok=True)
        enc.save_pretrained(save)
        tok.save_pretrained(save)
        torch.save({"head": head.state_dict(), "labels": labels}, save / "head.pt")
    return prob


def team_as_is(texts: list[str], labels: list[str]) -> np.ndarray:
    sys.path.insert(0, str(TEAM))
    from review_analyzer import ReviewAnalyzer

    res = ReviewAnalyzer(TEAM).analyze(texts)["per_review"]
    P = np.zeros((len(texts), len(labels)), dtype=int)
    for i, r in enumerate(res):
        for x in r["reasons"]:
            ours = TEAM_MAP.get(x["aspect"])
            key = f"{ours}{'+' if x['polarity'] == 'positive' else '-'}" if ours else None
            if x["aspect"] == "Authenticity" and x["polarity"] == "positive":
                key = None
            if key in labels:
                P[i, labels.index(key)] = 1
    return P


def main(with_xlmr: bool = False) -> None:
    d, labels, Y = load()
    texts = d["text"].astype(str).tolist()
    groups = d["item_id"].values
    checked = d["checked_by_person"].fillna(False).astype(bool).values
    print(f"{len(d)} reviews, {len(labels)} reasons, {int(checked.sum())} person-checked")
    P: dict[str, np.ndarray] = {}
    common = Y.sum(0).argsort()[-2:]
    P["majority (two most common reasons)"] = np.zeros_like(Y)
    P["majority (two most common reasons)"][:, common] = 1
    P["team model as-is (mapped)"] = team_as_is(texts, labels)
    P["keyword rules"] = np.array([[int(bool(re.search(RULES.get(l, r"(?!)"), t, re.I))) for l in labels] for t in texts])
    folds = list(GroupKFold(n_splits=5).split(texts, Y, groups))
    E = encode(texts, str(TEAM / "aspect_model"))
    skip_ft = "--skip-finetune" in sys.argv
    keys = ["TF-IDF + logistic regression", "frozen XLM-R (team encoder) + LR", "average of TF-IDF and frozen XLM-R"]
    if not skip_ft:
        keys.append("fine-tuned MiniLM (Model C recipe)")
    for key in keys:
        P[key] = np.zeros_like(Y)
    if with_xlmr:
        P["fine-tuned XLM-R (from team model)"] = np.zeros_like(Y)
    for f, (tr, te) in enumerate(folds, 1):
        ttr, tte = [texts[i] for i in tr], [texts[i] for i in te]
        pt = tfidf_lr(ttr, tte, Y[tr])
        px = xlmr_lr(E[tr], Y[tr]).predict_proba(E[te])
        P["TF-IDF + logistic regression"][te] = cut(pt)
        P["frozen XLM-R (team encoder) + LR"][te] = cut(px)
        P["average of TF-IDF and frozen XLM-R"][te] = cut((pt + px) / 2)
        if not skip_ft:
            P["fine-tuned MiniLM (Model C recipe)"][te] = cut(finetune(ttr, Y[tr], tte, MINILM, epochs=10, lr_enc=4e-5))
        if with_xlmr:
            P["fine-tuned XLM-R (from team model)"][te] = cut(finetune(ttr, Y[tr], tte, str(TEAM / "aspect_model"), epochs=6, lr_enc=2e-5))
        print(f"fold {f} done", flush=True)

    rows, per = [], []
    for name, p in P.items():
        rows.append({"method": name,
                     "micro_f1": round(f1_score(Y, p, average="micro", zero_division=0), 3),
                     "macro_f1": round(f1_score(Y, p, average="macro", zero_division=0), 3),
                     "micro_precision": round(precision_score(Y, p, average="micro", zero_division=0), 3),
                     "micro_recall": round(recall_score(Y, p, average="micro", zero_division=0), 3),
                     "micro_f1_on_person_checked": round(f1_score(Y[checked], p[checked], average="micro", zero_division=0), 3) if checked.any() else None,
                     "n_reviews": len(Y), "n_person_checked": int(checked.sum())})
        for j, l in enumerate(labels):
            per.append({"method": name, "reason": l, "reviews_with_it": int(Y[:, j].sum()),
                        "f1": round(f1_score(Y[:, j], p[:, j], zero_division=0), 3)})
    res = pd.DataFrame(rows)
    old = HERE / "reports" / "model_a_results.csv"
    if skip_ft and old.exists():                      # the slow fine-tune's scores from the previous full run
        prev = pd.read_csv(old)
        res = pd.concat([res, prev[prev["method"].str.startswith("fine-tuned")]], ignore_index=True)
    res = res.sort_values("micro_f1", ascending=False)
    (HERE / "reports").mkdir(exist_ok=True)
    tag = "_with_xlmr" if with_xlmr else ""
    res.to_csv(HERE / "reports" / f"model_a_results{tag}.csv", index=False)
    per_df = pd.DataFrame(per).pivot(index=["reason", "reviews_with_it"], columns="method", values="f1").reset_index()
    old_per = HERE / "reports" / f"model_a_per_label{tag}.csv"
    if skip_ft and old_per.exists():
        prev = pd.read_csv(old_per)
        for col in [c for c in prev.columns if c.startswith("fine-tuned")]:
            per_df[col] = per_df["reason"].map(dict(zip(prev["reason"], prev[col])))
    per_df.to_csv(old_per, index=False)
    print(res.to_string(index=False))

    # The winner = best micro-F1 among the TRAINABLE methods (not the majority, rules or the team model as-is).
    trainable = res[~res["method"].str.startswith(("majority", "keyword", "team model"))].iloc[0]["method"]
    print("final model, trained on all 800 reviews:", trainable)
    import joblib
    OUT_MODEL.mkdir(parents=True, exist_ok=True)
    for f in OUT_MODEL.iterdir():                     # replace whatever an earlier run saved
        f.unlink()
    if trainable.startswith("fine-tuned MiniLM"):
        finetune(texts, Y, [], MINILM, epochs=10, lr_enc=4e-5, save=OUT_MODEL, labels=labels)
    else:
        w, c, clf_t = tfidf_fit(texts, Y)
        bundle = {"method": trainable, "labels": labels, "threshold": 0.5,
                  "tfidf": (w, c, clf_t) if "TF-IDF" in trainable else None,
                  "xlmr_lr": xlmr_lr(E, Y) if "XLM-R" in trainable else None,
                  "xlmr_encoder": "team aspect_model encoder, mean pooling, max 128 tokens"}
        joblib.dump(bundle, OUT_MODEL / "reasons.joblib")
    print("saved", OUT_MODEL)

if __name__ == "__main__":
    main("--xlmr" in sys.argv)
