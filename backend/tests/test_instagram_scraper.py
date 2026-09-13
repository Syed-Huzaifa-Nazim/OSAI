"""The Instagram scraper, with Apify replaced by canned actor output.

Instagram is never contacted by this project: Apify's hosted actor does the
fetching. These tests stand in for that actor, so the parts this repo owns --
reading its output, the two-run flow, and what gets stored -- are covered
without spending a credit or touching the network.

The fixtures are shaped like real actor items, including the awkward parts: a
profile run that nests its posts, a carousel, a caption whose hashtags are not
listed separately, and a comments run keyed by post URL.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.config import settings
from app.scrapers import ScraperError, get_source_scraper
from app.scrapers.instagram import InstagramSourceScraper
from app.scrapers.instagram import client as client_module
from app.scrapers.instagram import extract

POST_ONE: dict[str, Any] = {
    "url": "https://www.instagram.com/p/AAA111/",
    "ownerUsername": "verdantroast",
    "caption": "New single origin landed this morning.\nRoasted Tuesday, shipped Wednesday.",
    "hashtags": ["coffee", "SingleOrigin"],
    "likesCount": 412,
    "commentsCount": 17,
    "timestamp": "2026-09-01T08:30:00.000Z",
    "type": "Sidecar",
    "displayUrl": "https://scontent.test/one.jpg",
    "childPosts": [
        {"type": "Image", "displayUrl": "https://scontent.test/one-a.jpg"},
        {"type": "Video", "videoUrl": "https://scontent.test/one-b.mp4"},
    ],
    "locationName": "Lahore",
}

POST_TWO: dict[str, Any] = {
    "url": "https://www.instagram.com/p/BBB222/",
    "ownerUsername": "verdantroast",
    # No hashtags array: they have to be read off the caption.
    "caption": "Cold brew season is here #coldbrew #summer",
    "likesCount": 98,
    "commentsCount": 3,
    "timestamp": 1788246000,
    "type": "Video",
    "videoUrl": "https://scontent.test/two.mp4",
    "videoViewCount": 5400,
    "isSponsored": True,
}

#: A profile run returns one item per profile, with the posts nested inside it.
PROFILE_ITEMS = [{
    "inputUrl": "https://www.instagram.com/verdantroast/",
    "username": "verdantroast",
    "latestPosts": [POST_ONE, POST_TWO],
}]

COMMENT_ITEMS = [
    {
        "postUrl": "https://www.instagram.com/p/AAA111/",
        "ownerUsername": "coffee_fan",
        "text": "Ordered this morning, cannot wait.",
        "likesCount": 4,
        "timestamp": "2026-09-01T09:00:00.000Z",
    },
    {
        "postUrl": "https://www.instagram.com/p/AAA111/",
        "owner": {"username": "brewnerd"},
        "text": "Any plans for a decaf?",
        "likesCount": 1,
    },
    {"postUrl": "https://www.instagram.com/p/AAA111/", "text": ""},   # empty: dropped
]

PROFILE_URL = "https://www.instagram.com/verdantroast/"


@pytest.fixture
def apify(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stands in for the actor. Records what each run was asked for."""
    state: dict[str, Any] = {
        "posts": list(PROFILE_ITEMS),
        "comments": list(COMMENT_ITEMS),
        "post_runs": [],
        "comment_runs": [],
    }

    def fake_posts(profile_url: str, limit: int) -> list[dict[str, Any]]:
        state["post_runs"].append((profile_url, limit))
        result = state["posts"]
        if isinstance(result, BaseException):
            raise result
        return result

    def fake_comments(post_urls: list[str], limit: int) -> list[dict[str, Any]]:
        state["comment_runs"].append((list(post_urls), limit))
        result = state["comments"]
        if isinstance(result, BaseException):
            raise result
        return result

    monkeypatch.setattr(client_module, "fetch_profile_posts", fake_posts)
    monkeypatch.setattr(client_module, "fetch_post_comments", fake_comments)
    monkeypatch.setattr(settings, "apify_api_token", "test-token")
    return state


