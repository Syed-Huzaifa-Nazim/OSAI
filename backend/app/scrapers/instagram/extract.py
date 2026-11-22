"""Turning one Apify post object into a storable record.

Pure: a dict in, text fields and metadata out. No network, so it is exercised
directly by tests against saved actor output.

Only the fields named in selectors.POST_PATHS and COMMENT_PATHS are ever read.
The actor's raw payload is never stored wholesale.
"""

from __future__ import annotations

import html as html_lib
import re
from datetime import datetime, timezone
from typing import Any

from . import selectors as S

_WS_RE = re.compile(r"\s+")
_HASHTAG_RE = re.compile(r"#(\w+)")


def _get(node: dict[str, Any], key: str, paths: dict[str, list[str]]) -> Any:
    """First non-empty value among the dotted paths configured for ``key``."""
    for path in paths.get(key, []):
        value: Any = node
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
            if value is None:
                break
        if value not in (None, "", [], {}):
            return value
    return None


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return _WS_RE.sub(" ", html_lib.unescape(str(value)).replace("\xa0", " ")).strip()


def caption_text(value: Any) -> str:
    """Captions keep their line breaks: they are how a post is written."""
    if value is None:
        return ""
    text = html_lib.unescape(str(value)).replace("\xa0", " ")
    lines = [_WS_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def to_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"-?\d[\d,]*", str(value))
    if not match:
        return None
    try:
        return int(match.group(0).replace(",", ""))
    except ValueError:
        return None


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def to_timestamp(value: Any) -> str | None:
    """Apify returns ISO 8601; epoch seconds turn up on some actor versions."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    return text or None


def hashtags(post: dict[str, Any], caption: str) -> list[str]:
    """The actor's list when it has one, otherwise read off the caption."""
    raw = _get(post, "hashtags", S.POST_PATHS)
    tags = [clean_text(tag).lstrip("#") for tag in raw] if isinstance(raw, list) else []
    if not tags:
        tags = _HASHTAG_RE.findall(caption)
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        key = tag.lower()
        if tag and key not in seen:
            seen.add(key)
            out.append(tag)
    return out


def media_items(post: dict[str, Any]) -> list[dict[str, Any]]:
    """Every slide of a carousel, or the single image/video of a normal post."""
    children = post.get(S.CHILD_POSTS_KEY)
    items: list[dict[str, Any]] = []

    if isinstance(children, list) and children:
        for child in children:
            if not isinstance(child, dict):
                continue
            url = child.get("videoUrl") or child.get("displayUrl")
            if url:
                items.append({"media_type": clean_text(child.get("type")) or None, "media_url": url,
                              "thumbnail_url": child.get("displayUrl") or None})
    else:
        url = _get(post, "media_url", S.POST_PATHS)
        if url:
            items.append({
                "media_type": clean_text(_get(post, "media_type", S.POST_PATHS)) or None,
                "media_url": str(url),
                "thumbnail_url": (str(t) if (t := _get(post, "thumbnail_url", S.POST_PATHS)) else None),
            })

    return items[: S.MAX_MEDIA_PER_POST]


def profile_username(items: list[dict[str, Any]]) -> str | None:
    """The scraped profile's own username, read from the profile item itself.

    Deliberately never read off a post. ``ownerUsername`` on a post is the
    post's *author*, which on a collaboration post is the other collaborator,
    so a profile whose newest post is a collaboration would be labelled with
    somebody else's handle. Only an item carrying profile-level markers is
    considered at all.
    """
    for item in items:
        if not isinstance(item, dict):
            continue
        if not any(key in item for key in S.PROFILE_MARKER_KEYS):
            continue
        name = clean_text(_get(item, "username", S.PROFILE_PATHS)).lstrip("@")
        if name:
            return name
    return None


def profile_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    """The profile-level numbers the engagement model needs.

    Read from the same profile item as the username (the posts run already
    returns it), so no extra Apify run is spent. Returns {} when the actor sent
    no profile item; the analysis then reports that it could not grade the side.
    """
    for item in items:
        if not isinstance(item, dict):
            continue
        if not any(key in item for key in S.PROFILE_MARKER_KEYS):
            continue
        stats: dict[str, Any] = {}
        for key in ("followers_count", "following_count", "posts_count", "highlights_count"):
            value = _get(item, key, S.PROFILE_PATHS)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                stats[key] = int(value)
        for key in ("biography", "external_url", "category", "full_name", "profile_picture"):
            value = _get(item, key, S.PROFILE_PATHS)
            if isinstance(value, str) and value.strip():
                stats[key] = value.strip()
        verified = _get(item, "is_verified", S.PROFILE_PATHS)
        if isinstance(verified, bool):
            stats["is_verified"] = verified
        if stats:
            return stats
    return {}


def extract_post(profile_url: str, post: dict[str, Any]) -> dict[str, Any]:
    """One post's structured fields. Returns {} for an item that is not a post."""
    post_url = _get(post, "post_url", S.POST_PATHS)
    caption = caption_text(_get(post, "caption", S.POST_PATHS))
    if not post_url and not caption:
        return {}

    tags = hashtags(post, caption)
    media = media_items(post)
    like_count = to_int(_get(post, "like_count", S.POST_PATHS))
    comment_count = to_int(_get(post, "comment_count", S.POST_PATHS))

    return {
        "profile_url": profile_url,
        "post_url": str(post_url) if post_url else None,
        "owner_username": clean_text(_get(post, "owner_username", S.POST_PATHS)) or None,
        "caption": caption,
        "hashtags": tags,
        "hashtag_count": len(tags),
        "like_count": like_count,
        "comment_count": comment_count,
        "engagement_count": (like_count or 0) + (comment_count or 0),
        "media_type": clean_text(_get(post, "media_type", S.POST_PATHS)) or None,
        "media_url": (media[0]["media_url"] if media else None),
        "media_count": len(media),
        "video_view_count": to_int(_get(post, "video_views", S.POST_PATHS)),
        "location_name": clean_text(_get(post, "location", S.POST_PATHS)) or None,
        "is_sponsored": to_bool(_get(post, "is_sponsored", S.POST_PATHS)),
        "posted_at": to_timestamp(_get(post, "posted_at", S.POST_PATHS)),
        "caption_length": len(caption),
        "caption_word_count": len(caption.split()),
        "media": media,
    }


def extract_comments(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Comment rows grouped by the post URL they belong to."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        post_url = next(
            (item.get(path) for path in S.COMMENT_POST_URL_PATHS if item.get(path)), None
        )
        text = caption_text(_get(item, "comment_text", S.COMMENT_PATHS))
        if not post_url or not text:
            continue
        grouped.setdefault(str(post_url), []).append({
            "commenter_username": clean_text(_get(item, "commenter_username", S.COMMENT_PATHS)) or None,
            "comment_text": text,
            "like_count": to_int(_get(item, "like_count", S.COMMENT_PATHS)),
            "posted_at": to_timestamp(_get(item, "posted_at", S.COMMENT_PATHS)),
        })
    return grouped


def post_text_fields(record: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, str]:
    """What stage 3 embeds for one post, one field at a time."""
    tags = record.get("hashtags") or []
    comment_lines = [comment["comment_text"] for comment in comments if comment["comment_text"]]
    return {
        "caption": record.get("caption") or "No caption on this post.",
        "hashtags": " ".join(f"#{tag}" for tag in tags) or "No hashtags on this post.",
        "comments": "\n".join(comment_lines) or "No comments were collected for this post.",
    }
