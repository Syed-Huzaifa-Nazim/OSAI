"""Scores each post's picture or video with the models we trained.

  image_quality  trained on KonIQ-10k people's quality ratings (1 poor .. 5 excellent): photos and carousel covers
  video_quality  trained on LSVQ people's quality ratings (0 .. 100): videos and reels
  memorability   trained on LaMem memorability scores (0 .. 1): the picture, or a video's middle frame

How a score is made (see cnn_features.py and train_common.py): a vision network reads the picture, and a model
we trained on people's ratings turns what it saw into a score. A model that has not been trained yet (no file in
models/) is skipped, and the app says so. Pictures are fetched with the same allow-listed, size-capped helper the
media proxy uses, right after scraping, while Instagram's links are alive. Nothing is stored.
"""
from __future__ import annotations

import io
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from PIL import Image

from . import cnn_features, media_features as mf

logger = logging.getLogger("optistratix.analysis.media")

MODELS = Path(__file__).parent / "models"
KINDS = {
    "image_quality": {"label": "Picture quality", "scale": "1 (poor) to 5 (excellent)", "noun": "picture"},
    "video_quality": {"label": "Video quality", "scale": "0 (poor) to 100 (excellent)", "noun": "video"},
    "memorability": {"label": "Memorability", "scale": "0 to 1 (higher = easier to remember)", "noun": "picture"},
    "reel_quality": {"label": "Reel picture quality", "scale": "1 (poor) to 5 (excellent)", "noun": "frame of each reel"},
}
# A score made with another kind's model: reels have no trained video model, so frames spread over each reel are
# scored with the picture model (KonIQ-10k) and averaged. It sees how each frame looks, not camera shake or cuts.
DERIVED = {"reel_quality": "image_quality"}
HEAD_NAMES = {
    "ridge_on_network_features": "ridge regression",
    "svr_on_network_features": "support vector regression",
    "random_forest_on_our_measurements": "Random Forest",
}
MAX_VIDEOS_PER_ACCOUNT = 10     # an engineering limit: videos are big downloads
WORKERS = 4
_cache: dict[str, dict[str, Any] | None] = {}


def load(kind: str) -> dict[str, Any] | None:
    """The trained model, or None if it is missing or cannot be used here."""
    if kind in DERIVED:
        return load(DERIVED[kind])
    if kind not in _cache:
        p = MODELS / f"{kind}.joblib"
        m = None
        if p.exists():
            try:
                m = joblib.load(p)
                if m.get("feature_set") == "cnn" and not cnn_features.available():
                    m["problem"] = "needs PyTorch (pip install torch torchvision)"
            except Exception as exc:  # noqa: BLE001 - e.g. saved with another scikit-learn version
                logger.warning("Could not load %s (%s): retrain it.", p.name, exc)
                m = {"problem": f"could not be loaded ({exc}); retrain it"}
        _cache[kind] = m
    return _cache[kind]


def reset_cache() -> None:
    _cache.clear()


def _usable(kind: str) -> bool:
    m = load(kind)
    return bool(m) and not m.get("problem") and "model" in m


def describe(kind: str) -> str:
    m = load(kind)
    noun = KINDS[kind]["noun"]
    if m["feature_set"] == "cnn":
        weights = m.get("report", {}).get("weights", "none")
        extra = "" if weights in (None, "none") else ", with rare scores weighted more during training"
        return (f"a {m['backbone']} vision network (pre-trained on general photos) reads each {noun}, and a "
                f"{HEAD_NAMES.get(m['head'], m['head'])} we trained on {m['trained_on']} turns what it sees into a score{extra}")
    return f"simple measurements of the {noun} (sharpness, light, colour, noise) and a Random Forest we trained on {m['trained_on']}"


def status() -> dict[str, dict[str, Any]]:
    """Which models exist and work, and how well they did on ratings they had not seen."""
    out = {}
    for kind, meta in KINDS.items():
        m = load(kind)
        out[kind] = {**meta, "available": _usable(kind)}
        if m and m.get("problem"):
            out[kind]["problem"] = m["problem"]
        if _usable(kind):
            rep = m["report"]
            out[kind].update(trained_on=m.get("trained_on"), n_train=rep["n_train"], srcc=rep["srcc"], description=describe(kind),
                             baseline_srcc=rep.get("baseline_measurements_only_srcc"))
    return out


def any_available() -> bool:
    return any(_usable(k) for k in KINDS)


def unavailable_reason() -> str:
    problems = [f"{KINDS[k]['label']} model {m['problem']}" for k in KINDS if k not in DERIVED and (m := load(k)) and m.get("problem")]
    if problems:
        return "; ".join(problems) + "."
    return ("The picture and video models have not been trained yet. Run the training scripts "
            "(train_image_quality, train_video_quality, train_memorability) and restart.")


