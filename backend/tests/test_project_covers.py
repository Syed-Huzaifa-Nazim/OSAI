"""One picture per project for its dashboard card, always from the user's own side."""

from __future__ import annotations

from app.services import project_covers
from app.services.repository import MemoryRepository


def _post(pid, role, i, media_type, url, when):
    return {"id": f"{role}{i}", "project_id": pid, "role": role, "media_type": media_type, "media_url": url,
            "posted_at": when, "post_url": f"https://instagram.com/p/{role}{i}/"}


def test_an_instagram_project_shows_the_newest_own_photo_never_the_competitors_or_a_video_file():
    repo = MemoryRepository("u")
    repo.replace_instagram_posts("p1", [
        _post("p1", "own", 1, "Video", "https://cdn.test/own-new.mp4", "2026-11-10"),
        _post("p1", "own", 2, "Image", "https://cdn.test/own-old.jpg", "2026-11-01"),
        _post("p1", "competitor", 3, "Image", "https://cdn.test/rival.jpg", "2026-11-12"),
    ])
    project = {"id": "p1", "comparison_type": "social_media"}
    assert project_covers.cover_for(repo, project) == "https://cdn.test/own-old.jpg"    # the reel has no cover saved


def test_a_reels_cover_picture_is_used_when_it_was_saved():
    repo = MemoryRepository("u")
    repo.replace_instagram_posts("p2", [_post("p2", "own", 1, "Video", "https://cdn.test/new.mp4", "2026-11-10")])
    repo.replace_instagram_post_media("p2", [{"id": "m1", "post_id": "own1", "project_id": "p2", "position": 1,
                                              "media_type": "Video", "media_url": "https://cdn.test/new.mp4",
                                              "thumbnail_url": "https://cdn.test/new-cover.jpg"}])
    assert project_covers.cover_for(repo, {"id": "p2", "comparison_type": "social_media"}) == "https://cdn.test/new-cover.jpg"


def test_a_project_with_nothing_scraped_has_no_picture_and_does_not_fail():
    repo = MemoryRepository("u")
    assert project_covers.cover_for(repo, {"id": "empty", "comparison_type": "social_media"}) is None
    assert project_covers.cover_for(repo, {"id": "empty", "comparison_type": "website"}) is None
    assert project_covers.cover_for(repo, {"id": "empty", "comparison_type": "ecommerce_product"}) is None
