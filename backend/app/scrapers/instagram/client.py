"""Talking to Apify's hosted Instagram actor.

The only place this project touches Apify. Two calls: the posts on a profile,
and the comments on those posts. Both return the actor's raw items; turning
them into records is extract.py's job.

Every failure becomes a :class:`ScraperError` whose message is written for the
user, because that is what the pipeline shows on the failed stage.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.scrapers.base import ScraperError
from . import selectors as S

log = logging.getLogger("optistratix.scrapers.instagram")


def _client() -> Any:
    """An authenticated Apify client, or a clear error about the token."""
    if not settings.apify_api_token:
        raise ScraperError(
            "Instagram scraping needs an Apify API token. Add APIFY_API_TOKEN to backend/.env "
            "and restart the server."
        )
    try:
        from apify_client import ApifyClient
    except ImportError as exc:  # pragma: no cover - listed in requirements.txt
        raise ScraperError(
            "The apify-client package is not installed. Run: pip install -r requirements.txt"
        ) from exc
    return ApifyClient(settings.apify_api_token)


def _run_actor(client: Any, run_input: dict[str, Any]) -> list[dict[str, Any]]:
    """Runs the actor to completion and returns its dataset items."""
    actor_id = settings.apify_instagram_actor_id or S.DEFAULT_ACTOR_ID
    try:
        run = client.actor(actor_id).call(run_input=run_input)
    except Exception as exc:  # noqa: BLE001 - the client raises several unrelated types
        message = str(exc)
        if "401" in message or "unauthor" in message.lower() or "token" in message.lower():
            raise ScraperError(
                "Apify rejected the API token. Check APIFY_API_TOKEN in backend/.env."
            ) from exc
        raise ScraperError(f"Apify could not run the Instagram scraper ({message}).") from exc

    if not run or not run.get("defaultDatasetId"):
        raise ScraperError("Apify returned no dataset for the Instagram run.")

    status = (run.get("status") or "").upper()
    if status not in ("SUCCEEDED", "READY", ""):
        log.warning("Apify run finished with status %s", status)

    try:
        return list(client.dataset(run["defaultDatasetId"]).iterate_items())
    except Exception as exc:  # noqa: BLE001
        raise ScraperError(f"Apify returned a dataset that could not be read ({exc}).") from exc


def fetch_profile_posts(profile_url: str, limit: int) -> list[dict[str, Any]]:
    """Public posts on one profile, newest first, as the actor returns them."""
    client = _client()
    items = _run_actor(
        client,
        {
            "directUrls": [profile_url],
            "resultsType": S.RESULTS_TYPE_POSTS,
            "resultsLimit": limit,
        },
    )
    return items


def fetch_post_comments(post_urls: list[str], limit: int) -> list[dict[str, Any]]:
    """Comments on the given posts. A second actor run, so it is optional."""
    if not post_urls:
        return []
    client = _client()
    return _run_actor(
        client,
        {
            "directUrls": post_urls,
            "resultsType": S.RESULTS_TYPE_COMMENTS,
            "resultsLimit": limit,
        },
    )


def iter_posts(items: list[dict[str, Any]]):
    """Yields ``(profile_url, post)`` from whichever shape the actor returned.

    A profile run nests the posts under the profile item; a direct post run
    returns them at the top level. Both shapes come back from the same actor
    depending on the link, so both are handled.
    """
    for item in items:
        if not isinstance(item, dict):
            continue
        nested = item.get(S.NESTED_POSTS_KEY)
        profile_url = item.get("inputUrl") or item.get("url")
        if isinstance(nested, list) and nested:
            for post in nested:
                if isinstance(post, dict):
                    yield profile_url, post
        elif any(key in item for key in S.PROFILE_MARKER_KEYS):
            # A profile item carrying no posts is a profile with nothing public
            # to read, not a post. The actor does answer this way sometimes.
            # Yielding it would store the profile itself as a phantom post:
            # no media, no author, no caption, and a tile in the grid for it.
            continue
        else:
            yield profile_url, item
