"""Trains the video-quality model on LSVQ (videos rated by people).

    python -m app.analysis.instagram.train_video_quality \
        --videos ~/Downloads/lsvq --labels ~/Downloads/lsvq/train_labels.txt ~/Downloads/lsvq/labels_test.txt

Each label line looks like  yfcc-batch17/725.mp4, -1, -1, 76.84  : the video, two unused numbers, and the
rating (0 bad .. 100 excellent). Only videos you actually downloaded are used. Each video is read as 8 frames
by the vision network, plus our own measurements of light, sharpness and motion.
Slow on a laptop CPU (a few seconds per video); use --limit 100 first, and --cache so a second run is instant.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import cnn_features, media_features as mf
from .train_common import extract, train_and_save


def main(videos: str, labels: list[str], limit: int | None = None, workers: int = 4, features: str = "cnn",
         backbone: str = "resnet50", max_side: int = 384, cache: str | None = None, pretrained: bool = True):
    if features == "cnn" and not cnn_features.available():
        raise SystemExit("The vision network needs PyTorch. Install it (see RUN_ME.md) or use --features handcrafted.")
    root = Path(videos).expanduser()
    rows: dict[str, float] = {}
    for f in labels:
        for line in Path(f).expanduser().read_text().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2 and parts[0].endswith(".mp4") and (root / parts[0]).exists():
                rows[str(root / parts[0])] = float(parts[-1])
    items = list(rows.items())[:limit] if limit else list(rows.items())
    print(f"{len(items)} videos found with a rating")
    data = extract([p for p, _ in items], [y for _, y in items], "video", features, backbone, max_side, pretrained, workers, cache)
    print(f"{len(data['y'])} videos usable")
    return train_and_save("video_quality", data, mf.VIDEO_FEATURES, {
        "trained_on": "LSVQ", "kind": "video_quality", "scale": [0, 100], "backbone": backbone if features == "cnn" else None,
        "max_side": max_side, "pretrained": pretrained})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", required=True); ap.add_argument("--labels", nargs="+", required=True)
    ap.add_argument("--limit", type=int); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--features", choices=["cnn", "handcrafted"], default="cnn")
    ap.add_argument("--backbone", default="resnet50",
                    help="one network or several to compare, e.g. resnet18,resnet50 (choices: " + ", ".join(cnn_features.BACKBONES) + ")")
    ap.add_argument("--max-side", type=int, default=384); ap.add_argument("--cache")
    a = ap.parse_args()
    main(a.videos, a.labels, a.limit, a.workers, a.features, a.backbone, a.max_side, a.cache)
