"""Combined review reasons = the team model (very precise) + Model A (finds more), with Model A's cut-offs
chosen on OUR 800 training labels only (5-fold GroupKFold by listing, same folds as train_review_model.py).

    ../../backend/.venv/bin/python tune_combined.py

Rule (decided before looking at the 150 person-checked test reviews):
  1. every reason the team model gives (its own 95% rule) is kept;
  2. a Model A reason is added when its probability >= t_praise (praise) or >= t_complaint (complaint);
  3. if one review gets the same reason as both praise and complaint, only one is kept:
     the team model's if it gave one, else the more likely one.
t_praise: the value with the best F1 on the out-of-fold predictions. t_complaint: the best F0.5 (precision counts
twice as much as recall), because complaints become gaps ("5 of 40 buyers complain about size"), so a wrong
complaint costs more than a missed one. Praise is only shown as a strength, so plain F1 is used there. They are saved into models/review_reasons/reasons.joblib and used
by the app (backend/app/analysis/daraz/reviews.py). The test on the 150 person-checked reviews is done once, after.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold

from train_review_model import HERE, OUT_MODEL, TEAM, encode, load, team_as_is, tfidf_lr, xlmr_lr

GRID = [round(x, 2) for x in np.arange(0.30, 0.96, 0.05)]


def combine(prob: np.ndarray, team: np.ndarray, labels: list[str], t_praise: float, t_complaint: float) -> np.ndarray:
    pos = np.array([lab.endswith("+") for lab in labels])
    pred = team.astype(bool) | np.where(pos, prob >= t_praise, prob >= t_complaint)
    pred = pred.astype(int)
    index = {lab: j for j, lab in enumerate(labels)}
    for lab, j in index.items():                      # same reason both + and -: keep one
        if not lab.endswith("+") or lab[:-1] + "-" not in index:
            continue
        k = index[lab[:-1] + "-"]
        both = (pred[:, j] == 1) & (pred[:, k] == 1)
        for i in np.where(both)[0]:
            if team[i, j] != team[i, k]:
                keep = j if team[i, j] else k
            else:
                keep = j if prob[i, j] >= prob[i, k] else k
            pred[i, k if keep == j else j] = 0
    return pred


def scores(Y: np.ndarray, P: np.ndarray, cols: np.ndarray) -> tuple[float, float, float]:
    y, p = Y[:, cols], P[:, cols]
    return (precision_score(y, p, average="micro", zero_division=0), recall_score(y, p, average="micro", zero_division=0),
            f1_score(y, p, average="micro", zero_division=0))


def main() -> None:
    d, labels, Y = load()
    texts = d["text"].astype(str).tolist()
    folds = list(GroupKFold(n_splits=5).split(texts, Y, d["item_id"].values))
    E = encode(texts, str(TEAM / "aspect_model"))
    prob = np.zeros(Y.shape)
    for tr, te in folds:                              # out-of-fold Model A probabilities (average method)
        pt = tfidf_lr([texts[i] for i in tr], [texts[i] for i in te], Y[tr])
        px = xlmr_lr(E[tr], Y[tr]).predict_proba(E[te])
        prob[te] = (pt + px) / 2
    team = team_as_is(texts, labels)
    pos = np.array([lab.endswith("+") for lab in labels])

    rows = []
    for tp in GRID:
        for tc in GRID:
            P = combine(prob, team, labels, tp, tc)
            rows.append({"t_praise": tp, "t_complaint": tc,
                         **dict(zip(["praise_p", "praise_r", "praise_f1"], scores(Y, P, pos))),
                         **dict(zip(["complaint_p", "complaint_r", "complaint_f1"], scores(Y, P, ~pos))),
                         "all_f1": f1_score(Y, P, average="micro", zero_division=0)})
    grid = pd.DataFrame(rows)
    grid["complaint_f05"] = 1.25 * grid.complaint_p * grid.complaint_r / (0.25 * grid.complaint_p + grid.complaint_r).replace(0, np.nan)
    grid = grid.fillna(0).round(3)
    best_p = grid.sort_values(["praise_f1", "t_praise"], ascending=[False, False]).iloc[0]["t_praise"]
    best_c = grid.sort_values(["complaint_f05", "t_complaint"], ascending=[False, False]).iloc[0]["t_complaint"]
    chosen = grid[(grid.t_praise == best_p) & (grid.t_complaint == best_c)].iloc[0]

    def line(name, P):
        return {"method": name, **dict(zip(["praise_p", "praise_r", "praise_f1"], scores(Y, P, pos))),
                **dict(zip(["complaint_p", "complaint_r", "complaint_f1"], scores(Y, P, ~pos))),
                "all_f1": f1_score(Y, P, average="micro", zero_division=0)}
    summary = pd.DataFrame([line("team model as-is", team), line("Model A alone (0.5)", (prob >= 0.5).astype(int)),
                            line(f"combined (praise {best_p}, complaints {best_c})", combine(prob, team, labels, best_p, best_c))]).round(3)
    (HERE / "reports").mkdir(exist_ok=True)
    grid.to_csv(HERE / "reports" / "model_a_combined_grid.csv", index=False)
    summary.to_csv(HERE / "reports" / "model_a_combined.csv", index=False)
    print(summary.to_string(index=False))
    print("chosen:", dict(chosen))

    import joblib  # SAFETY: our own file written by train_review_model.py
    path = OUT_MODEL / "reasons.joblib"
    bundle = joblib.load(path)
    bundle["combine"] = {"with_team": True, "t_praise": float(best_p), "t_complaint": float(best_c),
                         "chosen_on": "out-of-fold predictions on the 800 training labels (GroupKFold by listing); praise by F1, complaints by F0.5"}
    joblib.dump(bundle, path)
    print("saved cut-offs into", path)


if __name__ == "__main__":
    main()
