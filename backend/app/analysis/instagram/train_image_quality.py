"""Trains the picture-quality model on KonIQ-10k (10,073 pictures rated by about 120 people each).

    python -m app.analysis.instagram.train_image_quality \
        --images ~/Downloads/koniq_images --scores ~/Downloads/koniq10k_scores_and_distributions.tab

--scores is the small .tab/.csv file (columns image_name, c1..c5, c_total, MOS, SD ...). MOS is the average
rating from 1 (bad) to 5 (excellent). Needs PyTorch for the vision network (see RUN_ME.md);
use --features handcrafted to train without it (weaker). Use --limit 300 first to check everything runs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import cnn_features, media_features as mf
from .train_common import extract, train_and_save


def main(images: str, scores: str, limit: int | None = None, workers: int = 4, features: str = "cnn",
         backbone: str = "resnet50", max_side: int = 512, cache: str | None = None, pretrained: bool = True):
    if features == "cnn" and not cnn_features.available():
        raise SystemExit("The vision network needs PyTorch. Install it (see RUN_ME.md) or use --features handcrafted.")
    df = pd.read_csv(scores, sep=None, engine="python")
    df.columns = [str(c).strip().strip('"').lower() for c in df.columns]
    if "image_name" not in df.columns or "mos" not in df.columns:
        raise SystemExit(f"Expected columns image_name and MOS in the scores file, found: {list(df.columns)[:8]}")
    root = Path(images).expanduser()
    rows = [(str(root / str(n).strip().strip('"')), float(m)) for n, m in zip(df["image_name"], df["mos"]) if (root / str(n).strip().strip('"')).exists()]
    if limit:
        rows = rows[:limit]
    print(f"{len(rows)} pictures found (of {len(df)} in the scores file)")
    data = extract([r[0] for r in rows], [r[1] for r in rows], "image", features, backbone, max_side, pretrained, workers, cache)
    print(f"{len(data['y'])} pictures usable")
    return train_and_save("image_quality", data, mf.IMAGE_FEATURES, {
        "trained_on": "KonIQ-10k", "kind": "image_quality", "scale": [1, 5], "backbone": backbone if features == "cnn" else None,
        "max_side": max_side, "pretrained": pretrained})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True); ap.add_argument("--scores", required=True)
    ap.add_argument("--limit", type=int); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--features", choices=["cnn", "handcrafted"], default="cnn")
    ap.add_argument("--backbone", default="resnet50",
                    help="one network or several to compare, e.g. resnet18,resnet50 (choices: " + ", ".join(cnn_features.BACKBONES) + ")")
    ap.add_argument("--max-side", type=int, default=512); ap.add_argument("--cache")
    a = ap.parse_args()
    main(a.images, a.scores, a.limit, a.workers, a.features, a.backbone, a.max_side, a.cache)
