"""Scraping and the product comparison view.

    GET  /scrapers/platforms                                      platforms the form offers
    POST /scrapers/projects/{id}/scrape                           scrape + embed, in the background
    GET  /scrapers/projects/{id}/products                         the scraped listings
    GET  /scrapers/projects/{id}/comparison                       every parameter, with who leads
    GET  /scrapers/projects/{id}/comparison/{parameter}           one parameter, with passages

An e-commerce comparison scrapes and displays; it does not run the agent
pipeline. The scrape still records its progress as pipeline stages 2 and 3, so
status polling, errors and retries work the same way they do everywhere else.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.core.security import CurrentUser, get_current_user
from app.models.ecommerce import (
    ComparisonGroup,
    EcommerceProduct,
    ParameterComparison,
    PlatformOption,
)
from app.models.pipeline import PipelineState
from app.scrapers import available_platforms
from app.services import ecommerce_comparison_service as comparison_service
from app.services import pipeline_service
from app.services.repository import get_repository

logger = logging.getLogger("optistratix.scrapers.routes")

router = APIRouter(prefix="/scrapers", tags=["scrapers"])

COMPETITOR_QUERY = Query(
    default=None,
    description="Product id of the competitor listing to compare against. Defaults to the first.",
)


@router.get("/platforms", response_model=list[PlatformOption])
async def list_platforms() -> list[PlatformOption]:
    """Every e-commerce platform a comparison can run against.

    Unauthenticated: it is a static capability list with nothing user-specific
    in it, and the intake form needs it before a project exists.
    """
    return [PlatformOption.model_validate(info.__dict__) for info in available_platforms()]


@router.post("/projects/{project_id}/scrape", response_model=PipelineState)
async def start_scrape(
    project_id: str,
    tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> PipelineState:
    """Scrapes both listings and embeds their text, after the response is sent.

    Scraping takes 30-90 seconds per listing when the Playwright fallback is
    needed, far longer than a request should be held open. Poll
    ``GET /projects/{id}/pipeline`` for progress; stages 2 and 3 are the scrape.
    """
    repo = get_repository(user.id, user.token)
    state = pipeline_service.start_scrape(repo, project_id)

    def runner() -> None:
        # BackgroundTasks runs sync callables in a worker thread with no event
        # loop of its own, hence asyncio.run.
        try:
            asyncio.run(pipeline_service.run_scrape(project_id, user.id))
        except Exception:  # noqa: BLE001 - a crashed task must not be silent
            logger.exception("Background scrape failed for %s", project_id)

    tasks.add_task(runner)
    return PipelineState.model_validate(state)


@router.get("/projects/{project_id}/products", response_model=list[EcommerceProduct])
async def list_products(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> list[EcommerceProduct]:
    """The scraped listings behind an e-commerce project."""
    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)  # 404s unless the caller owns it

    # Photos, price tiers and supplier profiles are extras: if a table cannot be
    # read (for instance before its migration has been applied), the listings
    # still load without that part.
    def grouped(reader: Callable[[str], list[dict]], label: str) -> dict[str, list[dict]]:
        try:
            rows = reader(project_id)
        except Exception as exc:  # noqa: BLE001 - never fail the comparison over extras
            logger.warning("Could not read %s for %s: %s", label, project_id, exc)
            rows = []
        by_product: dict[str, list[dict]] = {}
        for row in rows:
            by_product.setdefault(row["product_id"], []).append(row)
        return by_product

    images_by_product = grouped(repo.list_ecommerce_product_images, "product images")
    tiers_by_product = grouped(repo.list_ecommerce_product_price_tiers, "price tiers")
    suppliers_by_product = grouped(repo.list_ecommerce_product_suppliers, "supplier profiles")

    return [
        EcommerceProduct.model_validate({
            **row,
            "images": sorted(images_by_product.get(row["id"], []), key=lambda i: i["position"]),
            "price_tiers": sorted(tiers_by_product.get(row["id"], []), key=lambda t: t["position"]),
            "supplier": (suppliers_by_product.get(row["id"]) or [None])[0],
        })
        for row in repo.list_ecommerce_products(project_id)
    ]


@router.get("/projects/{project_id}/comparison", response_model=list[ComparisonGroup])
async def comparison(
    project_id: str,
    competitor: str | None = COMPETITOR_QUERY,
    user: CurrentUser = Depends(get_current_user),
) -> list[ComparisonGroup]:
    """Every parameter group side by side, with a winner per metric.

    Computed on read rather than stored: it is a pure function of two rows that
    are already persisted, so caching it would only create a second thing that
    can go stale.
    """
    repo = get_repository(user.id, user.token)
    groups = comparison_service.scoreboard(repo, project_id, competitor)
    return [ComparisonGroup.model_validate(group) for group in groups]


@router.get(
    "/projects/{project_id}/comparison/{parameter}", response_model=ParameterComparison
)
async def parameter_comparison(
    project_id: str,
    parameter: str,
    competitor: str | None = COMPETITOR_QUERY,
    user: CurrentUser = Depends(get_current_user),
) -> ParameterComparison:
    """One parameter in full: metric rows, the read-out, and retrieved passages."""
    repo = get_repository(user.id, user.token)
    detail = comparison_service.parameter_detail(repo, project_id, parameter, competitor)
    return ParameterComparison.model_validate(detail)
