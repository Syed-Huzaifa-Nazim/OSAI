"""Materialize and verify the public OSAI Git LFS weights during image builds.

The GitHub source archive used by Railway may contain LFS pointers. This script
downloads only the six required weights from the destination repository, keeps
partial downloads for retries, and never prints signed download URLs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

LFS_BATCH_URL = "https://github.com/Syed-Huzaifa-Nazim/OSAI.git/info/lfs/objects/batch"
MODEL_PATHS = (
    "Daraz_Model/model_package/aspect_model.joblib",
    "Daraz_Model/model_package/aspect_model/model.safetensors",
    "Daraz_Model/model_package/sentiment_model.joblib",
    "Daraz_Model/model_package/sentiment_model/model.safetensors",
    "backend/app/analysis/instagram/models/caption_model/head.pt",
    "backend/app/analysis/instagram/models/caption_model/model.safetensors",
)
POINTER = re.compile(rb"\Aversion https://git-lfs.github.com/spec/v1\r?\noid sha256:([0-9a-f]{64})\r?\nsize ([0-9]+)\r?\n?\Z")


def _digest(path: Path) -> tuple[str, int]:
    sha = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            sha.update(block)
            size += len(block)
    return sha.hexdigest(), size


def _download_action(oid: str, size: int) -> tuple[str, dict[str, str]]:
    body = json.dumps({"operation": "download", "transfers": ["basic"],
                       "objects": [{"oid": oid, "size": size}]}).encode()
    request = urllib.request.Request(
        LFS_BATCH_URL, data=body, method="POST",
        headers={"Accept": "application/vnd.git-lfs+json",
                 "Content-Type": "application/vnd.git-lfs+json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        obj = json.load(response)["objects"][0]
    if obj.get("error") or "download" not in obj.get("actions", {}):
        raise RuntimeError(f"LFS object unavailable: {oid[:12]}")
    action = obj["actions"]["download"]
    return action["href"], action.get("header", {})


def _materialize(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    pointer = POINTER.fullmatch(path.read_bytes()) if path.stat().st_size < 200 else None
    if pointer is None:
        if path.stat().st_size < 1000:
            raise RuntimeError(f"Unexpected small model file: {path}")
        print(f"Already materialized: {path.name} ({path.stat().st_size} bytes)", flush=True)
        return

    oid, size = pointer.group(1).decode(), int(pointer.group(2))
    partial = path.with_name(path.name + ".part")
    for attempt in range(1, 6):
        try:
            if partial.exists() and partial.stat().st_size > size:
                partial.unlink()
            offset = partial.stat().st_size if partial.exists() else 0
            url, headers = _download_action(oid, size)
            headers = dict(headers)
            if offset:
                headers["Range"] = f"bytes={offset}-"
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=180) as response:
                if offset and response.status != 206:
                    offset = 0
                with partial.open("ab" if offset else "wb") as stream:
                    shutil.copyfileobj(response, stream, length=4 * 1024 * 1024)
            actual_oid, actual_size = _digest(partial)
            if actual_size != size or actual_oid != oid:
                if actual_size < size:
                    raise IOError(f"Incomplete transfer ({actual_size}/{size} bytes)")
                partial.unlink(missing_ok=True)
                raise RuntimeError(f"SHA-256 mismatch for {path.name}")
            partial.replace(path)
            print(f"Verified LFS model: {path.name} ({size} bytes)", flush=True)
            return
        except (OSError, urllib.error.URLError, RuntimeError) as exc:
            if attempt == 5:
                raise RuntimeError(f"Could not materialize {path.name}") from exc
            print(f"Retrying {path.name} ({attempt}/5): {type(exc).__name__}", flush=True)
            time.sleep(min(2 ** attempt, 20))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    root = parser.parse_args().root.resolve()
    for relative in MODEL_PATHS:
        _materialize(root / relative)


if __name__ == "__main__":
    main()
