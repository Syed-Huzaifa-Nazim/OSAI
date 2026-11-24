"""Run one small real inference for each hosted Daraz/Instagram model layer.

Run one layer per process so large model instances do not accumulate in memory.
Examples: python -m scripts.smoke_models daraz; python -m scripts.smoke_models caption
"""

from __future__ import annotations

import argparse
import math


def check_daraz() -> None:
    from app.analysis.daraz import reviews

    output = reviews.analyse(["Beautiful earrings, excellent quality and fast delivery."])
    if len(output) != 1 or output[0].get("sentiment") not in {"positive", "negative", "neutral"}:
        raise RuntimeError(f"Daraz review inference failed: {output!r}")


def check_caption() -> None:
    import pandas as pd

    from app.analysis.instagram.content_layer import caption_labels

    output = caption_labels(pd.Series(["New jewellery on sale. DM us to order."]))
    if len(output) != 1 or not any(key.startswith("cap_") for key in output.columns):
        raise RuntimeError("Instagram caption inference returned no labels")


def check_picture() -> None:
    from PIL import Image

    from app.analysis.instagram.content_layer import picture_tags

    output = picture_tags([Image.new("RGB", (224, 224), (160, 160, 160))])
    if len(output) != 1 or "face" not in output[0] or "shown" not in output[0]:
        raise RuntimeError("Instagram/Daraz picture model inference failed")


def check_quality() -> None:
    from PIL import Image

    from app.analysis.instagram import media_features, media_scoring

    image = Image.new("RGB", (224, 224), (160, 160, 160))
    score = media_scoring._predict_image("image_quality", image, media_features.image_features(image))
    if score is None or not math.isfinite(score):
        raise RuntimeError("Instagram picture quality model inference failed")


def check_reel() -> None:
    import numpy as np
    from PIL import Image, ImageDraw

    from app.analysis.instagram.content_layer import _ocr_text
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    from scenedetect import ContentDetector

    image = Image.new("RGB", (320, 120), "white")
    ImageDraw.Draw(image).text((20, 35), "SALE 25", fill="black")
    text = _ocr_text(image)
    if not isinstance(text, str):
        raise RuntimeError("Instagram reel OCR failed")
    if not isinstance(get_speech_timestamps(np.zeros(16000, dtype=np.float32), VadOptions()), list):
        raise RuntimeError("Instagram reel voice detector failed")
    ContentDetector()


CHECKS = {
    "daraz": check_daraz,
    "caption": check_caption,
    "picture": check_picture,
    "quality": check_quality,
    "reel": check_reel,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("layer", choices=CHECKS)
    layer = parser.parse_args().layer
    CHECKS[layer]()
    print(f"PASS: {layer} inference", flush=True)


if __name__ == "__main__":
    main()
