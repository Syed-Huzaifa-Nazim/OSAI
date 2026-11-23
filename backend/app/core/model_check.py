"""Are all the trained models really usable on this server?

Every model layer skips itself quietly when its library or file is missing (so one missing part never stops an
analysis). That is right during a run, but a server set up without them would silently give fewer gaps. This
check runs at start-up and in /api/v1/health, and names exactly what is missing, including model files that are
only Git LFS placeholders (the repository was cloned without `git lfs pull`).

Set REQUIRE_MODELS=true on a hosted server: the backend then refuses to start until everything is in place.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from app.core.config import settings

APP = Path(__file__).resolve().parents[1]
IG = APP / "analysis" / "instagram" / "models"
DZ = APP / "analysis" / "daraz" / "models"

#: python import name -> pip package to install
LIBRARIES = {
    "torch": "torch (CPU build, see requirements-models.txt)", "torchvision": "torchvision",
    "open_clip": "open_clip_torch", "transformers": "transformers", "easyocr": "easyocr",
    "scenedetect": "scenedetect", "faster_whisper": "faster-whisper", "cv2": "opencv-python-headless",
    "sklearn": "scikit-learn", "joblib": "joblib", "scipy": "scipy", "PIL": "pillow",
}


def _files() -> dict[str, tuple[Path, int]]:
    """file label -> (path, smallest real size in bytes; anything smaller is a placeholder)."""
    daraz = Path(settings.daraz_review_model_dir)
    return {
        "Caption model weights": (IG / "caption_model" / "model.safetensors", 100_000_000),
        "Picture model heads": (IG / "picture_heads.joblib", 1_000),
        "Picture quality model": (IG / "image_quality.joblib", 10_000),
        "Jewellery evidence (Instagram)": (IG / "jewellery_evidence.json", 100),
        "Daraz evidence": (DZ / "daraz_evidence.json", 100),
        "Jewellery review reasons model": (DZ / "review_reasons" / "reasons.joblib", 100_000),
        "Review sentiment model weights": (daraz / "sentiment_model" / "model.safetensors", 100_000_000),
        "General review topics model weights": (daraz / "aspect_model" / "model.safetensors", 100_000_000),
        "Review model code": (daraz / "review_analyzer.py", 100),
    }


#: What each part of the analysis needs.
LAYERS: dict[str, tuple[list[str], list[str]]] = {
    "Instagram captions (Model C)": (["torch", "transformers"], ["Caption model weights"]),
    "Instagram pictures (Model D)": (["torch", "open_clip", "joblib", "PIL"], ["Picture model heads", "Jewellery evidence (Instagram)"]),
    "Instagram reels (face, text, cuts, voice)": (["torch", "open_clip", "cv2", "easyocr", "scenedetect", "faster_whisper"], ["Picture model heads"]),
    "Instagram picture quality (KonIQ)": (["torch", "torchvision", "joblib"], ["Picture quality model"]),
    "Daraz listing gaps (statistics)": (["scipy"], ["Daraz evidence"]),
    "Daraz reviews (sentiment + reasons)": (["torch", "transformers", "sklearn", "joblib"],
                                            ["Review sentiment model weights", "General review topics model weights",
                                             "Review model code", "Jewellery review reasons model"]),
    "Daraz main photo (Model D)": (["torch", "open_clip", "joblib", "PIL"], ["Picture model heads"]),
}


def _file_problem(path: Path, smallest: int) -> str | None:
    if not path.exists():
        return "missing"
    size = path.stat().st_size
    if size < smallest:
        try:
            if path.read_bytes()[:40].startswith(b"version https://git-lfs"):
                return "only a Git LFS placeholder (run: git lfs pull)"
        except OSError:
            pass
        return f"too small ({size} bytes)"
    return None


def report() -> dict[str, Any]:
    libs = {name: importlib.util.find_spec(name) is not None for name in LIBRARIES}
    files = {label: _file_problem(path, smallest) for label, (path, smallest) in _files().items()}
    layers = {}
    for layer, (need_libs, need_files) in LAYERS.items():
        missing = [f"library {LIBRARIES[n]}" for n in need_libs if not libs[n]]
        missing += [f"{f}: {files[f]}" for f in need_files if files[f]]
        layers[layer] = {"ready": not missing, "missing": missing}
    return {"ready": all(v["ready"] for v in layers.values()), "layers": layers}


def summary_lines(rep: dict[str, Any]) -> list[str]:
    return [f"{layer}: NOT READY ({'; '.join(v['missing'])})" for layer, v in rep["layers"].items() if not v["ready"]]
