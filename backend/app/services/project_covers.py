"""One picture per project, for its card on the dashboard: taken from the user's OWN side of what was scraped.

  Instagram  -> the newest post's photo (a reel's cover frame, a carousel's first slide)
  Product    -> the own listing's main image
  Website    -> the own page's share image (og:image), else its first image

Nothing is downloaded or stored: the URL is the source's own. A project with nothing scraped yet, or a table
that cannot be read, simply has no picture (the card then shows an icon).
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("optistratix.project_covers")

_VIDEO = re.compile(r"\.mp4(\?|$)", re.I)


def _instagram(repo, project_id: str) -> str | None:
    posts = [p for p in repo.list_instagram_posts(project_id) if p.get("role") == "own"]
    posts.sort(key=lambda p: p.get("posted_at") or "", reverse=True)
    try:
        media = repo.list_instagram_post_media(project_id)
    except Exception:  # noqa: BLE001 - media rows are an extra
        media = []
    first: dict[str, dict[str, Any]] = {}
    for m in sorted(media, key=lambda m: m.get("position") or 0):
        first.setdefault(m.get("post_id"), m)
    for post in posts:
        m = first.get(post.get("id")) or {}
        if m.get("thumbnail_url"):                      # a still picture Instagram gave (a reel's cover frame)
            return m["thumbnail_url"]
        is_video = str(m.get("media_type") or post.get("media_type") or "").lower() == "video"
        for url in (m.get("media_url"), post.get("media_url")):
            if url and not is_video and not _VIDEO.search(url):
                return url
    return None


def _product(repo, project_id: str) -> str | None:
    own = [p for p in repo.list_ecommerce_products(project_id) if p.get("role") == "own"]
    if not own:
        return None
    images = sorted(
        (i for i in repo.list_ecommerce_product_images(project_id) if i.get("product_id") == own[0].get("id")),
        key=lambda i: (not i.get("is_primary"), i.get("position") or 0),
    )
    return images[0].get("url") if images else None


def _website(repo, project_id: str) -> str | None:
    own_pages = {p.get("id") for p in repo.list_website_pages(project_id) if p.get("role") == "own"}
    images = [i for i in repo.list_website_page_images(project_id) if i.get("page_id") in own_pages]
    images.sort(key=lambda i: (i.get("source") != "og_image", i.get("position") or 0))
    return images[0].get("image_url") if images else None


def cover_for(repo, project: dict[str, Any]) -> str | None:
    kind = project.get("comparison_type")
    try:
        if kind == "social_media":
            return _instagram(repo, project["id"])
        if kind == "ecommerce_product":
            return _product(repo, project["id"])
        if kind == "website":
            return _website(repo, project["id"])
    except Exception as exc:  # noqa: BLE001 - one project's picture must never break the dashboard
        logger.info("No cover picture for project %s: %s", project.get("id"), exc)
    return None


def covers(repo) -> dict[str, str]:
    """project id -> picture URL, for every project that has one."""
    out: dict[str, str] = {}
    for project in repo.list_projects():
        url = cover_for(repo, project)
        if url:
            out[project["id"]] = url
    return out
