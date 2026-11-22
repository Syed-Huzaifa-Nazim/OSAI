"""Daraz jewellery dataset, step 3: what each listing's main photo shows, with our Model D
(frozen CLIP + heads trained on 300 person-checked Instagram jewellery pictures): jewellery worn / in hand /
displayed / other, and whether a face is visible. Photos are cached in raw/photos/. Writes photo_tags.csv.
"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.analysis.instagram.content_layer import picture_tags  # noqa: E402

PHOTOS = HERE / "raw" / "photos"


def photo(item_id: str, url: str) -> Image.Image | None:
    path = PHOTOS / f"{item_id}.jpg"
    if not path.exists():
        try:
            r = requests.get(url if url.startswith("http") else "https:" + url, timeout=30,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            im.thumbnail((512, 512))
            im.save(path, quality=90)
            time.sleep(0.2)
        except Exception as exc:  # noqa: BLE001
            print("photo failed", item_id, type(exc).__name__)
            return None
    return Image.open(path).convert("RGB")


def main() -> None:
    PHOTOS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(HERE / "search_listings.csv").drop_duplicates("item_id")
    rows, batch = [], []

    def flush():
        tags = picture_tags([im for _, im in batch])
        rows.extend({"item_id": i, "photo_face": t["face"], "photo_shown": t["shown"]} for (i, _), t in zip(batch, tags))
        batch.clear()

    from concurrent.futures import ThreadPoolExecutor
    pairs = [(str(r.item_id), str(r.image)) for r in df.itertuples()]
    with ThreadPoolExecutor(8) as pool:                 # downloads in parallel; tagging stays in one thread
        for n, ((item_id, _), im) in enumerate(zip(pairs, pool.map(lambda p: photo(*p), pairs)), 1):
            if im is not None:
                batch.append((item_id, im))
            if len(batch) == 32:
                flush()
            if n % 200 == 0:
                print(n, "photos", flush=True)
    if batch:
        flush()
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "photo_tags.csv", index=False)
    print(len(out), "tagged;", out.photo_shown.value_counts().to_dict(), "faces", int(out.photo_face.sum()))


if __name__ == "__main__":
    main()