# ------------------------------------------------------------------ scoring one picture or video
def _extractor(m: dict[str, Any]):
    if m.get("feature_set") != "cnn":
        return None
    # the network and layers that won on the choosing set when this model was trained (older models: layers 2-4)
    return cnn_features.get_extractor(m["backbone"], m["max_side"], m.get("pretrained", True),
                                      tuple(m.get("layers") or cnn_features.DEFAULT_LAYERS))


def _predict_image(kind: str, img: Image.Image, hand: dict[str, float]) -> float | None:
    if not _usable(kind):
        return None
    m = load(kind)
    ext, hv = _extractor(m), mf.to_vector(hand, m["hand_features"])
    x = hv if ext is None else np.concatenate([ext.image_vector(img), hv])
    return float(m["model"].predict([x])[0])


def _predict_video(frames: list[Image.Image], hand: dict[str, float]) -> float | None:
    if not _usable("video_quality"):
        return None
    m = load("video_quality")
    ext, hv = _extractor(m), mf.to_vector(hand, m["hand_features"])
    x = hv if ext is None else np.concatenate([ext.frames_vector(frames), hv])
    return float(m["model"].predict([x])[0])


def _download(url: str, limit: int) -> bytes | None:
    """The bytes at an Instagram media link, or None. Uses the media proxy's own safe fetcher."""
    from app.scrapers.instagram import media as instagram_media

    try:
        _, _, _, chunks = instagram_media.open_stream(url)
        buf, size = io.BytesIO(), 0
        for chunk in chunks:
            size += len(chunk)
            if size > limit:
                return None
            buf.write(chunk)
        return buf.getvalue()
    except Exception as exc:  # noqa: BLE001 - one dead link must not stop the analysis
        logger.info("Could not fetch %s: %s", url[:80], exc)
        return None


def _score_one(kind: str, url: str) -> dict[str, float | None]:
    out: dict[str, float | None] = {k: None for k in KINDS}
    if not url:
        return out
    try:
        if kind == "video":
            data = _download(url, 40_000_000)
            if data is None:
                return out
            fd, path = tempfile.mkstemp(suffix=".mp4")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                read = mf.read_video(path)
            finally:
                os.unlink(path)
            if read is None:
                return out
            frames = read[0]
            out["video_quality"] = _predict_video(frames, mf._video_stats(*read))
            if _usable("image_quality"):
                per_frame = [v for f in frames if (v := _predict_image("image_quality", f, mf.image_features(f))) is not None]
                out["reel_quality"] = float(np.mean(per_frame)) if per_frame else None
            mid = frames[len(frames) // 2]
            out["memorability"] = _predict_image("memorability", mid, mf.image_features(mid))
        else:
            data = _download(url, 12_000_000)
            if data is None:
                return out
            img = Image.open(io.BytesIO(data))
            hand = mf.image_features(img)
            out["image_quality"] = _predict_image("image_quality", img, hand)
            out["memorability"] = _predict_image("memorability", img, hand)
    except Exception as exc:  # noqa: BLE001
        logger.info("Could not score %s: %s", url[:80], exc)
    return out


def score_posts(df: pd.DataFrame, max_videos: int = MAX_VIDEOS_PER_ACCOUNT) -> tuple[pd.DataFrame, dict[str, int]]:
    """Adds image_quality / video_quality / memorability columns (NaN where not scored) to a posts table."""
    scores = pd.DataFrame(np.nan, index=df.index, columns=list(KINDS))
    stats = {"posts": int(len(df)), "scored": 0, "failed": 0, "videos_skipped": 0}
    if not any_available() or df.empty:
        return scores, stats
    is_video = df["media_type"].fillna("").astype(str).str.lower().eq("video")
    keep_videos = set(df[is_video].sort_values("when", ascending=False).head(max_videos).index)
    stats["videos_skipped"] = int(is_video.sum() - len(keep_videos))
    jobs = [(i, "video" if is_video[i] else "image", df.at[i, "media_url"]) for i in df.index if (not is_video[i]) or i in keep_videos]
    # the network is not thread-safe to build twice at once: build it here, then score in a few threads
    for k in KINDS:
        if _usable(k) and (ext := _extractor(load(k))) is not None:
            _ = ext
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for (i, _, _), res in zip(jobs, pool.map(lambda j: _score_one(j[1], j[2]), jobs)):
            got = False
            for k, v in res.items():
                if v is not None:
                    scores.at[i, k], got = v, True
            stats["scored" if got else "failed"] += 1
    return scores, stats
