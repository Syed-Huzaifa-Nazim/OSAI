"""Trains the memorability model on LaMem (about 60,000 pictures with memorability scores).

    python -m app.analysis.instagram.train_memorability --images ~/Downloads/lamem/images --scores ~/Downloads/lamem/splits/train_1.txt

The scores file has one picture per line: the file name, then the score (space or comma separated).
Memorability depends on what is in a picture, so the vision network matters most here. Use --limit 20000
(it is a large dataset) and --cache so a second run is instant.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import cnn_features, media_features as mf
from .train_common import extract, train_and_save


def main(images: str, scores: str, limit: int | None = None, workers: int = 4, features: str = "cnn",
         backbone: str = "resnet50", max_side: int = 384, cache: str | None = None, pretrained: bool = True):
    if features == "cnn" and not cnn_features.available():
        raise SystemExit("The vision network needs PyTorch. Install it (see RUN_ME.md) or use --features handcrafted.")
    root = Path(images).expanduser()
    rows = []
    for line in Path(scores).expanduser().read_text().splitlines():
        parts = line.replace(",", " ").split()
        if len(parts) >= 2:
            try:
                score = float(parts[1])
            except ValueError:
                continue
            if (root / parts[0]).exists():
                rows.append((str(root / parts[0]), score))
    if limit:
        rows = rows[:limit]
    print(f"{len(rows)} pictures found with a score")
    data = extract([r[0] for r in rows], [r[1] for r in rows], "image", features, backbone, max_side, pretrained, workers, cache)
    return train_and_save("memorability", data, mf.IMAGE_FEATURES, {
        "trained_on": "LaMem", "kind": "memorability", "scale": [0, 1], "backbone": backbone if features == "cnn" else None,
        "max_side": max_side, "pretrained": pretrained})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True); ap.add_argument("--scores", required=True)
    ap.add_argument("--limit", type=int); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--features", choices=["cnn", "handcrafted"], default="cnn")
    ap.add_argument("--backbone", default="resnet50",
                    help="one network or several to compare, e.g. resnet18,resnet50 (choices: " + ", ".join(cnn_features.BACKBONES) + ")")
    ap.add_argument("--max-side", type=int, default=384); ap.add_argument("--cache")
    a = ap.parse_args()
    main(a.images, a.scores, a.limit, a.workers, a.features, a.backbone, a.max_side, a.cache)
