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

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.core.errors import AppError
from app.core.security import CurrentUser, get_current_user
from app.scrapers.base import ScraperError
from app.scrapers.instagram import media as instagram_media
from app.scrapers.instagram import selectors as instagram_selectors
from app.models.ecommerce import (
    ComparisonGroup,
    EcommerceProduct,
    ParameterComparison,
    PlatformOption,
)
from app.models.pipeline import PipelineState
from app.models.sources import ScrapedDocuments, ScrapedPage, ScrapedPost
from app.scrapers import available_platforms, source_kind_for
from app.services import ecommerce_comparison_service as comparison_service
from app.services import pipeline_service
from app.services import token_service
from app.services import site_comparison_service
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


MEDIA_URL_QUERY = Query(
    ..., description="The Instagram CDN URL to relay.", max_length=2000
)


@router.get("/media")
def media(request: Request, url: str = MEDIA_URL_QUERY) -> StreamingResponse:
    """Relays one Instagram image or video.

    Instagram's CDN sends ``Cross-Origin-Resource-Policy: same-origin``, so a
    browser refuses to render its media on this app's origin however it is
    linked. Fetching it here and handing on the bytes is the only way to show a
    post's picture; the rules that keep it from being an open proxy live in
    ``scrapers/instagram/media.py``.

    **Unauthenticated on purpose.** An ``<img>`` tag cannot carry a bearer
    token, and there is nothing here to protect: the bytes are public, and the
    URL came from the page that is asking for them. What bounds this endpoint
    is the host allowlist, not the caller's identity.

    Defined sync, so FastAPI runs it in a worker thread: the fetch underneath
    blocks, and would otherwise hold the event loop for the whole download.
    """
    try:
        status_code, content_type, passthrough, chunks = instagram_media.open_stream(
            url, range_header=request.headers.get("range")
        )
    except ScraperError as exc:
        raise AppError(str(exc), code="media_not_relayed") from exc

    return StreamingResponse(
        chunks,
        status_code=status_code,
        media_type=content_type,
        headers={
            **passthrough,
            "Cache-Control": f"private, max-age={instagram_selectors.MEDIA_CACHE_SECONDS}",
            "X-Content-Type-Options": "nosniff",
        },
    )


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
    project = repo.get_project(project_id)
    pipeline_service._require_scrapable(project)
    run_id = None if user.is_demo else token_service.reserve(user, project_id)
    try:
        state = pipeline_service.start_scrape(repo, project_id, run_id)
    except Exception:
        if run_id:
            token_service.finish(run_id, False, "Scrape did not start")
        raise

    def runner() -> None:
        # BackgroundTasks runs sync callables in a worker thread with no event
        # loop of its own, hence asyncio.run.
        try:
            asyncio.run(pipeline_service.run_scrape(project_id, user.id, run_id))
        except Exception as exc:  # noqa: BLE001 - a crashed task must not be silent
            logger.exception("Background scrape failed for %s", project_id)
            if run_id:
                try:
                    token_service.finish(run_id, False, "Background scrape interrupted")
                except Exception:
                    logger.exception("Could not release scrape token for %s", project_id)
            pipeline_service.record_crash(project_id, user.id, [2, 3], exc)

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


#: How much of a page's text the scraped-data screen previews.
TEXT_PREVIEW_LENGTH = 400


@router.get("/projects/{project_id}/documents", response_model=ScrapedDocuments)
async def list_documents(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> ScrapedDocuments:
    """The pages or posts behind a website or social comparison.

    The counterpart of ``/products`` for the two comparison types whose unit is
    a page or a post rather than a listing. Which list comes back is decided by
    the project's comparison type, so the caller makes one request either way.
    """
    repo = get_repository(user.id, user.token)
    project = repo.get_project(project_id)  # 404s unless the caller owns it

    kind = source_kind_for(project.get("comparison_type") or "", project.get("social_platform"))
    if kind not in ("website", "instagram"):
        return ScrapedDocuments()

    reader = repo.list_website_pages if kind == "website" else repo.list_instagram_posts
    try:
        rows = reader(project_id)
    except Exception as exc:  # noqa: BLE001 - an unreadable table is an empty screen, not a 500
        logger.warning("Could not read %s documents for %s: %s", kind, project_id, exc)
        return ScrapedDocuments(kind=kind)

    if kind == "website":
        images = _children(repo.list_website_page_images, "page_id", project_id, "page images")
        return ScrapedDocuments(
            kind=kind,
            pages=[
                ScrapedPage.model_validate({
                    **row,
                    "text_preview": (row.get("cleaned_text") or "")[:TEXT_PREVIEW_LENGTH],
                    "images": images.get(row["id"], []),
                })
                for row in rows
            ],
        )

    media = _children(repo.list_instagram_post_media, "post_id", project_id, "post media")
    comments = _children(repo.list_instagram_post_comments, "post_id", project_id, "post comments")
    return ScrapedDocuments(
        kind=kind,
        posts=[
            ScrapedPost.model_validate({
                **row,
                "media": media.get(row["id"], []),
                "comments": comments.get(row["id"], []),
            })
            for row in rows
        ],
    )


def _children(
    reader: Callable[[str], list[dict]], parent_key: str, project_id: str, label: str
) -> dict[str, list[dict]]:
    """Rows that hang off a page or a post, grouped by the row they belong to.

    Images, media and comments are extras in the same sense a listing's photos
    are: if the table cannot be read -- most likely because its migration has
    not been applied yet -- the pages and posts still load without them.
    """
    try:
        rows = reader(project_id)
    except Exception as exc:  # noqa: BLE001 - never fail the screen over extras
        logger.warning("Could not read %s for %s: %s", label, project_id, exc)
        return {}

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row[parent_key], []).append(row)
    return grouped


def _comparison_service(repo, project_id: str):
    """Which comparison a project gets: listings, or pages and posts.

    Both services expose the same two functions and return the same shapes, so
    the routes below never branch again.
    """
    project = repo.get_project(project_id)
    if site_comparison_service.source_kind_of(project):
        return site_comparison_service
    return comparison_service


@router.get("/projects/{project_id}/comparison", response_model=list[ComparisonGroup])
async def comparison(
    project_id: str,
    competitor: str | None = COMPETITOR_QUERY,
    user: CurrentUser = Depends(get_current_user),
) -> list[ComparisonGroup]:
    """Every parameter group side by side, with a winner per metric.

    Computed on read rather than stored: it is a pure function of rows that are
    already persisted, so caching it would only create a second thing that can
    go stale.
    """
    repo = get_repository(user.id, user.token)
    service = _comparison_service(repo, project_id)
    groups = service.scoreboard(repo, project_id, competitor)
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
    service = _comparison_service(repo, project_id)
    detail = service.parameter_detail(repo, project_id, parameter, competitor)
    return ParameterComparison.model_validate(detail)
