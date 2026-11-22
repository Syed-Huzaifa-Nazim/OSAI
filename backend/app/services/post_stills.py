"""The still picture of each scraped Instagram post: a reel's cover frame, otherwise its first image.

A reel's media URL is an .mp4 video, which cannot be shown as a picture. Instagram also gives a cover frame
(`thumbnail_url`, migration 0013); this module maps every post URL to that still, so the gap cards, the
explanations and the PDF report all show the same picture for a post.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import Any

logger = logging.getLogger("optistratix.post_stills")

_VIDEO = re.compile(r"\.mp4(\?|$)", re.I)


def is_video_url(url: str | None) -> bool:
    return bool(url and _VIDEO.search(url))


def post_stills(repo, project_id: str) -> dict[str, str]:
    """post URL -> its still picture. Empty when nothing was scraped or the media rows cannot be read."""
    try:
        posts = {p["id"]: p for p in repo.list_instagram_posts(project_id)}
        media = sorted(repo.list_instagram_post_media(project_id), key=lambda m: m.get("position") or 0)
    except Exception as exc:  # noqa: BLE001 - pictures are an extra; never a reason to fail
        logger.info("No post pictures for project %s: %s", project_id, exc)
        return {}
    out: dict[str, str] = {}
    for m in media:
        url = (posts.get(m.get("post_id")) or {}).get("post_url")
        if not url or url in out:
            continue
        is_video = str(m.get("media_type") or "").lower() == "video" or is_video_url(m.get("media_url"))
        still = m.get("thumbnail_url") or (None if is_video else m.get("media_url"))
        if still:
            out[url] = still
    return out


def _still(stills: dict[str, str], post_url: str | None, current: str | None) -> str:
    """The post's still when known; else the current picture, unless that is a video file."""
    if post_url and post_url in stills:
        return stills[post_url]
    return "" if is_video_url(current) else (current or "")


def with_stills(gaps: list[dict[str, Any]], stills: dict[str, str]) -> list[dict[str, Any]]:
    """Copies of the gaps whose example posts and saved explanation posts carry a still picture."""
    out = []
    for gap in gaps:
        details = gap.get("details") or {}
        if not details.get("examples") and not (details.get("explanation") or {}).get("evidence"):
            out.append(gap)
            continue
        gap = copy.deepcopy(gap)
        details = gap["details"]
        for ex in details.get("examples") or []:
            ex["imageUrl"] = _still(stills, ex.get("postUrl"), ex.get("imageUrl"))
        for ev in (details.get("explanation") or {}).get("evidence") or []:
            ev["image_url"] = _still(stills, ev.get("post_url"), ev.get("image_url"))
        out.append(gap)
    return out


def fill_evidence(evidence: list[dict[str, Any]], stills: dict[str, str]) -> None:
    """Gives each explanation post (in place) its still picture."""
    for ev in evidence:
        ev["image_url"] = _still(stills, ev.get("post_url"), ev.get("image_url"))
