"""Stream a bounded, class-stratified sample from the official Amazon Reviews 2023 corpus."""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter

import pandas as pd
import requests

from common import ROOT, config, save_json

BASE = "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw"


def stream_jsonl(url, max_retries=12, range_size=256 * 1024):
    """Read JSONL in bounded byte ranges, retrying without losing partial lines."""
    offset = 0
    failures = 0
    buffer = b""
    total = None
    while True:
        end = offset + range_size - 1
        headers = {"Accept-Encoding": "identity", "Range": f"bytes={offset}-{end}"}
        try:
            with requests.get(url, headers=headers, timeout=(30, 60)) as response:
                response.raise_for_status()
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                if response.status_code != 206 or not match or int(match[1]) != offset:
                    raise RuntimeError("Dataset server did not honor the requested byte range")
                expected = int(match[2]) - offset + 1
                if len(response.content) != expected:
                    raise RuntimeError("Dataset server returned an incomplete byte range")
                total = int(match[3])
                buffer += response.content
                offset += expected
                failures = 0
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        yield json.loads(line)
                if offset >= total:
                    if buffer.strip():
                        yield json.loads(buffer)
                    return
        except requests.RequestException as exc:
            failures += 1
            if failures > max_retries:
                raise RuntimeError(f"Dataset stream failed after {failures} retries at byte {offset:,}: {exc}") from exc
            print(f"Dataset connection interrupted at byte {offset:,}; retry {failures}/{max_retries}", flush=True)
            time.sleep(min(2 ** failures, 30))


def label_for_rating(rating):
    try:
        rating = int(float(rating))
    except (TypeError, ValueError):
        return None
    return 2 if rating <= 2 and rating >= 1 else (1 if rating == 3 else (0 if rating <= 5 and rating >= 4 else None))


def download(categories, per_class):
    # One pass per review category, with quotas per class and category.
    quotas = {(category, label): per_class // len(categories) + (index < per_class % len(categories))
              for index, category in enumerate(categories) for label in range(3)}
    counts = Counter()
    rows = []
    for category in categories:
        print(f"Streaming {category} reviews", flush=True)
        url = f"{BASE}/review_categories/{category}.jsonl"
        for seen, record in enumerate(stream_jsonl(url), start=1):
            if seen % 100000 == 0:
                print(f"{category}: scanned {seen:,} reviews; collected {sum(counts[(category, item)] for item in range(3)):,}", flush=True)
            label = label_for_rating(record.get("rating"))
            key = (category, label)
            if label is None or counts[key] >= quotas[key]:
                continue
            review = str(record.get("text") or "").strip()
            parent = str(record.get("parent_asin") or "").strip()
            if not review or not parent:
                continue
            rows.append({"parent_asin": parent, "category": category, "rating": int(float(record["rating"])),
                         "label": label, "review_text": review, "product_title": "", "sub_category": "", "price": None, "features": ""})
            counts[key] += 1
            if all(counts[(category, item)] >= quotas[(category, item)] for item in range(3)):
                break
        for item in range(3):
            if counts[(category, item)] < quotas[(category, item)]:
                raise RuntimeError(f"Insufficient {category} class {item} reviews: {counts[(category,item)]}")
        print(f"{category}: review quotas reached after {seen:,} rows", flush=True)
    # Join only sampled parent IDs, never materialize the large metadata archive.
    target = ROOT / "data/raw/amazon_raw_sample.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(target, index=False)
    for category in categories:
        print(f"Streaming {category} metadata for sampled products", flush=True)
        selected = {r["parent_asin"] for r in rows if r["category"] == category}
        metadata = {}
        url = f"{BASE}/meta_categories/meta_{category}.jsonl"
        for seen, record in enumerate(stream_jsonl(url), start=1):
            if seen % 500000 == 0:
                print(f"{category}: scanned {seen:,} metadata rows; matched {len(metadata):,}/{len(selected):,}", flush=True)
            parent = str(record.get("parent_asin") or "")
            if parent in selected:
                metadata[parent] = record
            if len(metadata) == len(selected):
                break
        for row in rows:
            if row["category"] != category:
                continue
            record = metadata.get(row["parent_asin"], {})
            row["product_title"] = str(record.get("title") or "")
            row["sub_category"] = str(record.get("main_category") or "")
            row["price"] = pd.to_numeric(record.get("price"), errors="coerce")
            row["features"] = " ".join(record.get("features") or [])
        pd.DataFrame(rows).to_csv(target, index=False)
        print(f"{category}: matched {len(metadata):,}/{len(selected):,} sampled products", flush=True)
    pd.DataFrame(rows).to_csv(target, index=False)
    save_json(ROOT / "data/raw/download_manifest.json", {"source": BASE, "categories": categories,
                                                        "per_class": per_class, "counts": {str(k): v for k, v in counts.items()},
                                                        "rows": len(rows), "metadata_matched": sum(bool(r["product_title"]) for r in rows)})
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=None)
    parser.add_argument("--categories", nargs="+", default=None)
    args = parser.parse_args()
    settings = config()
    print(download(args.categories or settings["categories"], args.per_class or settings["raw_per_class"]))

