"""Drafts picture tags for every saved post picture (Model D's labels, to be verified by a person).

  .venv/bin/python tag_pictures.py          (the data_collection environment: torch, open_clip, easyocr)

How each tag is drafted (marked in the file, so nobody mistakes a draft for a checked label):
  CLIP zero-shot (pretrained ViT-B-32, no training): the picture is compared with two short descriptions and the
  closer one wins (a two-way choice, so no threshold is invented). Several wordings per side are averaged.
  OCR (EasyOCR, English): reads text on the picture; regular expressions then look for a price, a phone number and
  sale words.
Writes labels/pictures_tags.csv (+ an Excel copy for checking later).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image

HERE = Path(__file__).resolve().parent
DATA, LABELS = HERE / "data", HERE / "labels"

# Each tag is a choice between options; the picture gets the option whose descriptions it is closest to. Wordings
# avoid "no ..." / "without ..." (CLIP matches the word, not the negation: "no human face" still means "face" to it).
CLIP_TAGS = {
    "jewellery_shown": {
        "worn": ["jewellery worn by a woman on her ear, neck or wrist", "a woman wearing a necklace and earrings"],
        "in_hand": ["a hand holding a piece of jewellery up to the camera", "jewellery resting in the palm of a hand"],
        "displayed": ["jewellery laid on a table, tray, box or cloth", "jewellery on a display stand or mannequin bust"],
        "other": ["a product photo of clothes, bags or other goods", "a graphic poster with mostly text"],
    },
    "background": {
        "plain": ["an item photographed on a plain single-colour backdrop", "a clean studio product shot"],
        "busy": ["a photo inside a busy shop with many items around", "a lifestyle photo in a room or outdoors"],
    },
    "face": {
        "face": ["a portrait photo of a woman's face", "a close-up of a person's face looking at the camera"],
        "object": ["a close-up photo of an object", "a photo of hands and jewellery", "a product on a surface"],
    },
    "amount": {
        "many": ["many pieces of jewellery spread out together", "a tray full of rings or earrings"],
        "one_set": ["a single necklace or one matching jewellery set", "one ring or one pair of earrings"],
    },
    "screenshot": {
        "screenshot": ["a phone screenshot of a chat conversation", "a screenshot of a customer message"],
        "photo": ["a photograph of a product", "a photograph of a person"],
    },
}
PRICE = re.compile(r"(?:\brs\.?\s?\d|\bpkr\s?\d|\d[\d,]{2,}\s?(?:/-|rs|pkr)|price\s*[:\-]?\s*\d)", re.I)
PHONE = re.compile(r"(?:\+?92|\b0)\s?3\d{2}[\s-]?\d{3}[\s-]?\d{4}")
SALE = re.compile(r"\b(?:sale|off|discount|offer|deal|flat\s?\d+|\d+\s?%)", re.I)


def clip_tags(paths: list[Path]) -> pd.DataFrame:
    import open_clip

    model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
    tok = open_clip.get_tokenizer("ViT-B-32")
    model.eval()
    with torch.no_grad():
        text_feats = {}
        for tag, options in CLIP_TAGS.items():
            emb = []
            for words in options.values():
                t = model.encode_text(tok(words))
                t = t / t.norm(dim=-1, keepdim=True)
                emb.append(t.mean(0))
            e = torch.stack(emb)
            text_feats[tag] = (list(options), e / e.norm(dim=-1, keepdim=True))
        rows = []
        for i in range(0, len(paths), 32):
            batch = paths[i:i + 32]
            imgs = torch.stack([preprocess(Image.open(p).convert("RGB")) for p in batch])
            f = model.encode_image(imgs)
            f = f / f.norm(dim=-1, keepdim=True)
            probs = {tag: (names, (100 * f @ t.T).softmax(dim=-1).numpy()) for tag, (names, t) in text_feats.items()}
            for j, p in enumerate(batch):
                row = {"shortcode": p.stem}
                for tag, (names, pr) in probs.items():
                    k = int(pr[j].argmax())
                    row[tag], row[f"p_{tag}"] = names[k], round(float(pr[j][k]), 3)
                rows.append(row)
            print(f"  CLIP {min(i + 32, len(paths))}/{len(paths)}", flush=True)
    return pd.DataFrame(rows)


def ocr_tags(paths: list[Path]) -> pd.DataFrame:
    import easyocr

    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    rows = []
    for k, p in enumerate(paths, 1):
        img = Image.open(p).convert("RGB")
        img.thumbnail((1080, 1080))
        try:
            text = " ".join(t for _, t, conf in reader.readtext(np.asarray(img)) if conf >= 0.3)
        except Exception as exc:  # noqa: BLE001 - one bad picture must not stop the rest
            text = f"[ocr failed: {exc}]"
        rows.append({"shortcode": p.stem, "ocr_text": text[:300],
                     "text_on_image": len(re.sub(r"[^A-Za-z0-9]", "", text)) >= 4,
                     "price_on_image": bool(PRICE.search(text)), "phone_on_image": bool(PHONE.search(text)),
                     "sale_words_on_image": bool(SALE.search(text))})
        if k % 50 == 0:
            print(f"  OCR {k}/{len(paths)}", flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    posts = pd.read_csv(HERE / "datasets" / "posts_dataset.csv")
    paths = [DATA / "media" / f"{c}.jpg" for c in posts["shortcode"] if (DATA / "media" / f"{c}.jpg").exists()]
    print(f"{len(paths)} pictures to tag")
    tags = clip_tags(paths)
    ocr_cols = ["shortcode", "ocr_text", "text_on_image", "price_on_image", "phone_on_image", "sale_words_on_image"]
    old = pd.read_csv(LABELS / "pictures_tags.csv") if (LABELS / "pictures_tags.csv").exists() else pd.DataFrame(columns=ocr_cols)
    old = old[[c for c in ocr_cols if c in old.columns]].dropna(subset=["shortcode"])
    todo = [p for p in paths if p.stem not in set(old["shortcode"])]
    print(f"OCR: {len(paths) - len(todo)} reused, {len(todo)} new")
    ocr = pd.concat([old, ocr_tags(todo)], ignore_index=True) if todo else old
    tags = tags.merge(ocr, on="shortcode", how="left")
    tags = posts[["shortcode", "handle", "format", "post_url"]].merge(tags, on="shortcode")
    tags["source_clip_tags"], tags["source_text_tags"] = "clip_zero_shot_draft", "ocr_draft"
    tags["verified_corrections"] = ""                        # filled in by a person
    tags.to_csv(LABELS / "pictures_tags.csv", index=False)
    summary = {t: tags[t].value_counts().to_dict() for t in CLIP_TAGS}
    summary.update({t: int(tags[t].fillna(False).astype(bool).sum()) for t in ["text_on_image", "price_on_image", "phone_on_image", "sale_words_on_image"]})
    print("pictures:", len(tags), "| tag counts:", summary)


if __name__ == "__main__":
    main()
