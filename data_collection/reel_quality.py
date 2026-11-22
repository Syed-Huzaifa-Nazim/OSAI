"""Reel picture quality with the app's own trained models (backend media_scoring), from the saved reel files.

  ../backend/.venv/bin/python reel_quality.py

Same scoring as the app: frames spread over the reel are scored with the KonIQ-10k picture-quality model (1 poor .. 5
excellent) and averaged = reel_quality; the LSVQ video model (0 .. 100) and the LaMem memorability model on the middle
frame are added when those trained models are present. Writes data/reel_parts/quality.csv (resumable).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
from app.analysis.instagram import media_features as mf  # noqa: E402
from app.analysis.instagram import media_scoring as ms  # noqa: E402

OUT = HERE / "data" / "reel_parts" / "quality.csv"


def main() -> None:
    posts = pd.read_csv(HERE / "datasets" / "posts_dataset.csv")
    codes = [c for c in posts.loc[posts["format"] == "reel", "shortcode"] if (HERE / "data" / "reels" / f"{c}.mp4").exists()]
    done = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["shortcode"])
    todo = [c for c in codes if c not in set(done["shortcode"])]
    print({k: v["problem"] for k in ms.KINDS if (v := ms.load(k)) and v.get("problem")} or "models ready", flush=True)
    print(f"{len(done)} done, {len(todo)} to do", flush=True)
    rows = []
    for k, c in enumerate(todo, 1):
        row = {"shortcode": c, "reel_quality": None, "video_quality": None, "memorability": None}
        try:
            read = mf.read_video(str(HERE / "data" / "reels" / f"{c}.mp4"))
            if read is not None:
                frames = read[0]
                row["video_quality"] = ms._predict_video(frames, mf._video_stats(*read))
                per = [v for f in frames if (v := ms._predict_image("image_quality", f, mf.image_features(f))) is not None]
                row["reel_quality"] = float(np.mean(per)) if per else None
                mid = frames[len(frames) // 2]
                row["memorability"] = ms._predict_image("memorability", mid, mf.image_features(mid))
        except Exception as exc:  # noqa: BLE001 - one broken file must not stop the rest
            print(f"  {c}: {exc}", flush=True)
        rows.append(row)
        if k % 25 == 0 or k == len(todo):
            done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
            done.to_csv(OUT, index=False)
            rows = []
            print(f"  quality {k}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()
