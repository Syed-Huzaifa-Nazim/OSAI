"""Website and Instagram comparisons end to end, through the HTTP API.

Only the two scrapers and Chroma are replaced. Routing, the scrape runner,
stage 2 persistence, stage 3 embedding and the read-back are all real, so what
is covered here is everything around the scrapers rather than the scrapers
themselves (they have their own test files).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.scrapers import ScrapedDocument, ScrapedSourceRecord, ScraperError
from app.scrapers.instagram import InstagramSourceScraper
from app.scrapers.website import WebsiteSourceScraper
from app.services.repository import MemoryRepository, get_repository
from app.vectorstore import chroma

OWN_SITE = "https://verdantroast.example"
RIVAL_SITE = "https://northbrew.example"
OWN_PROFILE = "https://www.instagram.com/verdantroast/"
RIVAL_PROFILE = "https://www.instagram.com/northbrew/"

WEBSITE_INTAKE = {
    "brandName": "Verdant Roast",
    "brandWebsite": OWN_SITE,
    "brandDescription": "Small-batch speciality coffee roaster.",
    "industry": "ecommerce",
    "objectives": ["Grow direct subscriptions"],
    "comparisonType": "website",
    "competitors": [{"name": "Northbrew", "landingPageUrl": RIVAL_SITE}],
}

INSTAGRAM_INTAKE = {
    **WEBSITE_INTAKE,
    "comparisonType": "social_media",
    "socialPlatform": "instagram",
    "brandWebsite": OWN_PROFILE,
    "competitors": [{"name": "Northbrew", "landingPageUrl": RIVAL_PROFILE}],
}


def _page_document(site: str, path: str, depth: int) -> ScrapedDocument:
    url = f"{site}{path}" if path else site
    return ScrapedDocument(
        url=url,
        title=f"{site} {path or 'home'}".strip(),
        excerpt="Roasted weekly in small batches.",
        text_fields={
            "page_text": "Every bag is roasted to order and shipped within 24 hours. " * 3,
            "headings": "Roasted weekly\nSubscriptions",
            "meta": "Verdant Roast\nSmall-batch coffee.",
        },
        metadata={
            "page_url": url,
            "canonical_url": url,
            "status_code": 200,
            "title": "Verdant Roast",
            "meta_description": "Small-batch coffee.",
            "headings": [{"level": "h1", "text": "Roasted weekly"}],
            "links": [{"url": f"{site}/shop", "text": "Shop"}],
            "heading_count": 1,
            "link_count": 1,
            "cleaned_text": "Every bag is roasted to order.",
            "word_count": 7,
            "content_hash": "a" * 64,
            "renderer": "http",
            "depth": depth,
            "is_root": depth == 0,
            # The facts the A-F parameters are derived from. A small, realistic
            # set: enough for the comparison to score something meaningful.
            "signals": {
                "above_fold_words": 40,
                "h1_count": 1,
                "heading_hierarchy_ok": True,
                "title_length": 30,
                "has_meta_description": True,
                "meta_description_length": 80,
                "internal_link_count": 12,
                "external_link_count": 2,
                "url_is_clean": True,
                "has_canonical": True,
                "has_og_tags": True,
                "has_viewport_meta": True,
                "has_lang_attribute": True,
                "has_nav_landmark": True,
                "nav_link_count": 6,
                "image_count": 4,
                "images_with_alt": 4,
                "responsive_image_count": 1,
                "script_count": 5,
                "stylesheet_count": 1,
                "paragraph_count": 8,
                "list_count": 2,
                "media_embed_count": 0,
                "social_proof_hits": ["testimonial"],
                "certification_hits": [],
                "has_about_link": True,
                "has_contact_link": True,
                "has_email_link": True,
                "has_phone_link": False,
                "cta_count": 2,
                "cta_labels": ["get started"],
                "form_count": 1,
                "form_field_count": 3,
                "has_newsletter_signup": False,
                "has_pricing_link": True,
                "mentions_contact_for_pricing": False,
                "is_https": True,
                "has_privacy_link": True,
                "has_terms_link": True,
                "has_cookie_notice": False,
                "analytics_tools": ["Google Analytics"],
                "chat_tools": [],
                "payment_tools": [],
                "is_editorial": False,
                "published_at": None,
                "has_robots_txt": depth == 0,
                "has_sitemap": depth == 0,
                "sitemap_url_count": 12 if depth == 0 else 0,
            },
        },
        children={
            "images": [
                {
                    "image_url": f"{site}/static/social-card.jpg",
                    "source": "og_image",
                    "alt_text": None,
                    "width": None,
                    "height": None,
                    "is_primary": True,
                },
                {
                    "image_url": f"{site}/static/hero.jpg",
                    "source": "hero",
                    "alt_text": "Beans on a table",
                    "width": 1200,
                    "height": 600,
                    "is_primary": False,
                },
            ],
        },
    )


def _post_document(profile: str, code: str, likes: int) -> ScrapedDocument:
    post_url = f"https://www.instagram.com/p/{code}/"
    return ScrapedDocument(
        url=post_url,
        title="New single origin landed",
        excerpt="New single origin landed this morning.",
        text_fields={
            "caption": "New single origin landed this morning. " * 4,
            "hashtags": "#coffee #singleorigin",
            "comments": "Ordered this morning.\nAny plans for a decaf?",
        },
        metadata={
            "profile_url": profile,
            "post_url": post_url,
            "profile_username": "verdantroast",
            "owner_username": "verdantroast",
            "caption": "New single origin landed this morning.",
            "caption_length": 38,
            "caption_word_count": 6,
            "hashtags": ["coffee", "singleorigin"],
            "hashtag_count": 2,
            "like_count": likes,
            "comment_count": 2,
            "engagement_count": likes + 2,
            "video_view_count": None,
            "media_type": "Image",
            "media_url": "https://scontent.test/a.jpg",
            "media_count": 1,
            "location_name": None,
            "is_sponsored": False,
            "posted_at": "2026-09-01T08:30:00.000Z",
            "collected_comment_count": 2,
        },
        children={
            "media": [{"media_type": "Image", "media_url": "https://scontent.test/a.jpg"}],
            "comments": [
                {
                    "commenter_username": "coffee_fan",
                    "comment_text": "Ordered this morning.",
                    "like_count": 4,
                    "posted_at": "2026-09-01T09:00:00.000Z",
                },
                {
                    "commenter_username": "brewnerd",
                    "comment_text": "Any plans for a decaf?",
                    "like_count": 1,
                    "posted_at": None,
                },
            ],
        },
    )


@pytest.fixture
def stubbed(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    """No network, no vector store; records what would have been stored."""
    calls: dict[str, list] = {"scraped": [], "stored": [], "queried": []}

    def fake_website(self: Any, url: str, role: str) -> ScrapedSourceRecord:
        calls["scraped"].append((role, url))
        # The user's own site yields two pages, the competitor's one.
        paths = ["", "/shop"] if role == "own" else [""]
        return ScrapedSourceRecord(
            role=role,
            kind="website",
            url=url,
            title="Verdant Roast",
            documents=[_page_document(url, path, index) for index, path in enumerate(paths)],
            method="http",
            warnings=["/pricing: HTTP 404"] if role == "own" else [],
        )

    def fake_instagram(self: Any, url: str, role: str) -> ScrapedSourceRecord:
        calls["scraped"].append((role, url))
        codes = ["AAA111", "BBB222"] if role == "own" else ["CCC333"]
        return ScrapedSourceRecord(
            role=role,
            kind="instagram",
            url=url,
            title="@verdantroast",
            documents=[_post_document(url, code, 100 + index) for index, code in enumerate(codes)],
            method="apify",
        )

    def fake_add_chunks(project_id, ids, documents, metadatas, embeddings=None):
        calls["stored"].extend(metadatas)
        return len(ids)

    def fake_query(project_id, text, n_results=8, where=None):
        calls["queried"].append(where)
        clauses = {key: value["$eq"] for clause in where["$and"] for key, value in clause.items()}
        return [{
            "document": f"{clauses['field_type']} passage from the {clauses['role']} side",
            "metadata": {"field_type": clauses["field_type"], "chunk_index": 0},
            "relevance": 0.66,
        }]

    monkeypatch.setattr(WebsiteSourceScraper, "scrape", fake_website)
    monkeypatch.setattr(InstagramSourceScraper, "scrape", fake_instagram)
    monkeypatch.setattr(chroma, "add_chunks", fake_add_chunks)
    monkeypatch.setattr(chroma, "query", fake_query)
    monkeypatch.setattr(chroma, "delete_collection", lambda project_id: None)

    # Instagram chunks go to pgvector; no model download in tests.
    from app.analysis.instagram import embeddings as pg_embeddings

    monkeypatch.setattr(
        pg_embeddings, "embed", lambda texts: [[1.0] + [0.0] * 383 for _ in texts]
    )
    return calls


def _create(client: TestClient, payload: dict[str, Any]) -> str:
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201, response.json()
    return response.json()["id"]


def _scrape(client: TestClient, project_id: str) -> None:
    response = client.post(f"/api/v1/scrapers/projects/{project_id}/scrape")
    assert response.status_code == 200, response.json()


def _sources(client: TestClient, project_id: str) -> list[dict[str, Any]]:
    response = client.get(f"/api/v1/projects/{project_id}/sources")
    assert response.status_code == 200, response.json()
    return response.json()


def _repo() -> MemoryRepository:
    return get_repository("demo-user-0001", "")


# ------------------------------------------------------------------ website


def test_a_website_comparison_scrapes_both_sites(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "complete", state["stages"]["2"]
    assert state["stages"]["3"]["status"] == "complete", state["stages"]["3"]
    # Nothing after the scrape runs: no gaps, no strategy.
    assert all(state["stages"][str(stage)]["status"] == "idle" for stage in range(4, 10))
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "complete"

    assert ("own", OWN_SITE) in stubbed["scraped"]
    assert ("competitor", RIVAL_SITE) in stubbed["scraped"]

    sources = _sources(client, project_id)
    assert len(sources) == 3                      # two own pages, one competitor page
    assert {source["kind"] for source in sources} == {"landing_page"}
    assert all(source["status"] == "embedded" for source in sources)
    assert all(source["chunkCount"] > 0 for source in sources)


def test_crawled_pages_are_stored_with_their_structure(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    pages = _repo().list_website_pages(project_id)
    assert [page["role"] for page in pages] == ["competitor", "own", "own"]

    # Each page's pictures are stored beside it, one row each, keyed to the page.
    images = _repo().list_website_page_images(project_id)
    assert len(images) == 6                        # three pages, two images each
    assert {image["page_id"] for image in images} == {page["id"] for page in pages}
    assert all(image["project_id"] == project_id for image in images)
    assert sorted({image["position"] for image in images}) == [1, 2]

    own_root = next(page for page in pages if page["role"] == "own" and page["is_root"])
    assert own_root["page_url"] == OWN_SITE
    assert own_root["submitted_url"] == OWN_SITE
    assert own_root["renderer"] == "http"
    assert own_root["headings"] == [{"level": "h1", "text": "Roasted weekly"}]
    assert own_root["competitor_id"] is None
    assert set(own_root["text_fields"]) == {"page_text", "headings", "meta"}
    # Every page points at the source row a citation would resolve to.
    source_ids = {source["id"] for source in _sources(client, project_id)}
    assert {page["source_id"] for page in pages} <= source_ids

    rival = next(page for page in pages if page["role"] == "competitor")
    assert rival["competitor_id"] is not None


def test_the_scraped_data_screen_reads_the_pages(client: TestClient, stubbed: dict) -> None:
    """What /documents serves is what the scraped-data page renders."""
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    body = client.get(f"/api/v1/scrapers/projects/{project_id}/documents").json()

    assert body["kind"] == "website"
    assert body["posts"] == []
    assert len(body["pages"]) == 3

    root = next(page for page in body["pages"] if page["role"] == "own" and page["isRoot"])
    assert root["pageUrl"] == OWN_SITE
    assert root["submittedUrl"] == OWN_SITE
    assert root["wordCount"] > 0 and root["headingCount"] == 1 and root["linkCount"] == 1
    assert root["textPreview"].startswith("Every bag is roasted")
    assert root["renderer"] == "http"
    # The full text and the link list stay in the database: the screen shows a
    # preview and the counts, and shipping every link would dwarf the payload.
    assert "cleanedText" not in root and "links" not in root


def test_the_scraped_data_screen_reads_the_posts(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, INSTAGRAM_INTAKE)
    _scrape(client, project_id)

    body = client.get(f"/api/v1/scrapers/projects/{project_id}/documents").json()

    assert body["kind"] == "instagram"
    assert body["pages"] == []
    assert len(body["posts"]) == 3

    post = body["posts"][0]
    assert post["postUrl"].startswith("https://www.instagram.com/p/")
    assert post["profileUsername"] == "verdantroast"
    assert post["ownerUsername"] == "verdantroast"
    assert post["hashtags"] == ["coffee", "singleorigin"]
    assert post["collectedCommentCount"] == 2
    assert post["engagementCount"] >= (post["likeCount"] or 0)
    assert {p["role"] for p in body["posts"]} == {"own", "competitor"}

    # The grid needs the picture and the modal needs the comments, so both come
    # back with the post rather than in a request per post.
    assert [item["mediaUrl"] for item in post["media"]] == ["https://scontent.test/a.jpg"]
    assert [comment["commenterUsername"] for comment in post["comments"]] == [
        "coffee_fan", "brewnerd",
    ]
    assert post["comments"][0]["commentText"] == "Ordered this morning."
    assert [comment["position"] for comment in post["comments"]] == [1, 2]


def test_the_scraped_data_screen_reads_the_page_images(
    client: TestClient, stubbed: dict
) -> None:
    """A comparison judges what a site shows, not only what it says."""
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    body = client.get(f"/api/v1/scrapers/projects/{project_id}/documents").json()
    root = next(page for page in body["pages"] if page["role"] == "own" and page["isRoot"])

    assert [image["source"] for image in root["images"]] == ["og_image", "hero"]
    assert root["images"][0]["imageUrl"].endswith("/static/social-card.jpg")
    assert root["images"][0]["isPrimary"] is True
    assert root["images"][1]["altText"] == "Beans on a table"
    assert [image["position"] for image in root["images"]] == [1, 2]
    # Stored against the page they were found on, and nothing else.
    assert {image["pageId"] for image in root["images"]} == {root["id"]}


def test_a_child_table_that_cannot_be_read_empties_that_list_only(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Most likely cause: the migration has not been applied yet. The posts
    still load; only their comments are missing."""
    def table_missing(self, project_id):
        raise RuntimeError('relation "instagram_post_comments" does not exist')

    project_id = _create(client, INSTAGRAM_INTAKE)
    _scrape(client, project_id)
    monkeypatch.setattr(MemoryRepository, "list_instagram_post_comments", table_missing)

    response = client.get(f"/api/v1/scrapers/projects/{project_id}/documents")

    assert response.status_code == 200
    body = response.json()
    assert len(body["posts"]) == 3
    assert all(post["comments"] == [] for post in body["posts"])
    assert all(post["media"] for post in body["posts"])


