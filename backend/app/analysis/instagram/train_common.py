"""Shared by the three training scripts (picture quality, video quality, memorability).

For every picture or video it makes two sets of numbers (feature extraction):
  - our own 12 measurements (sharpness, light, colour, noise, motion ...), and
  - the frozen vision network's reading of it (cnn_features.py): the mean and spread of every channel of
    all four ResNet layers, for each network asked for, so every choice below can be compared without re-reading.

Then, using only data and the choosing (validation) set, never the test set:
  1. Split 70 / 15 / 15 (train / choosing / test), STRATIFIED on the score, so every part has the same mix of
     low, middle and high scores (deciles; fewer groups only when the data is too small for ten).
  2. Network and layers (ablation): ResNet-18 vs ResNet-50 and the layer sets in cnn_features.LAYER_SETS,
     compared with ridge regression on the choosing set.
  3. Model and sample weights: ridge / SVR on the chosen network features, and a Random Forest on our 12
     measurements only, each with no weights, square-root-inverse or inverse frequency weights (rare scores
     count more; Yang et al., "Delving into Deep Imbalanced Regression", ICML 2021). Bins for the weights come
     from the Freedman-Diaconis / Sturges rule (numpy 'auto'), not a typed-in number.
  4. The winner is refitted on train + choosing and checked ONCE on the test set: SRCC, PLCC, MAE overall and
     per score group, next to the measurements-only Random Forest baseline.
Guards (learned from the training data only): ridge / SVR inputs are clipped to their training range, and every
model's scores to the range of the training ratings, so no input can push a score off the scale.
The full report is printed and saved next to the model as <name>_report.json.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import pearsonr, spearmanr
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from . import cnn_features, media_features as mf

MODELS = Path(__file__).parent / "models"
RF_BASELINE = "random_forest_on_our_measurements"
WEIGHTINGS = ("none", "sqrt_inverse", "inverse")
REPORT_GROUPS = 5            # equal-width score groups in the error report (the 1-5 scale -> five ranges)


# ------------------------------------------------------------------ the two feature sets
def _hand_image(path: str):
    try:
        return mf.to_vector(mf.image_features(Image.open(path)), mf.IMAGE_FEATURES)
    except Exception:  # noqa: BLE001
        return None


def _hand_video(path: str):
    try:
        res = mf.video_features(path)
        return None if res is None else mf.to_vector(res[0], mf.VIDEO_FEATURES)
    except Exception:  # noqa: BLE001
        return None


def _as_list(backbone) -> list[str]:
    if isinstance(backbone, str):
        return [b.strip() for b in backbone.split(",") if b.strip()]
    return list(backbone)


def _read_network(paths: list[str], keep: list[int], kind: str, backbone: str, max_side: int, pretrained: bool):
    ext = cnn_features.get_extractor(backbone, max_side, pretrained, cnn_features.ALL_LAYERS)
    vecs: list[np.ndarray | None] = [None] * len(paths)
    t0 = time.time()
    for n, i in enumerate(keep, 1):
        try:
            vecs[i] = ext.image_vector(Image.open(paths[i])) if kind == "image" else ext.frames_vector(mf.read_video(paths[i])[0])
        except Exception:  # noqa: BLE001
            vecs[i] = None
        if n % 100 == 0:
            rate = n / (time.time() - t0)
            print(f"  {backbone}: network read {n}/{len(keep)} ({rate:.1f}/s, about {(len(keep) - n) / rate / 60:.0f} min left)", flush=True)
    return vecs


def extract(paths: list[str], y: list[float], kind: str, features: str, backbone, max_side: int,
            pretrained: bool, workers: int, cache: str | None) -> dict[str, Any]:
    """Our measurements (always) and, when features == 'cnn', every network's vector (all four layers) per item.

    `backbone` is one name or several ("resnet18,resnet50"). With `cache`, everything read is saved, and a later run
    only reads what is missing (for example a second network).
    """
    backbones = _as_list(backbone) if features == "cnn" else []
    z = None
    if cache and Path(cache).exists():
        z = np.load(cache, allow_pickle=True)
        if list(z["paths"]) != paths:
            z = None
    fn = _hand_image if kind == "image" else _hand_video
    hand_saved = z is not None and "features_version" in z.files and int(z["features_version"]) == mf.FEATURES_VERSION
    if hand_saved:
        hand = [None if np.isnan(r).any() else list(r) for r in z["hand"]]
        print(f"using saved measurements from {cache}")
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            hand = list(pool.map(fn, paths, chunksize=8))
    keep = [i for i, v in enumerate(hand) if v is not None]
    cnn: dict[str, list] = {}
    for b in backbones:
        if z is not None and f"cnn_{b}" in z.files:
            m = z[f"cnn_{b}"]
            cnn[b] = [None if np.isnan(r).any() else r for r in m]
            print(f"using saved {b} features from {cache}")
        else:
            cnn[b] = _read_network(paths, keep, kind, b, max_side, pretrained)
    for b in backbones:
        keep = [i for i in keep if cnn[b][i] is not None]
    if cache:
        dim_h = len(mf.IMAGE_FEATURES if kind == "image" else mf.VIDEO_FEATURES)
        save = {"paths": np.array(paths), "y": np.array(y), "features_version": np.array(mf.FEATURES_VERSION),
                "hand": np.array([v if v is not None else [np.nan] * dim_h for v in hand], dtype=float)}
        for b in backbones:
            dim = next(v.shape[0] for v in cnn[b] if v is not None)
            save[f"cnn_{b}"] = np.array([v if v is not None else np.full(dim, np.nan) for v in cnn[b]], dtype=np.float32)
        if z is not None:
            for f in z.files:
                if f.startswith("cnn_") and f not in save:
                    save[f] = z[f]
        np.savez(cache, **save)
        print(f"saved features to {cache} (so changing the model later needs no re-reading)")
    return {
        "paths": [paths[i] for i in keep], "y": np.array([y[i] for i in keep], dtype=float),
        "hand": np.array([hand[i] for i in keep], dtype=float),
        "cnn": {b: np.array([cnn[b][i] for i in keep], dtype=np.float32) for b in backbones} or None,
        "kind": kind,
    }


# ------------------------------------------------------------------ split, weights, scores
def stratified_split(y: np.ndarray, seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """70 / 15 / 15 with every part holding the same mix of scores (deciles of the score).

    If the data is too small for ten groups in every part, fewer groups are tried; 0 groups means a plain random split.
    """
    idx = np.arange(len(y))
    ranks = pd.Series(y).rank(method="first").to_numpy()
    for q in range(10, 1, -1):
        groups = pd.qcut(ranks, q, labels=False)
        try:
            tr, hold = train_test_split(idx, test_size=0.3, stratify=groups, random_state=seed)
            va, te = train_test_split(hold, test_size=0.5, stratify=groups[hold], random_state=seed)
            return tr, va, te, q
        except ValueError:
            continue
    tr, hold = train_test_split(idx, test_size=0.3, random_state=seed)
    va, te = train_test_split(hold, test_size=0.5, random_state=seed)
    return tr, va, te, 0


def sample_weights(y: np.ndarray, scheme: str) -> np.ndarray | None:
    """How much each training item counts: rarer scores count more. Mean weight is 1.

    The score range is cut into bins by numpy's 'auto' rule (the larger of the Freedman-Diaconis and Sturges bin counts,
    so it still works when many scores are identical); an item's weight is 1 / (items in its bin)
    ('inverse') or 1 / sqrt(items in its bin) ('sqrt_inverse'). 'none' = every item counts the same.
    """
    if scheme == "none":
        return None
    edges = np.histogram_bin_edges(y, bins="auto")
    if len(edges) < 3:
        return None
    which = np.clip(np.digitize(y, edges[1:-1]), 0, len(edges) - 2)
    counts = np.bincount(which, minlength=len(edges) - 1).astype(float)
    w = 1.0 / counts[which] ** (1.0 if scheme == "inverse" else 0.5)
    return w / w.mean()


def _scores(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    return float(spearmanr(y, p).correlation), float(pearsonr(y, p)[0])


def group_errors(y: np.ndarray, p: np.ndarray, lo: float, hi: float, n_groups: int = REPORT_GROUPS) -> list[dict[str, Any]]:
    """Mean absolute error inside each equal-width score range: shows whether low and high scores are predicted as well
    as the middle ones."""
    edges = np.linspace(lo, hi, n_groups + 1)
    which = np.clip(np.digitize(y, edges[1:-1]), 0, n_groups - 1)
    out = []
    for g in range(n_groups):
        m = which == g
        out.append({"range": f"{edges[g]:.2f}-{edges[g + 1]:.2f}", "n": int(m.sum()),
                    "mae": round(float(np.abs(y[m] - p[m]).mean()), 4) if m.any() else None})
    return out


def _balanced_mae(groups: list[dict[str, Any]]) -> float | None:
    vals = [g["mae"] for g in groups if g["mae"] is not None]
    return round(float(np.mean(vals)), 4) if vals else None


# ------------------------------------------------------------------ guards against inputs and outputs out of range
class FeatureRangeClip(BaseEstimator, TransformerMixin):
    """Clips every input to the range it had in the TRAINING data (learned in fit, nothing typed in).

    A straight-line model (ridge) carries an extreme input straight into an extreme score; clipping means it never
    has to extrapolate beyond what it was trained on. Trees (Random Forest) do not need it.
    """

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        self.min_, self.max_ = X.min(axis=0), X.max(axis=0)
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X):
        return np.clip(np.asarray(X, dtype=float), self.min_, self.max_)


class BoundedRegressor(BaseEstimator, RegressorMixin):
    """A model whose scores stay inside the range of the ratings it was trained on (e.g. KonIQ 1.10 - 4.31)."""

    def __init__(self, estimator=None):
        self.estimator = estimator

    def fit(self, X, y, sample_weight=None):
        y = np.asarray(y, dtype=float)
        self.lo_, self.hi_ = float(y.min()), float(y.max())
        self.n_features_in_ = np.asarray(X).shape[1]
        if sample_weight is None:
            self.estimator.fit(X, y)
        elif hasattr(self.estimator, "steps"):          # a pipeline: the weights go to its last step (ridge / SVR)
            self.estimator.fit(X, y, **{f"{self.estimator.steps[-1][0]}__sample_weight": sample_weight})
        else:
            self.estimator.fit(X, y, sample_weight=sample_weight)
        return self

    def predict(self, X):
        return np.clip(self.estimator.predict(X), self.lo_, self.hi_)


# ------------------------------------------------------------------ the candidate models
def _make(head: str, n_features: int, n_samples: int, seed: int) -> Any:
    if head == RF_BASELINE:
        inner = RandomForestRegressor(n_estimators=300, min_samples_leaf=3, n_jobs=-1, random_state=seed)
    elif head == "ridge_on_network_features":
        inner = make_pipeline(FeatureRangeClip(), StandardScaler(), RidgeCV(alphas=np.logspace(0, 5, 11)))
    elif head == "svr_on_network_features":
        inner = make_pipeline(FeatureRangeClip(), StandardScaler(),
                              PCA(n_components=max(2, min(256, n_features, n_samples - 1)), random_state=seed), SVR(C=10.0))
    else:
        raise ValueError(head)
    return BoundedRegressor(inner)


def _fit(model: Any, X: np.ndarray, y: np.ndarray, w: np.ndarray | None) -> Any:
    return model.fit(X, y, sample_weight=w)


def _features(data: dict[str, Any], backbone: str | None, layers) -> np.ndarray:
    """Network columns of the chosen layers, then our measurements."""
    if backbone is None:
        return data["hand"]
    cols = cnn_features.columns(backbone, cnn_features.ALL_LAYERS, layers, video=data.get("kind") == "video")
    return np.hstack([data["cnn"][backbone][:, cols], data["hand"]])


# ------------------------------------------------------------------ choosing and checking the model
def train_and_save(name: str, data: dict[str, Any], hand_names: list[str], meta: dict[str, Any], seed: int = 0,
                   force: str | None = None) -> dict[str, Any]:
    y, hand = data["y"], data["hand"]
    cnn = data.get("cnn")
    if isinstance(cnn, np.ndarray):                   # an older caller passing one network's (layers 2-4) matrix
        cnn = {meta.get("backbone") or "resnet50": cnn}
        data = {**data, "cnn": cnn}
        layer_sets = [cnn_features.DEFAULT_LAYERS]
    else:
        layer_sets = cnn_features.LAYER_SETS
    use_cnn = bool(cnn)
    n = len(y)
    tr, va, te, q = stratified_split(y, seed)
    if min(len(tr), len(va), len(te)) < 5:
        raise SystemExit(f"Only {n} items were usable: too few to train and check a model. Check the folder and scores file.")
    lo, hi = float(y.min()), float(y.max())
    print(f"{n} items: {len(tr)} train / {len(va)} choosing / {len(te)} test (stratified on the score, {q} groups)")

    # ---- step 2: which network and which layers (ridge, no weights, choosing set)
    ablation: list[dict[str, Any]] = []
    best_b, best_layers = None, None
    if use_cnn:
        for b in cnn:
            for layers in layer_sets:
                X = _features(data, b, layers)
                p = _fit(_make("ridge_on_network_features", X.shape[1], len(tr), seed), X[tr], y[tr], None).predict(X[va])
                s = _scores(y[va], p)[0]
                ablation.append({"backbone": b, "layers": "+".join(l.replace("layer", "") for l in layers),
                                 "n_features": int(X.shape[1]), "choosing_srcc": round(s, 4)})
                print(f"  ablation {b:9s} layers {ablation[-1]['layers']:8s} ({X.shape[1]:5d} numbers): choosing SRCC {s:.4f}", flush=True)
        top = max(ablation, key=lambda r: r["choosing_srcc"])
        best_b = top["backbone"]
        best_layers = tuple(f"layer{c}" for c in top["layers"].split("+"))

    # ---- step 3: which model and which weights (choosing set)
    heads = [RF_BASELINE] + (["ridge_on_network_features", "svr_on_network_features"] if use_cnn else [])
    X_net = _features(data, best_b, best_layers) if use_cnn else None
    grid: list[dict[str, Any]] = []
    for head in heads:
        X = hand if head == RF_BASELINE else X_net
        for scheme in (("none",) if force else WEIGHTINGS):
            w = sample_weights(y[tr], scheme)
            if scheme != "none" and w is None:
                continue
            p = _fit(_make(head, X.shape[1], len(tr), seed), X[tr], y[tr], w).predict(X[va])
            s = _scores(y[va], p)[0]
            grid.append({"head": head, "weights": scheme, "choosing_srcc": round(s, 4),
                         "choosing_balanced_mae": _balanced_mae(group_errors(y[va], p, lo, hi))})
            print(f"  {head:36s} weights {scheme:12s}: choosing SRCC {s:.4f}, balanced MAE {grid[-1]['choosing_balanced_mae']}", flush=True)
    pool = [g for g in grid if g["head"] == force] if force else grid
    win = max(pool, key=lambda g: g["choosing_srcc"])
    best, scheme = win["head"], win["weights"]

    # ---- step 4: refit on train + choosing, check once on the test set
    trva = np.concatenate([tr, va])

    def refit_and_test(head: str, sch: str):
        X = hand if head == RF_BASELINE else X_net
        m = _fit(_make(head, X.shape[1], len(trva), seed), X[trva], y[trva], sample_weights(y[trva], sch))
        p = m.predict(X[te])
        return m, p

    model, p_best = refit_and_test(best, scheme)
    srcc, plcc = _scores(y[te], p_best)
    _, p_base = refit_and_test(RF_BASELINE, "none")
    base_srcc, _ = _scores(y[te], p_base)
    groups = group_errors(y[te], p_best, lo, hi)
    report = {
        "n_items": int(n), "n_train": int(len(trva)), "n_test": int(len(te)), "stratified_groups": q,
        "srcc": round(srcc, 4), "plcc": round(plcc, 4), "mae": round(float(np.abs(y[te] - p_best).mean()), 4),
        "head": best, "weights": scheme, "backbone": best_b,
        "layers": list(best_layers) if best_layers else None,
        "baseline_measurements_only_srcc": round(base_srcc, 4),
        "test_error_by_score_group": groups,
        "baseline_error_by_score_group": group_errors(y[te], p_base, lo, hi),
        "ablation_network_and_layers": ablation, "choosing_set_models": grid,
        "choosing_set_srcc": {f"{g['head']} / {g['weights']}": g["choosing_srcc"] for g in grid},
        "label_min": lo, "label_max": hi,
    }
    if scheme != "none":                              # for the report only: the same model without weights, same test set
        _, p_plain = refit_and_test(best, "none")
        report["same_model_without_weights"] = {"srcc": round(_scores(y[te], p_plain)[0], 4),
                                                "error_by_score_group": group_errors(y[te], p_plain, lo, hi)}
    MODELS.mkdir(exist_ok=True)
    saved_meta = {**meta}
    if use_cnn:
        saved_meta["backbone"] = best_b
        saved_meta["layers"] = list(best_layers)
    joblib.dump({
        "model": model, "head": best, "feature_set": "handcrafted" if best == RF_BASELINE else "cnn",
        "hand_features": hand_names, "report": report, **saved_meta,
    }, MODELS / f"{name}.joblib")
    (MODELS / f"{name}_report.json").write_text(json.dumps({**report, "trained_on": meta.get("trained_on")}, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k not in ("choosing_set_models", "ablation_network_and_layers")}, indent=1))
    print(f"saved {MODELS / (name + '.joblib')} and {name}_report.json")
    return report


__all__ = ["extract", "train_and_save", "stratified_split", "sample_weights", "group_errors", "MODELS"]
