"""Downloads each post's picture (a reel's cover frame) and each reel's video, while Instagram's links still work
(they expire after a few days). Uses the app's own safe, size-capped media fetcher (backend).

  ../backend/.venv/bin/python download_media.py

Writes data/media/<shortcode>.jpg and data/reels/<shortcode>.mp4, and data/media_index.csv (what was saved).
Already-saved files are skipped, so it can be run again after a failure.
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))
from app.scrapers.instagram import media as instagram_media  # noqa: E402

DATA = HERE / "data"
PICS, REELS = DATA / "media", DATA / "reels"
MAX_PICTURE, MAX_VIDEO = 15_000_000, 60_000_000


def shortcode(post_url: str) -> str:
    return post_url.rstrip("/").split("/")[-1]


def fetch(url: str, path: Path, limit: int) -> str:
    if path.exists() and path.stat().st_size > 0:
        return "saved"
    try:
        _, _, _, chunks = instagram_media.open_stream(url)
        size = 0
        with open(path, "wb") as f:
            for chunk in chunks:
                size += len(chunk)
                if size > limit:
                    raise ValueError("too large")
                f.write(chunk)
        return "saved"
    except Exception as exc:  # noqa: BLE001 - one dead link must not stop the rest
        path.unlink(missing_ok=True)
        return f"failed: {str(exc)[:80]}"


def main() -> None:
    PICS.mkdir(parents=True, exist_ok=True)
    REELS.mkdir(parents=True, exist_ok=True)
    posts = pd.read_csv(DATA / "posts.csv")
    jobs = []
    for _, r in posts.iterrows():
        code = shortcode(r["post_url"])
        is_video = str(r["media_type"]).lower() == "video"
        picture = r["thumbnail_url"] if is_video else r["media_url"]
        if isinstance(picture, str):
            jobs.append((code, "picture", picture, PICS / f"{code}.jpg", MAX_PICTURE))
        if is_video and isinstance(r["media_url"], str):
            jobs.append((code, "reel", r["media_url"], REELS / f"{code}.mp4", MAX_VIDEO))
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda j: fetch(j[2], j[3], j[4]), jobs))
    index = pd.DataFrame([{"shortcode": j[0], "kind": j[1], "file": str(j[3].relative_to(DATA)), "status": s}
                          for j, s in zip(jobs, results)])
    index.to_csv(DATA / "media_index.csv", index=False)
    print(index.groupby(["kind", index["status"].str.startswith("saved")]).size().to_string())
    bad = index[~index["status"].str.startswith("saved")]
    if len(bad):
        print(bad["status"].value_counts().head(5).to_string())


if __name__ == "__main__":
    main()