def test_a_product_comparison_has_no_pages_or_posts(client: TestClient, stubbed: dict) -> None:
    """The endpoint answers for any project; a listing comparison has neither."""
    from tests.test_ecommerce_scraper import _intake

    response = client.post("/api/v1/projects", json=_intake())
    assert response.status_code == 201, response.json()
    project_id = response.json()["id"]

    body = client.get(f"/api/v1/scrapers/projects/{project_id}/documents").json()
    assert body == {"kind": "", "pages": [], "posts": []}


def test_every_website_field_is_embedded_separately(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    assert {row["field_type"] for row in stubbed["stored"]} == {"page_text", "headings", "meta"}
    assert {row["kind"] for row in stubbed["stored"]} == {"website"}
    assert {row["role"] for row in stubbed["stored"]} == {"own", "competitor"}
    assert all(row["project_id"] == project_id for row in stubbed["stored"])
    assert all(row["source_id"] for row in stubbed["stored"])


# ---------------------------------------------------------------- instagram


def test_an_instagram_comparison_scrapes_both_profiles(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, INSTAGRAM_INTAKE)
    _scrape(client, project_id)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "complete"
    assert state["stages"]["3"]["status"] == "complete"

    sources = _sources(client, project_id)
    assert len(sources) == 3                      # two own posts, one competitor post
    assert {source["kind"] for source in sources} == {"social_post"}
    assert all(source["url"].startswith("https://www.instagram.com/p/") for source in sources)


def test_posts_are_stored_with_their_media_and_comments(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, INSTAGRAM_INTAKE)
    _scrape(client, project_id)

    repo = _repo()
    posts = repo.list_instagram_posts(project_id)
    media = repo.list_instagram_post_media(project_id)
    comments = repo.list_instagram_post_comments(project_id)

    assert len(posts) == 3
    assert {post["role"] for post in posts} == {"own", "competitor"}
    assert posts[0]["owner_username"] == "verdantroast"
    assert posts[0]["hashtags"] == ["coffee", "singleorigin"]
    assert posts[0]["engagement_count"] >= posts[0]["like_count"]

    # One media row per post, two comments per post, each tied to its post.
    assert len(media) == 3
    assert len(comments) == 6
    post_ids = {post["id"] for post in posts}
    assert {row["post_id"] for row in media} <= post_ids
    assert {row["post_id"] for row in comments} <= post_ids
    assert [row["position"] for row in comments[:2]] == [1, 2]
    assert all(row["project_id"] == project_id for row in media + comments)


def test_captions_hashtags_and_comments_are_embedded_separately(
    client: TestClient, stubbed: dict
) -> None:
    project_id = _create(client, INSTAGRAM_INTAKE)
    _scrape(client, project_id)

    from app.services.repository import MemoryRepository

    # Instagram chunks are stored in Postgres (pgvector), never in Chroma.
    assert stubbed["stored"] == []
    rows = [r for r in MemoryRepository._instagram_chunks if r["project_id"] == project_id]
    assert {row["field_type"] for row in rows} == {"caption", "hashtags", "comments"}
    assert {row["role"] for row in rows} == {"own", "competitor"}
    assert all(len(row["embedding"]) == 384 for row in rows)
    assert all(row["post_url"] for row in rows)


# ------------------------------------------------------- website comparison


def test_a_website_is_scored_against_its_competitor(client: TestClient, stubbed: dict) -> None:
    """The same endpoint the product comparison uses, for a site instead."""
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    groups = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison").json()

    assert [group["letter"] for group in groups] == list("ABCDEF")
    assert [group["label"] for group in groups][:2] == ["Content Strategy", "SEO Signals"]

    seo = next(group for group in groups if group["key"] == "seo_signals")
    assert seo["semanticFieldTypes"] == ["meta", "headings"]
    assert seo["metrics"], "a parameter with no rows would render an empty table"
    # Both sides were scraped from the same fixture, so nothing should be ahead.
    assert all(row["winner"] in (None, "tie") for row in seo["metrics"])

    technical = next(group for group in groups if group["key"] == "technical")
    https_row = next(row for row in technical["metrics"] if row["field"] == "is_https")
    assert (https_row["own"], https_row["competitor"]) == (True, True)


def test_one_website_parameter_in_full(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    detail = client.get(
        f"/api/v1/scrapers/projects/{project_id}/comparison/content_strategy"
    ).json()

    assert detail["metadataOnly"] is False
    assert detail["parameter"]["label"] == "Content Strategy"
    assert detail["parameter"]["insights"]
    for side in ("own", "competitor"):
        assert detail[side]["url"].startswith("https://")
        assert detail[side]["snippets"], "a searched parameter should retrieve passages"
        assert {snippet["fieldType"] for snippet in detail[side]["snippets"]} == {
            "page_text", "meta"
        }
        assert detail[side]["derived"]

    # Each side's passages are scoped to that side, so they never cross over.
    roles = {
        clause["role"]["$eq"]
        for where in stubbed["queried"]
        for clause in where["$and"]
        if "role" in clause
    }
    assert roles == {"own", "competitor"}


def test_a_metadata_only_website_parameter_does_not_search(
    client: TestClient, stubbed: dict
) -> None:
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    detail = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison/technical").json()

    assert detail["metadataOnly"] is True
    assert detail["own"]["snippets"] == []
    assert stubbed["queried"] == []


def test_an_unknown_website_parameter_is_a_404(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)
    response = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison/nonsense")
    assert response.status_code == 404


def test_a_social_comparison_has_no_parameters_to_score(
    client: TestClient, stubbed: dict
) -> None:
    """Instagram is shown, not judged: no parameters are defined for it yet."""
    project_id = _create(client, INSTAGRAM_INTAKE)
    _scrape(client, project_id)
    assert client.get(f"/api/v1/scrapers/projects/{project_id}/comparison").json() == []


def test_a_comparison_before_scraping_is_a_404(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, WEBSITE_INTAKE)
    response = client.get(f"/api/v1/scrapers/projects/{project_id}/comparison")
    assert response.status_code == 404


# ------------------------------------------------------------------- rules


def test_the_agent_pipeline_cannot_be_started_on_a_scraped_comparison(
    client: TestClient, stubbed: dict
) -> None:
    for payload in (WEBSITE_INTAKE, INSTAGRAM_INTAKE):
        project_id = _create(client, payload)
        response = client.post(f"/api/v1/projects/{project_id}/scout/run")
        assert response.status_code == 409


def test_scraping_again_replaces_what_was_stored(client: TestClient, stubbed: dict) -> None:
    project_id = _create(client, INSTAGRAM_INTAKE)
    _scrape(client, project_id)
    first = _repo().list_instagram_posts(project_id)
    _scrape(client, project_id)
    second = _repo().list_instagram_posts(project_id)

    assert len(second) == len(first) == 3
    assert {post["id"] for post in second}.isdisjoint({post["id"] for post in first})
    # The old posts' children went with them: no orphans, and no doubling up.
    assert len(_repo().list_instagram_post_comments(project_id)) == 6


def test_a_failed_scrape_is_recorded_in_the_scrapers_own_words(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreachable(self: Any, url: str, role: str) -> ScrapedSourceRecord:
        raise ScraperError("Nothing could be read from the site (HTTP 404).")

    monkeypatch.setattr(WebsiteSourceScraper, "scrape", unreachable)
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "error"
    assert "HTTP 404" in state["stages"]["2"]["error"]
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "failed"


def test_failing_to_store_the_pages_fails_the_scrape_and_says_why(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pages are the result, not an extra.

    Reporting success with nothing stored is exactly what hid a real bug: a
    duplicate post rejected the whole insert, the run still said complete, and
    the screen said "Nothing was collected" with no reason anywhere.
    """
    def table_missing(self, project_id, rows):
        raise RuntimeError('relation "website_pages" does not exist')

    monkeypatch.setattr(MemoryRepository, "replace_website_pages", table_missing)
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "error"
    assert "could not be saved" in state["stages"]["2"]["error"]
    assert "website_pages" in state["stages"]["2"]["error"]
    assert client.get(f"/api/v1/projects/{project_id}").json()["status"] == "failed"


def test_failing_to_store_comments_is_only_a_warning(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A post's comments hang off a post that is already stored: losing them
    thins the result rather than emptying it."""
    def table_missing(self, project_id, rows):
        raise RuntimeError('relation "instagram_post_comments" does not exist')

    monkeypatch.setattr(MemoryRepository, "replace_instagram_post_comments", table_missing)
    project_id = _create(client, INSTAGRAM_INTAKE)
    _scrape(client, project_id)

    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "complete"
    assert len(_repo().list_instagram_posts(project_id)) == 3
    assert _repo().list_instagram_post_comments(project_id) == []


def test_a_post_shared_by_both_profiles_is_kept_for_each_side(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An Instagram collaboration post appears on every collaborator's profile
    under one URL. It belongs to both sides and is counted for both, which is
    why the stored key is (project, role, post_url)."""
    shared = "SHARED1"

    def both_post_the_same_thing(self: Any, url: str, role: str) -> ScrapedSourceRecord:
        return ScrapedSourceRecord(
            role=role, kind="instagram", url=url, title="@verdantroast",
            documents=[_post_document(url, shared, 100)], method="apify",
        )

    monkeypatch.setattr(InstagramSourceScraper, "scrape", both_post_the_same_thing)
    project_id = _create(client, INSTAGRAM_INTAKE)
    _scrape(client, project_id)

    posts = _repo().list_instagram_posts(project_id)
    assert len(posts) == 2
    assert {post["role"] for post in posts} == {"own", "competitor"}
    assert {post["post_url"] for post in posts} == {
        f"https://www.instagram.com/p/{shared}/"
    }


def test_a_comparison_whose_only_competitor_cannot_be_read_fails(
    client: TestClient, stubbed: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def own_only(self: Any, url: str, role: str) -> ScrapedSourceRecord:
        if role == "competitor":
            raise ScraperError("Nothing could be read (HTTP 500).")
        return ScrapedSourceRecord(
            role=role, kind="website", url=url, title="Verdant Roast",
            documents=[_page_document(url, "", 0)], method="http",
        )

    monkeypatch.setattr(WebsiteSourceScraper, "scrape", own_only)
    project_id = _create(client, WEBSITE_INTAKE)
    _scrape(client, project_id)

    # With no competitor there is nothing to compare against, so this one does
    # fail: the single competitor was the whole comparison.
    state = client.get(f"/api/v1/projects/{project_id}/pipeline").json()
    assert state["stages"]["2"]["status"] == "error"
    assert "nothing to compare" in state["stages"]["2"]["error"]
