"""Model D: picture tags learned from the person-checked pictures (labels/picture_check_300.xlsx).

  .venv/bin/python train_picture_model.py

Method: frozen CLIP ViT-B-32 picture features (no fine-tuning, CPU only) + a logistic-regression head per tag.
Tested shop by shop (GroupKFold over shops: a shop's pictures are never in both training and test), and compared with
  - majority class   (always guess the most common answer)
  - CLIP zero-shot    (the drafts in pictures_tags.csv, no training)
Only tags the person actually corrected are trained (jewellery_shown, face).
Writes: models/picture_heads.joblib, labels/pictures_tags_model.csv (all pictures), reports/model_d_results.csv
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold

HERE = Path(__file__).resolve().parent
LABELS, MODELS, REPORTS = HERE / "labels", HERE / "models", HERE / "reports"
EMB = HERE / "data" / "clip_embeddings.npz"
TAGS = {"jewellery_shown": "correct_jewellery_shown", "face": "correct_face"}
TYPO = {"dsiplayed": "displayed", "dispalyed": "displayed", "display": "displayed", "in-hand": "in_hand"}


def embeddings(codes: list[str]) -> dict[str, np.ndarray]:
    """CLIP picture features for every picture, computed once and cached."""
    if EMB.exists():
        z = np.load(EMB, allow_pickle=True)
        cached = dict(zip(z["codes"], z["vecs"]))
        if set(codes) <= set(cached):
            return cached
    import open_clip

    model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
    model.eval()
    vecs = []
    with torch.no_grad():
        for i in range(0, len(codes), 32):
            imgs = torch.stack([preprocess(Image.open(HERE / "data" / "media" / f"{c}.jpg").convert("RGB")) for c in codes[i:i + 32]])
            f = model.encode_image(imgs)
            vecs.append((f / f.norm(dim=-1, keepdim=True)).numpy())
            print(f"  features {min(i + 32, len(codes))}/{len(codes)}", flush=True)
    vecs = np.concatenate(vecs)
    np.savez(EMB, codes=np.array(codes), vecs=vecs)
    return dict(zip(codes, vecs))


def checked_labels() -> pd.DataFrame:
    p = pd.read_excel(LABELS / "picture_check_300.xlsx", sheet_name="check")
    for tag, col in TAGS.items():
        fix = p[col].where(p[col].notna()).astype("string").str.strip().str.lower().replace(TYPO)
        p[f"{tag}_true"] = fix.fillna(p[tag].astype(str))           # empty yellow cell = the draft was right
    return p


def main() -> None:
    tags = pd.read_csv(LABELS / "pictures_tags.csv")
    emb = embeddings(tags["shortcode"].tolist())
    p = checked_labels()
    X = np.stack([emb[c] for c in p["shortcode"]])
    groups = p["handle"].to_numpy()
    rows, heads = [], {}
    for tag in TAGS:
        y = p[f"{tag}_true"].to_numpy()
        pred = np.empty_like(y, dtype=object)
        for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
            clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0).fit(X[tr], y[tr])
            pred[te] = clf.predict(X[te])
        majority = np.full_like(y, pd.Series(y).mode()[0], dtype=object)
        for name, guess in [("majority class", majority), ("CLIP zero-shot (drafts)", p[tag].astype(str).to_numpy()),
                            ("CLIP + trained head (Model D)", pred)]:
            rows.append({"tag": tag, "method": name, "accuracy": round(accuracy_score(y, guess), 3),
                         "macro_f1": round(f1_score(y, guess, average="macro", zero_division=0), 3), "n_pictures": len(y),
                         "n_shops": len(set(groups))})
        heads[tag] = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0).fit(X, y)   # final head: all 300
        print(pd.crosstab(pd.Series(y, name="true"), pd.Series(pred, name="Model D"), dropna=False).to_string(), "\n")

    res = pd.DataFrame(rows)
    REPORTS.mkdir(exist_ok=True)
    MODELS.mkdir(exist_ok=True)
    res.to_csv(REPORTS / "model_d_results.csv", index=False)
    joblib.dump({"backbone": "open_clip ViT-B-32 laion2b_s34b_b79k", "heads": heads}, MODELS / "picture_heads.joblib")
    print(res.to_string(index=False))

    # tag every picture with the trained heads; person-checked pictures keep the person's answer
    out = tags.copy()
    Xall = np.stack([emb[c] for c in out["shortcode"]])
    truth = p.set_index("shortcode")
    for tag, clf in heads.items():
        out[f"{tag}_model"] = clf.predict(Xall)
        out[f"p_{tag}_model"] = clf.predict_proba(Xall).max(1).round(3)
        out[f"{tag}_verified"] = out["shortcode"].map(truth[f"{tag}_true"])
    out["checked_by_person"] = out["shortcode"].isin(truth.index)
    out.to_csv(LABELS / "pictures_tags_model.csv", index=False)
    print(f"\nTagged {len(out)} pictures -> labels/pictures_tags_model.csv")


if __name__ == "__main__":
    main()
