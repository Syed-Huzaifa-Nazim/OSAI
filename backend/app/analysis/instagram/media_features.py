"""Numbers that describe how a picture or a video looks, calculated from the pixels.

No pretrained network is used. These features feed Random Forests that we train ourselves on
people's quality ratings (KonIQ-10k for pictures, LSVQ for videos) and on memorability ratings
(LaMem). Sharpness, light, contrast, colour, noise and detail are what quality ratings mostly
respond to; memorability depends more on what is in the picture, so expect that model to be weaker.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage

MAX_SIDE = 512                 # pictures are shrunk to this before measuring (speed)
FEATURES_VERSION = 2           # raise when a formula changes, so saved training features are measured again
VIDEO_FRAMES = 8               # frames read from each video
IMAGE_FEATURES = [
    "sharpness", "focus_centre", "brightness", "contrast", "dynamic_range", "colourfulness",
    "saturation", "noise", "detail", "entropy", "megapixels", "aspect",
]
_CORE = ["sharpness", "brightness", "contrast", "colourfulness", "saturation", "noise", "detail", "entropy"]
VIDEO_FEATURES = [f"{f}_{s}" for f in _CORE for s in ("mean", "std")] + ["motion_mean", "motion_std", "fps", "duration", "megapixels"]

_NOISE_KERNEL = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=float)


def image_features(img: Image.Image) -> dict[str, float]:
    """Twelve numbers describing one picture."""
    w0, h0 = img.size
    im = img.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    rgb = np.asarray(im, dtype=float) / 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    h, w = gray.shape

    lap = ndimage.laplace(gray)
    sharp = float(lap.var())
    cy0, cy1, cx0, cx1 = h // 4, 3 * h // 4, w // 4, 3 * w // 4
    centre = float(lap[cy0:cy1, cx0:cx1].var())
    border_mask = np.ones_like(lap, dtype=bool)
    border_mask[cy0:cy1, cx0:cx1] = False
    border = float(lap[border_mask].var()) if border_mask.any() else sharp
    # share of the sharpness that sits in the centre: 0..1 (0.5 = even). A plain ratio centre / border explodes
    # when the border is flat (one KonIQ picture gave 39,517 standard deviations), so the bounded share is used.
    focus_centre = centre / (centre + border) if centre + border > 0 else 0.5

    rg, yb = r - g, 0.5 * (r + g) - b
    colourfulness = math.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * math.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    saturation = float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-9), 0).mean())

    # Immerkaer's fast estimate of the noise level
    noise = float(math.sqrt(math.pi / 2) / (6 * max(w - 2, 1) * max(h - 2, 1)) * np.abs(ndimage.convolve(gray, _NOISE_KERNEL)).sum())
    gy, gx = np.gradient(gray)
    detail = float(np.hypot(gx, gy).mean())
    hist, _ = np.histogram(gray, bins=64, range=(0, 1))
    p = hist / max(hist.sum(), 1)
    entropy = float(-(p[p > 0] * np.log2(p[p > 0])).sum())
    p5, p95 = np.percentile(gray, [5, 95])
    return {
        "sharpness": sharp, "focus_centre": float(focus_centre), "brightness": float(gray.mean()), "contrast": float(gray.std()),
        "dynamic_range": float(p95 - p5), "colourfulness": float(colourfulness), "saturation": saturation, "noise": noise,
        "detail": detail, "entropy": entropy, "megapixels": float(w0 * h0 / 1e6), "aspect": float(w0 / max(h0, 1)),
    }


def read_video(path: str, n_frames: int = VIDEO_FRAMES):
    """(frames, small grayscale frames, fps, frame count) of a video file, or None if it cannot be read."""
    import cv2

    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            return None
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0
        if total < 2:
            return None
        idx = np.linspace(0, total - 1, n_frames).astype(int)
        frames, small = [], []
        for i in idx:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, bgr = cap.read()
            if not ok:
                continue
            frames.append(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
            small.append(cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (64, 64)).astype(float) / 255.0)
        if len(frames) < 2:
            return None
        return frames, small, fps, total
    finally:
        cap.release()


def _video_stats(frames, small, fps, total) -> dict[str, float]:
    """Our own measurements of a video: the picture measurements across frames, plus motion and size."""
    per = [image_features(f) for f in frames]
    out: dict[str, float] = {}
    for f in _CORE:
        vals = np.array([d[f] for d in per])
        out[f"{f}_mean"], out[f"{f}_std"] = float(vals.mean()), float(vals.std())
    diffs = np.array([np.abs(a - b).mean() for a, b in zip(small[:-1], small[1:])])
    out["motion_mean"], out["motion_std"] = float(diffs.mean()), float(diffs.std())
    out["fps"], out["duration"] = fps, float(total / fps) if fps else 0.0
    out["megapixels"] = per[0]["megapixels"]
    return out


def video_features(path: str) -> tuple[dict[str, float], Image.Image] | None:
    """Measurements of a video file, and its middle frame (used for picture-based scores). None if it cannot be read."""
    read = read_video(path)
    if read is None:
        return None
    return _video_stats(*read), read[0][len(read[0]) // 2]


def to_vector(features: dict[str, float], names: list[str]) -> list[float]:
    return [float(features.get(n, 0.0)) if np.isfinite(features.get(n, 0.0)) else 0.0 for n in names]


def image_inputs(img: Image.Image, extractor=None) -> tuple[dict[str, float], np.ndarray | None]:
    """What a quality / memorability model is given for one picture: our measurements, and the network's vector."""
    return image_features(img), (extractor.image_vector(img) if extractor is not None else None)


def video_inputs(path: str, extractor=None):
    """Same for a video: (measurements, network vector or None, middle frame), or None if it cannot be read."""
    read = read_video(path)
    if read is None:
        return None
    frames = read[0]
    return _video_stats(*read), (extractor.frames_vector(frames) if extractor is not None else None), frames[len(frames) // 2]
