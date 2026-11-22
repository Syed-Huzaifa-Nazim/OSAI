"""Grids of pictures with their drafted tags underneath, for a quick human (or Claude) spot check.

  .venv/bin/python contact_sheets.py [n_pictures] [seed]

Writes labels/spotcheck/sheet_01.jpg ... (12 pictures per sheet) and labels/spotcheck/sample.csv (which pictures).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "labels" / "spotcheck"
OCR_FLAGS = {"text_on_image": "TEXT", "price_on_image": "PRICE", "phone_on_image": "PHONE", "sale_words_on_image": "SALE"}


def main(n: int = 48, seed: int = 7) -> None:
    tags = pd.read_csv(HERE / "labels" / "pictures_tags.csv")
    sample = tags.sample(frac=1, random_state=seed).groupby("handle").head(2)          # 2 per shop
    sample = sample.sample(min(n, len(sample)), random_state=seed).reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    sample[["shortcode", "handle"]].to_csv(OUT / "sample.csv", index=False)
    font = ImageFont.load_default()
    tile, cols = 300, 4
    for s in range(0, len(sample), 12):
        part = sample.iloc[s:s + 12]
        rows = (len(part) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tile, rows * (tile + 46)), "white")
        draw = ImageDraw.Draw(sheet)
        for k, (_, r) in enumerate(part.iterrows()):
            x, y = (k % cols) * tile, (k // cols) * (tile + 46)
            img = Image.open(HERE / "data" / "media" / f"{r['shortcode']}.jpg").convert("RGB")
            img.thumbnail((tile - 6, tile - 6))
            sheet.paste(img, (x + 3, y + 3))
            ocr = [v for t, v in OCR_FLAGS.items() if str(r[t]).lower() == "true"]
            draw.text((x + 4, y + tile + 2), f"#{s + k + 1} {r['handle'][:20]}", fill="black", font=font)
            draw.text((x + 4, y + tile + 16), f"{r['jewellery_shown'].upper()} · {r['background']} · {r['face']} · {r['amount']}", fill="darkred", font=font)
            draw.text((x + 4, y + tile + 30), " ".join(ocr) or "(no text)", fill="gray", font=font)
        sheet.save(OUT / f"sheet_{s // 12 + 1:02d}.jpg", quality=85)
    print(f"{len(sample)} pictures on {(len(sample) + 11) // 12} sheets in {OUT}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 48, int(sys.argv[2]) if len(sys.argv) > 2 else 7)
