"""Every post shows a still picture: a reel's cover frame, never its .mp4 video file."""
from app.services.post_stills import fill_evidence, post_stills, with_stills


class _Repo:
    def list_instagram_posts(self, project_id):
        return [{"id": "a", "post_url": "https://ig/p/a"}, {"id": "b", "post_url": "https://ig/p/b"},
                {"id": "c", "post_url": "https://ig/p/c"}]

    def list_instagram_post_media(self, project_id):
        return [
            {"post_id": "a", "position": 0, "media_type": "video", "media_url": "https://cdn/a.mp4", "thumbnail_url": "https://cdn/a.jpg"},
            {"post_id": "b", "position": 0, "media_type": "image", "media_url": "https://cdn/b.jpg", "thumbnail_url": None},
            {"post_id": "c", "position": 0, "media_type": "video", "media_url": "https://cdn/c.mp4", "thumbnail_url": None},
        ]


class _Broken:
    def list_instagram_posts(self, project_id):
        raise RuntimeError("no table")


def test_reel_gets_its_cover_photo_gets_itself_and_a_reel_without_cover_gets_nothing() -> None:
    assert post_stills(_Repo(), "p") == {"https://ig/p/a": "https://cdn/a.jpg", "https://ig/p/b": "https://cdn/b.jpg"}


def test_unreadable_media_means_no_pictures_not_an_error() -> None:
    assert post_stills(_Broken(), "p") == {}


def test_gap_examples_and_saved_explanation_posts_get_stills_without_changing_the_original() -> None:
    gap = {"id": "g", "details": {
        "examples": [{"postUrl": "https://ig/p/a", "imageUrl": "https://cdn/a.mp4"}],
        "explanation": {"evidence": [{"post_url": "https://ig/p/c", "image_url": "https://cdn/c.mp4"},
                                     {"post_url": "https://ig/p/b", "image_url": ""}]},
    }}
    stills = post_stills(_Repo(), "p")
    [out] = with_stills([gap], stills)
    assert out["details"]["examples"][0]["imageUrl"] == "https://cdn/a.jpg"
    assert [e["image_url"] for e in out["details"]["explanation"]["evidence"]] == ["", "https://cdn/b.jpg"]
    assert gap["details"]["examples"][0]["imageUrl"] == "https://cdn/a.mp4"      # the stored gap is untouched
    plain = {"id": "old"}
    assert with_stills([plain], stills) == [plain]


def test_new_explanation_posts_get_stills() -> None:
    evidence = [{"post_url": "https://ig/p/a", "image_url": "https://cdn/a.mp4"}, {"post_url": "https://ig/p/zz", "image_url": "https://cdn/z.mp4"}]
    fill_evidence(evidence, post_stills(_Repo(), "p"))
    assert [e["image_url"] for e in evidence] == ["https://cdn/a.jpg", ""]