# =================================================================== extract


def test_a_post_is_reduced_to_its_business_facts() -> None:
    record = extract.extract_post(PROFILE_URL, POST_ONE)

    assert record["post_url"] == "https://www.instagram.com/p/AAA111/"
    assert record["owner_username"] == "verdantroast"
    assert record["caption"].startswith("New single origin landed this morning.")
    assert record["hashtags"] == ["coffee", "SingleOrigin"]
    assert (record["like_count"], record["comment_count"]) == (412, 17)
    assert record["engagement_count"] == 429
    assert record["location_name"] == "Lahore"
    assert record["posted_at"] == "2026-09-01T08:30:00.000Z"
    assert record["caption_word_count"] > 5
    # A carousel keeps every slide, in order.
    assert [item["media_url"] for item in record["media"]] == [
        "https://scontent.test/one-a.jpg",
        "https://scontent.test/one-b.mp4",
    ]
    assert record["media_count"] == 2


def test_hashtags_are_read_off_the_caption_when_the_actor_lists_none() -> None:
    record = extract.extract_post(PROFILE_URL, POST_TWO)
    assert record["hashtags"] == ["coldbrew", "summer"]
    assert record["hashtag_count"] == 2
    assert record["is_sponsored"] is True
    assert record["video_view_count"] == 5400
    # Epoch seconds turn up on some actor versions.
    assert (record["posted_at"] or "").startswith("2026-")


def test_comments_are_grouped_by_post_and_empty_ones_dropped() -> None:
    grouped = extract.extract_comments(COMMENT_ITEMS)
    comments = grouped["https://www.instagram.com/p/AAA111/"]

    assert [comment["commenter_username"] for comment in comments] == ["coffee_fan", "brewnerd"]
    assert comments[0]["like_count"] == 4
    assert all(comment["comment_text"] for comment in comments)


def test_text_fields_say_so_when_there_is_nothing() -> None:
    fields = extract.post_text_fields({"caption": "", "hashtags": []}, [])
    assert fields["caption"] == "No caption on this post."
    assert "No hashtags" in fields["hashtags"]
    assert "No comments" in fields["comments"]


def test_malformed_actor_items_do_not_raise() -> None:
    assert extract.extract_post(PROFILE_URL, {}) == {}
    assert extract.extract_comments([None, "nope", {}]) == {}          # type: ignore[list-item]
    weird = extract.extract_post(PROFILE_URL, {
        "url": "https://www.instagram.com/p/CCC/",
        "caption": None,
        "hashtags": "not a list",
        "likesCount": "1,204",
        "commentsCount": None,
        "childPosts": "not a list",
        "timestamp": "",
    })
    assert weird["like_count"] == 1204
    assert weird["hashtags"] == [] and weird["media"] == []
    assert weird["posted_at"] is None


# =================================================================== adapter


@pytest.mark.parametrize(
    ("url", "username"),
    [
        ("https://www.instagram.com/verdantroast/", "verdantroast"),
        ("https://instagram.com/verdant.roast_1", "verdant.roast_1"),
        ("https://m.instagram.com/verdantroast?hl=en", "verdantroast"),
    ],
)
def test_a_profile_link_is_understood(url: str, username: str) -> None:
    assert InstagramSourceScraper().username(url) == username


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("", "empty"),
        ("ftp://instagram.com/verdantroast", "http"),
        ("https://www.facebook.com/verdantroast", "not an Instagram address"),
        ("https://instagram.com.evil.example/verdantroast", "not an Instagram address"),
        ("https://notinstagram.com/verdantroast", "not an Instagram address"),
        ("https://www.instagram.com/", "not a profile"),
        ("https://www.instagram.com/p/AAA111/", "not a profile"),
        ("https://www.instagram.com/explore/tags/coffee/", "not a profile"),
    ],
)
def test_anything_but_a_profile_link_is_refused(url: str, message: str) -> None:
    with pytest.raises(ScraperError, match=message):
        InstagramSourceScraper().validate_url(url)


