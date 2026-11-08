"""Reading back an e-commerce comparison for display.

This is the standalone scraper's comparison view, rebuilt on this project's
storage: listings come from ``ecommerce_products`` (Supabase) and passages from
the project's Chroma collection. Nothing here writes, and nothing here calls a
model -- every figure is arithmetic over the two scraped rows, and every
passage is a stored chunk.

It is platform-neutral. The parameter list and the metric rules come from the
platform's scraper (``app/scrapers/<platform>/``), so a second marketplace
needs no change here.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.errors import NotFoundError
from app.scrapers import COMPETITOR, OWN, get_scraper
from app.services.repository import Repository
from app.vectorstore import chroma

logger = logging.getLogger("optistratix.comparison")

#: Passages retrieved per text field, per listing. Matches the standalone tool.
SNIPPETS_PER_FIELD = 3


def load_pair(
    repo: Repository, project_id: str, competitor_product_id: str | None = None
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Returns (project, own listing, competitor listing).

    A project can compare against several competitors; the page shows one at a
    time. With no competitor named, the first one is used.
    """
    project = repo.get_project(project_id)  # 404s unless the caller owns it
    products = repo.list_ecommerce_products(project_id)

    own = next((p for p in products if p.get("role") == OWN), None)
    competitors = [p for p in products if p.get("role") == COMPETITOR]
    if own is None or not competitors:
        raise NotFoundError(
            "These listings have not been scraped yet. Start the scrape and try again."
        )

    if competitor_product_id is None:
        return project, own, competitors[0]

    competitor = next((p for p in competitors if p["id"] == competitor_product_id), None)
    if competitor is None:
        raise NotFoundError("That competitor listing is not part of this comparison.")
    return project, own, competitor


def _scraper_for(project: dict[str, Any], own: dict[str, Any]) -> Any:
    return get_scraper(project.get("ecommerce_platform") or own.get("platform"))


def scoreboard(
    repo: Repository, project_id: str, competitor_product_id: str | None = None
) -> list[dict[str, Any]]:
    """Every parameter group with its metric rows and who leads it."""
    project, own, competitor = load_pair(repo, project_id, competitor_product_id)
    return _scraper_for(project, own).build_metrics(
        own.get("raw_metadata") or {}, competitor.get("raw_metadata") or {}
    )


def parameter_detail(
    repo: Repository,
    project_id: str,
    parameter_key: str,
    competitor_product_id: str | None = None,
) -> dict[str, Any]:
    """One parameter: metric rows, rule-based read-out, and retrieved passages."""
    project, own, competitor = load_pair(repo, project_id, competitor_product_id)
    scraper = _scraper_for(project, own)

    groups = scraper.build_metrics(
        own.get("raw_metadata") or {}, competitor.get("raw_metadata") or {}
    )
    group = next((g for g in groups if g["key"] == parameter_key), None)
    if group is None:
        valid = ", ".join(g["key"] for g in groups)
        raise NotFoundError(f"Unknown comparison parameter '{parameter_key}'. Valid: {valid}.")

    field_types = group.get("semantic_field_types") or []
    query = group.get("query")

    return {
        "parameter": group,
        "metadata_only": not field_types,
        "own": _side(project_id, own, group["own_derived"], field_types, query),
        "competitor": _side(
            project_id, competitor, group["competitor_derived"], field_types, query
        ),
    }


def _side(
    project_id: str,
    product: dict[str, Any],
    derived: dict[str, Any],
    field_types: list[str],
    query: str | None,
) -> dict[str, Any]:
    return {
        "product_id": product["id"],
        "role": product.get("role", ""),
        "product_name": product.get("product_name", ""),
        "url": product.get("url", ""),
        "snippets": _snippets(project_id, product["id"], field_types, query),
        "derived": derived,
    }


def _snippets(
    project_id: str, product_id: str, field_types: list[str], query: str | None
) -> list[dict[str, Any]]:
    """The most relevant stored passages for one listing, best first.

    Each field type is searched on its own, as the standalone tool did: a
    combined search lets one long field (reviews) crowd out a short one (the
    title) that answers the question just as well.
    """
    if not field_types or not query:
        return []

    snippets: list[dict[str, Any]] = []
    for field_type in field_types:
        where = {
            "$and": [
                {"product_id": {"$eq": product_id}},
                {"field_type": {"$eq": field_type}},
            ]
        }
        try:
            hits = chroma.query(project_id, query, n_results=SNIPPETS_PER_FIELD, where=where)
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
