"""Reading back a website or social comparison for display.

The counterpart of ``ecommerce_comparison_service`` for the comparison types
whose unit is a page or a post. Same output shape, so the comparison page, the
parameter grid and the gap triage screen cannot tell the two apart.

The difference is what a "side" is. A product comparison has one row per side
already; a site has many crawled pages, so each side is summarised first by the
scraper that collected it (``SourceScraper.aggregate``), and the parameters are
built from those two summaries. The summary is computed from storage on every
read, so changing how a parameter scores never needs a re-crawl.

Nothing here writes, and nothing here calls a model.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

from app.core.errors import NotFoundError
from app.scrapers import COMPETITOR, OWN, ScraperError, get_source_scraper, source_kind_for
from app.services.repository import Repository
from app.vectorstore import chroma

logger = logging.getLogger("optistratix.comparison.site")

#: Passages retrieved per text field, per side. Matches the product path.
SNIPPETS_PER_FIELD = 3


def source_kind_of(project: dict[str, Any]) -> str | None:
    """Which source scraper this project's comparison belongs to, if any."""
    return source_kind_for(project.get("comparison_type") or "", project.get("social_platform"))


def _documents(repo: Repository, project: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    readers = {
        "website": repo.list_website_pages,
        "instagram": repo.list_instagram_posts,
    }
    reader = readers.get(kind)
    if reader is None:
        return []
    try:
        return reader(project["id"])
    except Exception as exc:  # noqa: BLE001 - an unreadable table is an empty comparison
        logger.warning("Could not read %s documents for %s: %s", kind, project["id"], exc)
        return []


def load_sides(
    repo: Repository, project_id: str, competitor_id: str | None = None
) -> tuple[dict[str, Any], Any, list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """(project, scraper, own documents, competitor documents, competitor id).

    A project can compare against several competitors; the page shows one at a
    time. With none named, the first one that has documents is used.
    """
    project = repo.get_project(project_id)  # 404s unless the caller owns it
    kind = source_kind_of(project)
    if kind is None:
        raise NotFoundError("This project is not a website or social comparison.")

    documents = _documents(repo, project, kind)
    own = [row for row in documents if row.get("role") == OWN]
    rivals = [row for row in documents if row.get("role") == COMPETITOR]

    if not own or not rivals:
        raise NotFoundError(
            "This comparison has not been scraped yet. Start the scrape and try again."
        )

    if competitor_id:
        chosen = [row for row in rivals if row.get("competitor_id") == competitor_id]
        if not chosen:
            raise NotFoundError("That competitor is not part of this comparison.")
    else:
        first = rivals[0].get("competitor_id")
        chosen = [row for row in rivals if row.get("competitor_id") == first]
        competitor_id = first

    try:
        scraper = get_source_scraper(kind)
    except ScraperError as exc:
        raise NotFoundError(str(exc)) from exc

    return project, scraper, own, chosen, competitor_id


def scoreboard(
    repo: Repository, project_id: str, competitor_id: str | None = None
) -> list[dict[str, Any]]:
    """Every parameter group with its metric rows and who leads it."""
    _project, scraper, own, rivals, _chosen = load_sides(repo, project_id, competitor_id)
    return scraper.build_metrics(scraper.aggregate(own), scraper.aggregate(rivals))


def parameter_detail(
    repo: Repository,
    project_id: str,
    parameter_key: str,
    competitor_id: str | None = None,
) -> dict[str, Any]:
    """One parameter: metric rows, the read-out, and retrieved passages."""
    project, scraper, own, rivals, chosen = load_sides(repo, project_id, competitor_id)
    groups = scraper.build_metrics(scraper.aggregate(own), scraper.aggregate(rivals))

    group = next((item for item in groups if item["key"] == parameter_key), None)
    if group is None:
        valid = ", ".join(item["key"] for item in groups)
        raise NotFoundError(f"Unknown comparison parameter '{parameter_key}'. Valid: {valid}.")

    field_types = group.get("semantic_field_types") or []
    query = group.get("query")

    return {
        "parameter": group,
        "metadata_only": not field_types,
        "own": _side(project, own, OWN, None, group["own_derived"], field_types, query),
        "competitor": _side(
            project, rivals, COMPETITOR, chosen, group["competitor_derived"], field_types, query
        ),
    }


def _side(
    project: dict[str, Any],
    documents: list[dict[str, Any]],
    role: str,
    competitor_id: str | None,
    derived: dict[str, Any],
    field_types: list[str],
    query: str | None,
) -> dict[str, Any]:
    first = documents[0] if documents else {}
    url = first.get("submitted_url") or first.get("page_url") or first.get("profile_url") or ""
    host = (urlsplit(url).hostname or url) if url else "Not scraped"

    return {
        # The side's identity for the UI. A site has no single row id, so the
        # competitor it belongs to names it; the user's own side is "own".
        "product_id": competitor_id or role,
        "role": role,
        "product_name": first.get("owner_username") and f"@{first['owner_username']}" or host,
        "url": url,
        "snippets": _snippets(project["id"], role, competitor_id, field_types, query),
        "derived": derived,
    }


def _snippets(
    project_id: str,
    role: str,
    competitor_id: str | None,
    field_types: list[str],
    query: str | None,
) -> list[dict[str, Any]]:
    """The most relevant stored passages for one side, best first.

    Scoped by role rather than by document: a side is the whole site, so the
    passage that answers the question may be on any page of it.
    """
    if not field_types or not query:
        return []

    snippets: list[dict[str, Any]] = []
    for field_type in field_types:
        clauses: list[dict[str, Any]] = [
            {"role": {"$eq": role}},
            {"field_type": {"$eq": field_type}},
        ]
        if competitor_id:
            clauses.append({"competitor_id": {"$eq": competitor_id}})

        try:
            hits = chroma.query(
                project_id, query, n_results=SNIPPETS_PER_FIELD, where={"$and": clauses}
            )
        except Exception as exc:  # noqa: BLE001 - metrics still render without passages
            logger.warning("Passage retrieval failed for %s/%s: %s", project_id, field_type, exc)
            continue

        for hit in hits:
            metadata = hit.get("metadata") or {}
            snippets.append({
                "field_type": metadata.get("field_type", field_type),
                "text": hit.get("document") or "",
                "score": round(float(hit.get("relevance") or 0.0), 4),
                "chunk_index": int(metadata.get("chunk_index") or 0),
            })

    snippets.sort(key=lambda snippet: snippet["score"] or 0.0, reverse=True)
    return snippets