def test_one_key_per_profile_however_the_link_is_written() -> None:
    scraper = InstagramSourceScraper()
    keys = {
        scraper.canonical_url("https://www.instagram.com/VerdantRoast/"),
        scraper.canonical_url("https://instagram.com/verdantroast"),
        scraper.canonical_url("https://m.instagram.com/verdantroast?hl=en"),
    }
    assert keys == {"https://www.instagram.com/verdantroast/"}


def test_a_profile_scrape_returns_a_document_per_post(apify: dict[str, Any]) -> None:
    record = get_source_scraper("instagram").scrape(PROFILE_URL, "own")

    assert (record.kind, record.role, record.method) == ("instagram", "own", "apify")
    assert record.title == "@verdantroast"
    assert record.url == PROFILE_URL
    assert len(record.documents) == 2

    first = record.documents[0]
    assert first.url == "https://www.instagram.com/p/AAA111/"
    assert set(first.text_fields) == {"caption", "hashtags", "comments"}
    assert "#coffee" in first.text_fields["hashtags"]
    assert "Ordered this morning" in first.text_fields["comments"]
    assert first.metadata["like_count"] == 412
    assert first.metadata["collected_comment_count"] == 2
    assert len(first.children["media"]) == 2
    assert len(first.children["comments"]) == 2
    # The actor's raw payload is never carried through.
    assert "childPosts" not in first.metadata and "raw_data" not in first.metadata


def test_both_runs_are_asked_for_what_the_settings_allow(apify: dict[str, Any]) -> None:
    get_source_scraper("instagram").scrape(PROFILE_URL, "own")

    assert apify["post_runs"] == [(PROFILE_URL, settings.instagram_posts_limit)]
    asked_urls, comment_limit = apify["comment_runs"][0]
    assert asked_urls == [
        "https://www.instagram.com/p/AAA111/",
        "https://www.instagram.com/p/BBB222/",
    ]
    assert comment_limit == settings.instagram_comments_limit


def test_the_profile_is_named_after_the_link_not_its_newest_post(
    apify: dict[str, Any],
) -> None:
    """A collaboration post is authored by the OTHER account.

    Instagram shows a collaboration on both collaborators' profiles, and the
    actor reports the originating author in ``ownerUsername``. Naming the
    profile after its newest post therefore labelled a profile with a
    stranger's handle, which is exactly what happened in the field. The name
    comes from the profile item; the post keeps its own author.
    """
    collaboration = {**POST_ONE, "ownerUsername": "beingssinglemom"}
    apify["posts"] = [{
        "inputUrl": PROFILE_URL,
        "username": "verdantroast",
        "followersCount": 5120,
        "latestPosts": [collaboration, POST_TWO],
    }]

    record = get_source_scraper("instagram").scrape(PROFILE_URL, "own")

    assert record.title == "@verdantroast"
    assert all(
        document.metadata["profile_username"] == "verdantroast"
        for document in record.documents
    )
    # The post's own author is still recorded, which is how the screen can say
    # the post was a collaboration.
    assert record.documents[0].metadata["owner_username"] == "beingssinglemom"


def test_the_profile_name_falls_back_to_the_submitted_link() -> None:
    """An actor version that returns no profile item must not rename anything."""
    assert extract.profile_username([POST_ONE, POST_TWO]) is None
    assert extract.profile_username([{"username": "verdantroast"}]) is None
    assert extract.profile_username([{"fullName": "V", "username": "verdantroast"}]) == "verdantroast"


