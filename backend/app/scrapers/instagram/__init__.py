"""Instagram scraper.

Everything Instagram-specific lives in this folder and nowhere else:

    client.py     the two Apify actor runs (posts, then their comments)
    extract.py    one actor item -> caption, hashtags, media, engagement counts
    selectors.py  the actor id, its output paths, and every limit

Instagram itself is never contacted by this project: the standalone scraper's
approach is kept exactly, which is to let Apify's hosted Instagram actor do the
fetching and return JSON. Only publicly viewable content is read; no login is
performed and no access control is worked around.

This module is the thin adapter presenting it through the platform-neutral
:class:`SourceScraper` contract.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlsplit

from app.core.config import settings
from app.scrapers.base import ScrapedDocument, ScrapedSourceRecord, ScraperError, SourceScraper
from app.scrapers.instagram import client, extract
from app.scrapers.instagram import selectors as S

logger = logging.getLogger("optistratix.scrapers.instagram")

#: Each post contributes these, chunked and embedded separately so retrieval
#: can be scoped to, say, comments alone.
TEXT_FIELD_TYPES = ["caption", "hashtags", "comments"]

_USERNAME_RE = re.compile(S.USERNAME_PATTERN)


class InstagramSourceScraper(SourceScraper):
    kind = "instagram"
    label = "Instagram"
    url_hint = "A public Instagram profile link"
    url_example = "https://www.instagram.com/yourpage"
    #: Every post is recorded as a social post in ``scraped_sources``.
    source_kind = "social_post"
    text_field_types = tuple(TEXT_FIELD_TYPES)

    @classmethod
    def is_available(cls) -> bool:
        return settings.has_apify

    @classmethod
    def unavailable_reason(cls) -> str:
        return (
            "Instagram scraping needs an Apify API token. Add APIFY_API_TOKEN to backend/.env "
            "and restart the server."
        )

    def username(self, url: str) -> str | None:
        """The profile name in a link, or None when it is not a profile link."""
        parts = urlsplit((url or "").strip())
        segments = [segment for segment in (parts.path or "").split("/") if segment]
        if not segments:
            return None
        first = segments[0]
        if first.lower() in S.RESERVED_PATH_SEGMENTS or not _USERNAME_RE.match(first):
            return None
        return first

    def canonical_url(self, url: str) -> str:
        """One key per profile, whatever the link looks like."""
        name = self.username(url)
        if not name:
            return (url or "").strip().lower()
        return S.CANONICAL_PROFILE_URL.format(username=name.lower())

    def validate_url(self, url: str) -> None:
        """Shape check only -- the link is never fetched here."""
        value = (url or "").strip()
        if not value:
            raise ScraperError("Instagram URL is empty.")

        parts = urlsplit(value)
        if parts.scheme not in ("http", "https"):
            raise ScraperError(f"Invalid URL '{value[:80]}': must start with http:// or https://")

        host = (parts.hostname or "").lower()
        if host != S.ALLOWED_HOST_SUFFIX and not host.endswith("." + S.ALLOWED_HOST_SUFFIX):
            raise ScraperError(
                f"'{host or value[:80]}' is not an Instagram address. Paste a profile link, "
                "e.g. https://www.instagram.com/yourpage"
            )

        if not self.username(value):
            raise ScraperError(
                "That Instagram link is not a profile. Paste the profile link, e.g. "
                "https://www.instagram.com/yourpage"
            )

    def scrape(self, url: str, role: str) -> ScrapedSourceRecord:
        """Reads one public profile: its recent posts, and their comments."""
        self.validate_url(url)
        if not self.is_available():
            raise ScraperError(self.unavailable_reason())

        profile_url = self.canonical_url(url)
        posts_limit = min(settings.instagram_posts_limit, S.MAX_POSTS_PER_PROFILE)
        comments_limit = min(settings.instagram_comments_limit, S.MAX_COMMENTS_PER_POST)

        items = client.fetch_profile_posts(profile_url, posts_limit)
        warnings: list[str] = []
        # The profile run only nests the newest 12 posts. For more, a "posts" run reads them directly; the profile
        # run is still what the name, followers and bio come from.
        more: list[dict] = []
        if posts_limit > S.DETAILS_POSTS_CAP:
            try:
                more = client.fetch_more_posts(profile_url, posts_limit)
            except ScraperError as exc:
                logger.warning("Extra Instagram posts could not be read for %s: %s", profile_url, exc)
                warnings.append(f"Only the newest {S.DETAILS_POSTS_CAP} posts could be read ({exc}).")
        records: list[dict] = []
        seen_posts: set[str] = set()
        for input_url, post in [*client.iter_posts(more), *client.iter_posts(items)]:
            record = extract.extract_post(input_url or profile_url, post)
            if not record:
                continue
            # One row per post. A profile occasionally lists the same post
            # twice, and a duplicate would be rejected by storage for the whole
            # batch rather than on its own.
            post_url = record.get("post_url")
            if post_url:
                if post_url in seen_posts:
                    continue
                seen_posts.add(post_url)
            records.append(record)
            if len(records) >= posts_limit:
                break

        # The extra-posts run can also "succeed" with nothing (Instagram blocked it, or the Apify run was cut short
        # for credit or memory). Then only the profile run's 12 posts are left: say so, instead of silently showing
        # fewer posts than the profile has.
        total = next((item.get("postsCount") for item in items if isinstance(item, dict) and isinstance(item.get("postsCount"), int)), None)
        if (records and len(records) < posts_limit and not any("could be read" in w for w in warnings)
                and (total > len(records) if total is not None else len(records) >= S.DETAILS_POSTS_CAP)):
            warnings.append(
                f"Only {len(records)} posts could be read for this profile"
                + (f" (it has {total:,})" if total else "")
                + ". The request for more posts returned nothing: Apify may be out of credit or busy, or Instagram "
                "blocked it. Scrape again later to read up to "
                f"{posts_limit}."
            )

        if not records:
            raise ScraperError(
                f"No public posts were found for {profile_url}. The profile may be private, "
                "empty, or the link may be wrong."
            )

        comments_by_post: dict[str, list[dict]] = {}
        if comments_limit > 0:
            # Reading comments is a second actor run and the slowest part of a
            # social scrape, so its cost is bounded by the post budget rather
            # than by skipping posts: every post that was collected gets its
            # comments, because every post can be opened on the results screen.
            # Setting INSTAGRAM_COMMENT_POSTS_LIMIT above 0 caps it again, and
            # the busiest posts are then the ones that keep their comments.
            ranked = sorted(
                (record for record in records if record.get("post_url")),
                key=lambda record: record.get("engagement_count") or 0,
                reverse=True,
            )
            cap = settings.instagram_comment_posts_limit
            if cap > 0:
                ranked = ranked[:cap]
            post_urls = [record["post_url"] for record in ranked]
            try:
                comments_by_post = extract.extract_comments(
                    client.fetch_post_comments(post_urls, comments_limit)
                )
            except ScraperError as exc:
                # The posts are already collected; losing their comments is a
                # thinner result, not a failed scrape.
                logger.warning("Instagram comments could not be read for %s: %s", profile_url, exc)
                warnings.append(f"Comments could not be collected ({exc}).")

        # The profile's own name, from the profile item the actor returned.
        # Not from a post: ownerUsername there is the post's author, and on a
        # collaboration post that is the other account, which is exactly how a
        # profile came to be displayed under a stranger's handle.
        username = extract.profile_username(items) or self.username(url) or profile_url
        # Followers, bio, highlights...: what the engagement model grades a
        # profile on. Stored on every post row, the same way as the username.
        stats = extract.profile_stats(items)
        if not stats:
            warnings.append(
                "Profile details (followers, bio) were not returned, so this side "
                "cannot be graded by the engagement model."
            )
        for record in records:
            record["profile_username"] = username
            record["profile_stats"] = stats

        documents = [
            self._document(record, comments_by_post.get(record.get("post_url") or "", []))
            for record in records
        ]

        return ScrapedSourceRecord(
            role=role,
            kind=self.kind,
            url=profile_url,
            title=f"@{username}",
            documents=documents,
            method="apify",
            warnings=warnings,
        )

    @staticmethod
    def _document(record: dict, comments: list[dict]) -> ScrapedDocument:
        caption = record.get("caption") or ""
        metadata = {key: value for key, value in record.items() if key != "media"}
        metadata["collected_comment_count"] = len(comments)

        return ScrapedDocument(
            url=record.get("post_url") or record.get("profile_url") or "",
            title=(caption.splitlines()[0] if caption else "Instagram post")[:200],
            excerpt=caption[: S.EXCERPT_LENGTH],
            text_fields=extract.post_text_fields(record, comments),
            metadata=metadata,
            children={"media": record.get("media") or [], "comments": comments},
        )


__all__ = ["InstagramSourceScraper", "TEXT_FIELD_TYPES"]