def test_every_collected_post_has_its_comments_read(apify: dict[str, Any]) -> None:
    """Every post can be opened on the results screen, and an opened post shows
    its comments, so the post budget is what bounds the scrape."""
    assert settings.instagram_comment_posts_limit == 0

    get_source_scraper("instagram").scrape(PROFILE_URL, "own")

    asked_urls, _ = apify["comment_runs"][0]
    assert asked_urls == [
        "https://www.instagram.com/p/AAA111/",
        "https://www.instagram.com/p/BBB222/",
    ]


def test_only_the_busiest_posts_have_their_comments_read(
    apify: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Comments are a second actor run and the slowest part of a scrape, so the
    limit exists for anyone who needs to cap it: the busiest posts keep theirs."""
    monkeypatch.setattr(settings, "instagram_comment_posts_limit", 1)

    record = get_source_scraper("instagram").scrape(PROFILE_URL, "own")

    # POST_ONE has 412 likes and 17 comments; POST_TWO has 98 and 3.
    asked_urls, _ = apify["comment_runs"][0]
    assert asked_urls == ["https://www.instagram.com/p/AAA111/"]
    # Both posts are still stored, with their counts; only the quieter one has
    # no comment text behind it.
    assert len(record.documents) == 2
    assert record.documents[0].children["comments"]
    assert record.documents[1].children["comments"] == []


def test_a_post_listed_twice_is_stored_once(apify: dict[str, Any]) -> None:
    """A duplicate would be rejected by storage for the whole batch, not on its
    own, so it never reaches storage."""
    apify["posts"] = [{
        "inputUrl": PROFILE_URL,
        "latestPosts": [POST_ONE, POST_TWO, dict(POST_ONE)],
    }]

    record = get_source_scraper("instagram").scrape(PROFILE_URL, "own")

    urls = [document.url for document in record.documents]
    assert urls == [
        "https://www.instagram.com/p/AAA111/",
        "https://www.instagram.com/p/BBB222/",
    ]


def test_losing_the_comments_is_a_warning_not_a_failed_scrape(apify: dict[str, Any]) -> None:
    apify["comments"] = ScraperError("Apify rejected the API token.")

    record = get_source_scraper("instagram").scrape(PROFILE_URL, "own")

    assert len(record.documents) == 2
    assert any("Comments could not be collected" in warning for warning in record.warnings)
    assert record.documents[0].children["comments"] == []


def test_an_empty_or_private_profile_is_reported_plainly(apify: dict[str, Any]) -> None:
    apify["posts"] = []
    with pytest.raises(ScraperError, match="No public posts"):
        get_source_scraper("instagram").scrape(PROFILE_URL, "own")


def test_a_profile_that_comes_back_without_posts_is_not_stored_as_one(
    apify: dict[str, Any],
) -> None:
    """The actor sometimes answers with the profile alone, posts and all
    missing. Seen live. That is a profile with nothing readable, not a post,
    and treating it as one put a tile in the grid with no picture, no author
    and no caption -- while reporting the scrape as a success."""
    apify["posts"] = [{
        "inputUrl": PROFILE_URL,
        "url": PROFILE_URL,
        "username": "verdantroast",
        "followersCount": 5120,
        "latestPosts": [],
    }]

    with pytest.raises(ScraperError, match="No public posts"):
        get_source_scraper("instagram").scrape(PROFILE_URL, "own")


def test_without_a_token_instagram_reports_itself_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "apify_api_token", "")
    assert InstagramSourceScraper.is_available() is False
    with pytest.raises(ScraperError, match="Apify API token"):
        InstagramSourceScraper().scrape(PROFILE_URL, "own")


def test_the_post_and_comment_limits_are_capped(monkeypatch: pytest.MonkeyPatch, apify: dict) -> None:
    """A configuration mistake must not turn into an unbounded Apify bill."""
    monkeypatch.setattr(settings, "instagram_posts_limit", 10_000)
    monkeypatch.setattr(settings, "instagram_comments_limit", 10_000)

    get_source_scraper("instagram").scrape(PROFILE_URL, "own")

    assert apify["post_runs"][0][1] == 50
    assert apify["comment_runs"][0][1] == 50
