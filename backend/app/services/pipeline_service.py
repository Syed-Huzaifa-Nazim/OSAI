"""Pipeline state and the background runner.

The runner is what makes the nine stages real rather than a diagram: it drives
the automated stages in sequence and *stops* at stages 5 and 7 until a human
submits a decision. Those stops are the product, so they are enforced here in
the runner rather than left to the UI to respect.

FastAPI BackgroundTasks is used to start a run. It is adequate for a single
process; Celery/Redis or Supabase Edge Functions are the upgrade path once runs
outlive a web worker. Noted in docs/architecture.md.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.api.v1.agents.registry import get_agent, get_critic
from app.core.errors import ConflictError
from app.models.pipeline import CHECKPOINT_STAGES, StageStatus
from app.scrapers import is_source_supported, source_kind_for, source_kinds
from app.services import demo_data
from app.services.repository import Repository, get_worker_repository, new_id
from app.vectorstore import chroma

logger = logging.getLogger("optistratix.pipeline")

#: Stages the runner drives on its own. 1 is the intake form, 5 and 7 are human.
AUTOMATED_STAGES = (2, 3, 4, 6, 8, 9)

#: What an e-commerce comparison runs today: scrape both listings (stage 2),
#: then chunk and embed their text (stage 3) so the comparison page can show
#: retrieved passages. Nothing after that runs -- no gap analysis, strategy or
#: human checkpoints. The comparison is displayed straight from the scraped
#: data, the way the standalone scraper did.
SCRAPE_STAGES = (2, 3)

CHECKPOINT_MESSAGES = {
    5: "Waiting for you to prioritise the identified gaps",
    7: "Waiting for your final approval of the strategy",
}


# ------------------------------------------------------------------ state ---


def empty_state(project_id: str) -> dict[str, Any]:
    """A fresh pipeline. Stage 1 is already complete. The intake form is what
    created the project."""
    now = demo_data.iso()
    stages: dict[str, Any] = {}
    for stage_id in range(1, 10):
        done = stage_id == 1
        stages[str(stage_id)] = {
            "id": stage_id,
            "status": StageStatus.COMPLETE.value if done else StageStatus.IDLE.value,
            "progress": 100 if done else 0,
            "started_at": now if done else None,
            "completed_at": now if done else None,
            "message": None,
            "error": None,
            "metrics": None,
        }
    return {
        "project_id": project_id,
        "current_stage": 1,
        "stages": stages,
        "blocked_on": None,
        "updated_at": now,
    }


def load_state(repo: Repository, project_id: str) -> dict[str, Any]:
    state = repo.get_pipeline(project_id)
    if state is None:
        state = empty_state(project_id)
        repo.save_pipeline(project_id, state)
    return state


def _set_stage(
    state: dict[str, Any],
    stage_id: int,
    **patch: Any,
) -> None:
    stage = state["stages"][str(stage_id)]
    stage.update(patch)
    state["updated_at"] = demo_data.iso()


def _park_at_checkpoint(state: dict[str, Any], stage_id: int) -> None:
    _set_stage(
        state,
        stage_id,
        status=StageStatus.AWAITING_HUMAN.value,
        started_at=demo_data.iso(),
        message=CHECKPOINT_MESSAGES[stage_id],
    )
    state["current_stage"] = stage_id
    state["blocked_on"] = stage_id


# ----------------------------------------------------------------- runner ---


async def run_from(project_id: str, user_id: str, start_stage: int) -> None:
    """Runs automated stages from ``start_stage`` until a checkpoint or the end.

    Any failure marks the stage errored and stops the run; it never leaves the
    pipeline claiming to be running.
    """
    repo = get_worker_repository(user_id)
    state = load_state(repo, project_id)
    stage_id = start_stage

    while stage_id <= 9:
        if stage_id in CHECKPOINT_STAGES:
            _park_at_checkpoint(state, stage_id)
            repo.save_pipeline(project_id, state)
            repo.update_project(
                project_id, {"status": "awaiting_review", "current_stage": stage_id}
            )
            logger.info("Project %s parked at checkpoint stage %d", project_id, stage_id)
            return

        try:
            await _run_stage(repo, project_id, state, stage_id)
        except Exception as exc:  # noqa: BLE001 - surface it on the stage, then stop
            logger.exception("Stage %d failed for project %s", stage_id, project_id)
            _set_stage(
                state,
                stage_id,
                status=StageStatus.ERROR.value,
                error=f"{type(exc).__name__}: {exc}",
            )
            state["blocked_on"] = None
            repo.save_pipeline(project_id, state)
            repo.update_project(project_id, {"status": "failed"})
            return

        stage_id += 1

    state["current_stage"] = 9
    state["blocked_on"] = None
    repo.save_pipeline(project_id, state)
    repo.update_project(project_id, {"status": "complete", "current_stage": 9})
    logger.info("Project %s completed the pipeline", project_id)


async def _run_stage(
    repo: Repository, project_id: str, state: dict[str, Any], stage_id: int
) -> None:
    """Executes one automated stage and persists whatever it produced."""
    _set_stage(
        state,
        stage_id,
        status=StageStatus.RUNNING.value,
        progress=0,
        started_at=demo_data.iso(),
        error=None,
        message="Working...",
    )
    state["current_stage"] = stage_id
    state["blocked_on"] = None
    repo.save_pipeline(project_id, state)
    repo.update_project(project_id, {"status": "running", "current_stage": stage_id})

    project = repo.get_project(project_id)
    context: dict[str, Any] = {"project_id": project_id, "project": project}

    if stage_id == 2:
        context["competitors"] = repo.list_competitors(project_id)
        result = await get_agent(2, project).run(context)
        repo.replace_sources(project_id, result.payload)
        # An e-commerce Scout also returns the structured listings behind those
        # sources. Persisting them here keeps the agent free of storage concerns,
        # exactly as the sources themselves are handled.
        products = result.artifacts.get("ecommerce_products")
        if products is not None:
            repo.replace_ecommerce_products(project_id, products)
            # After the products: each image row references its product.
            # Photos are an extra, not the comparison, so failing to store them
            # (say, before the images migration has been applied) is recorded
            # as a warning and the scrape carries on.
            try:
                repo.replace_ecommerce_product_images(
                    project_id, result.artifacts.get("ecommerce_product_images") or []
                )
            except Exception as exc:  # noqa: BLE001 - never fail a scrape over photos
                logger.warning("Could not store product images for %s: %s", project_id, exc)
                result.warnings.append(
                    f"Product images were scraped but could not be saved ({type(exc).__name__})."
                )
            # Price tiers and supplier profiles (Alibaba) are extras in the same
            # sense: the comparison reads raw_metadata, so failing to store the
            # structured copies is a warning, not a failed scrape.
            for artifact, store, label in (
                ("ecommerce_product_price_tiers", repo.replace_ecommerce_product_price_tiers, "price tiers"),
                ("ecommerce_product_suppliers", repo.replace_ecommerce_product_suppliers, "supplier profiles"),
            ):
                try:
                    store(project_id, result.artifacts.get(artifact) or [])
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not store %s for %s: %s", label, project_id, exc)
                    result.warnings.append(
                        f"Product {label} were scraped but could not be saved ({type(exc).__name__})."
                    )

        # The website and social Scouts return the structured copy of what they
        # read. Parents before children, so a foreign key always has something
        # to point at.
        #
        # Unlike the product extras, the pages and posts ARE the result here:
        # stage 3 embeds them and the screen renders them, so failing to store
        # one fails the stage. Reporting success with nothing stored is exactly
        # what hid the duplicate-post bug behind "Nothing was collected".
        for artifact, store, label in (
            ("website_pages", repo.replace_website_pages, "website pages"),
            ("instagram_posts", repo.replace_instagram_posts, "Instagram posts"),
        ):
            if artifact in result.artifacts:
                try:
                    store(project_id, result.artifacts[artifact] or [])
                except Exception as exc:  # noqa: BLE001 - re-raised with context
                    raise RuntimeError(f"The scraped {label} could not be saved: {exc}") from exc

        # Media and comments hang off a post that is already stored. Losing
        # them thins the result rather than emptying it.
        for artifact, store, label in (
            ("website_page_images", repo.replace_website_page_images, "website images"),
            ("instagram_post_media", repo.replace_instagram_post_media, "Instagram media"),
            ("instagram_post_comments", repo.replace_instagram_post_comments, "Instagram comments"),
        ):
            if artifact not in result.artifacts:
                continue
            try:
                store(project_id, result.artifacts[artifact] or [])
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not store %s for %s: %s", label, project_id, exc)
                result.warnings.append(
                    f"{label.capitalize()} were scraped but could not be saved "
                    f"({type(exc).__name__})."
                )
        message = f"{result.items_processed} sources collected"

    elif stage_id == 3:
        context["sources"] = repo.list_sources(project_id)
        context["ecommerce_products"] = repo.list_ecommerce_products(project_id)
        context["source_documents"] = _source_documents(repo, project)
        result = await get_agent(3, project).run(context)
        counts = result.artifacts.get("product_chunk_counts") or {}
        for product_id, chunk_count in counts.items():
            repo.update_ecommerce_product(project_id, product_id, {"chunk_count": chunk_count})
        # A page or post is embedded against its source row, so the sources
        # screen shows what is actually retrievable.
        for source_id, chunk_count in (result.artifacts.get("source_chunk_counts") or {}).items():
            try:
                repo.update_source(
                    project_id, source_id, {"chunk_count": chunk_count, "status": "embedded"}
                )
            except Exception as exc:  # noqa: BLE001 - a count is not worth failing a run
                logger.warning("Could not update source %s: %s", source_id, exc)
        message = f"{result.items_processed} chunks embedded into the project collection"

    elif stage_id == 4:
        context["sources"] = repo.list_sources(project_id)
        context["ecommerce_products"] = repo.list_ecommerce_products(project_id)
        result = await get_agent(4, project).run(context)
        repo.replace_gaps(project_id, result.payload)
        repo.update_project(project_id, {"gap_count": len(result.payload)})
        message = f"{result.items_processed} gaps identified"

    elif stage_id == 6:
        result = await _run_strategy_stage(repo, project_id, project, context)
        message = result.payload["message"]

    elif stage_id == 8:
        result = await _run_document_stage(repo, project_id, project)
        message = "Strategy document ready to export"

    elif stage_id == 9:
        result = await _run_automation_stage(repo, project_id)
        message = f"{result.items_processed} content assets suggested"

    else:  # pragma: no cover - AUTOMATED_STAGES is exhaustive
        raise ValueError(f"Stage {stage_id} is not an automated stage")

    _set_stage(
        state,
        stage_id,
        status=StageStatus.COMPLETE.value,
        progress=100,
        completed_at=demo_data.iso(),
        message=message,
        metrics={
            "items_processed": result.items_processed,
            "duration_ms": result.duration_ms,
            "tokens_used": result.tokens_used,
            "cost_usd": result.cost_usd,
        },
    )
    repo.save_pipeline(project_id, state)

    for warning in result.warnings:
        logger.info("Stage %d (%s): %s", stage_id, project_id, warning)


async def _run_strategy_stage(
    repo: Repository, project_id: str, project: dict[str, Any], context: dict[str, Any]
) -> Any:
    """Stage 6: Strategist drafts, Critic reviews, both records are kept."""
    from app.api.v1.agents.base import AgentResult

    gaps = repo.list_gaps(project_id)
    accepted = [gap for gap in gaps if gap.get("decision") == "accepted"]
    if not accepted:
        raise ConflictError(
            "No gaps were accepted at the first checkpoint, so there is nothing to build a "
            "strategy from."
        )

    context["accepted_gaps"] = accepted
    draft_result = await get_agent(6).run(context)
    draft = draft_result.payload

    # Whether a paid budget exists is not captured at intake yet, so the Critic
    # is told there is none. That is the honest default for an SME pilot, and it
    # is why the paid initiative gets rejected in a demo run.
    critic_result = await get_critic().run({"draft": draft, "has_budget": False})
    critiqued = critic_result.payload

    previous = repo.get_strategy(project_id)
    version = (previous["version"] + 1) if previous else 1
    repo.clear_strategies(project_id)

    strategy = {
        "id": new_id("strategy"),
        "project_id": project_id,
        "version": version,
        "title": draft["title"],
        "executive_summary": draft["executive_summary"],
        "status": "awaiting_approval",
        "initiatives": critiqued["initiatives"],
        "critic_feedback": critiqued["critic_feedback"],
        "addressed_gap_ids": draft["addressed_gap_ids"],
        "generated_at": demo_data.iso(),
        "approved_at": None,
    }
    repo.insert_strategy(strategy)

    return AgentResult(
        payload={
            "message": (
                f"{len(critiqued['initiatives'])} initiatives generated, "
                f"{len(critiqued['critic_feedback'])} critic interventions"
            )
        },
        items_processed=len(critiqued["initiatives"]),
        duration_ms=draft_result.duration_ms + critic_result.duration_ms,
        tokens_used=(draft_result.tokens_used or 0) + (critic_result.tokens_used or 0),
        cost_usd=round((draft_result.cost_usd or 0) + (critic_result.cost_usd or 0), 3),
        warnings=[*draft_result.warnings, *critic_result.warnings],
    )


async def _run_document_stage(repo: Repository, project_id: str, project: dict[str, Any]) -> Any:
    """Stage 8: assemble the document from what the run actually produced."""
    from app.api.v1.agents.base import AgentResult

    strategy = repo.get_strategy(project_id)
    if strategy is None:
        raise ConflictError("There is no approved strategy to build a document from.")

    await asyncio.sleep(0.6)

    gaps = repo.list_gaps(project_id)
    reviews = repo.list_reviews(project_id)
    sources = repo.list_sources(project_id)

    sections = demo_data.build_document_sections(
        project, gaps, strategy, reviews, len(sources)
    )
    content = "\n\n".join(f"## {section['heading']}\n\n{section['body']}" for section in sections)

    document = {
        "id": new_id("doc"),
        "project_id": project_id,
        "strategy_id": strategy["id"],
        "title": strategy["title"],
        "content": content,
        "sections": sections,
        "available_formats": ["pdf", "docx", "markdown"],
        "word_count": len(content.split()),
        "generated_at": demo_data.iso(),
    }
    repo.insert_document(document)

    return AgentResult(payload=document, items_processed=len(sections), duration_ms=600,
                       tokens_used=7_260, cost_usd=0.135)


async def _run_automation_stage(repo: Repository, project_id: str) -> Any:
    """Stage 9: map content assets onto the approved initiatives."""
    from app.api.v1.agents.base import AgentResult

    strategy = repo.get_strategy(project_id)
    if strategy is None:
        raise ConflictError("There is no strategy to generate content against.")

    await asyncio.sleep(0.5)
    suggestions = demo_data.build_suggestions(project_id, strategy)
    repo.replace_suggestions(project_id, suggestions)

    return AgentResult(
        payload=suggestions,
        items_processed=len(suggestions),
        duration_ms=500,
        tokens_used=5_400,
        cost_usd=0.081,
    )


def _source_documents(repo: Repository, project: dict[str, Any]) -> list[dict[str, Any]]:
    """The pages or posts stage 3 embeds, for a website or social comparison.

    Read back from storage rather than passed along from stage 2, so a re-embed
    never needs a re-scrape. An unreadable table (its migration not applied yet)
    yields nothing rather than failing the stage.
    """
    kind = source_kind_for(project.get("comparison_type") or "", project.get("social_platform"))
    readers = {
        "website": (repo.list_website_pages, "page_url"),
        "instagram": (repo.list_instagram_posts, "post_url"),
    }
    if kind not in readers:
        return []

    reader, url_key = readers[kind]
    try:
        rows = reader(project["id"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read %s documents for %s: %s", kind, project["id"], exc)
        return []

    return [{**row, "kind": kind, "url": row.get(url_key) or ""} for row in rows]


def _require_scrapable(project: dict[str, Any]) -> None:
    """Refuses a project nothing can scrape, before any stage is marked running."""
    comparison_type = project.get("comparison_type") or ""
    if comparison_type == "ecommerce_product":
        return

    kind = source_kind_for(comparison_type, project.get("social_platform"))
    if kind is None:
        raise ConflictError("This project has nothing that can be scraped.")
    if not is_source_supported(kind):
        # Either no scraper exists for it, or the one that does cannot run --
        # Instagram without an Apify token, say. Both are told plainly rather
        # than failing halfway through a run.
        raise ConflictError(
            get_source_scraper_reason(kind)
            if kind in source_kinds()
            else f"{kind.title()} comparisons are not available yet."
        )


def get_source_scraper_reason(kind: str) -> str:
    from app.scrapers import get_source_scraper

    return get_source_scraper(kind).unavailable_reason()


# ------------------------------------------------------------- transitions ---


def start(repo: Repository, project_id: str) -> dict[str, Any]:
    """Opens a run. The caller schedules ``run_from`` as a background task."""
    project = repo.get_project(project_id)
    if not project.get("is_demo"):
        # Every comparison type now has a real scraper behind it, and all three
        # scrape and display rather than running the agent pipeline. Refused
        # here, not just hidden in the UI, so no route can start agents by
        # accident. The seeded demo project is exempt: walking the nine stages
        # with no network is the whole reason it exists.
        raise ConflictError(
            "Comparisons scrape and display; the agent pipeline is switched off for them. "
            "Start a scrape instead."
        )
    state = load_state(repo, project_id)
    if state["stages"]["2"]["status"] == StageStatus.RUNNING.value:
        raise ConflictError("This pipeline is already running.")

    repo.update_project(project_id, {"status": "running", "current_stage": 2})
    return state


def start_scrape(repo: Repository, project_id: str) -> dict[str, Any]:
    """Opens a scrape-only run. The caller schedules ``run_scrape`` in the background.

    Stage 2 is marked running *before* returning, so a client that starts
    polling immediately sees progress rather than an idle pipeline for the
    moment before the background task picks the job up.
    """
    project = repo.get_project(project_id)
    if project.get("is_demo"):
        # The seeded project's links do not resolve; it exists to walk the nine
        # stages with no network, and scraping it would only fail.
        raise ConflictError(
            "The demo project is seeded data, not a real comparison, so there is nothing "
            "to scrape. Create an analysis of your own."
        )
    _require_scrapable(project)

    current = load_state(repo, project_id)
    if any(
        current["stages"][str(stage_id)]["status"] == StageStatus.RUNNING.value
        for stage_id in SCRAPE_STAGES
    ):
        raise ConflictError("These listings are already being scraped.")

    # Every scrape starts clean, so a re-run never mixes old vectors or an old
    # stage error into the new result.
    state = empty_state(project_id)
    _set_stage(
        state,
        2,
        status=StageStatus.RUNNING.value,
        progress=0,
        started_at=demo_data.iso(),
        message="Queued",
    )
    state["current_stage"] = 2
    repo.save_pipeline(project_id, state)
    chroma.delete_collection(project_id)
    repo.update_project(project_id, {"status": "running", "current_stage": 2})
    return state


async def run_scrape(project_id: str, user_id: str) -> None:
    """Runs the scrape stages and stops. Never starts an agent.

    A failure is recorded on the stage that failed, in the scraper's own
    words -- those messages are written for the user ("not a Daraz domain",
    "HTTP 404") -- and the project is marked failed so the page can offer a
    retry.
    """
    repo = get_worker_repository(user_id)
    state = load_state(repo, project_id)

    for stage_id in SCRAPE_STAGES:
        try:
            await _run_stage(repo, project_id, state, stage_id)
        except Exception as exc:  # noqa: BLE001 - surface it on the stage, then stop
            logger.exception("Scrape stage %d failed for project %s", stage_id, project_id)
            _set_stage(
                state,
                stage_id,
                status=StageStatus.ERROR.value,
                error=str(exc) or type(exc).__name__,
                message=None,
            )
            state["blocked_on"] = None
            repo.save_pipeline(project_id, state)
            repo.update_project(project_id, {"status": "failed"})
            return

    state["blocked_on"] = None
    repo.save_pipeline(project_id, state)
    repo.update_project(project_id, {"status": "complete", "current_stage": SCRAPE_STAGES[-1]})
    logger.info("Project %s scraped and embedded", project_id)


def reset(repo: Repository, project_id: str) -> dict[str, Any]:
    """Clears everything the run produced. Keeps the project and competitors."""
    state = empty_state(project_id)
    repo.save_pipeline(project_id, state)
    repo.replace_sources(project_id, [])
    repo.replace_gaps(project_id, [])
    repo.clear_strategies(project_id)
    repo.replace_suggestions(project_id, [])
    repo.update_project(project_id, {"status": "draft", "current_stage": 1, "gap_count": 0})
    chroma.delete_collection(project_id)
    return state


def close_checkpoint(
    repo: Repository, project_id: str, stage_id: int, message: str
) -> dict[str, Any]:
    """Marks a human checkpoint complete so the runner may proceed past it."""
    state = load_state(repo, project_id)
    stage = state["stages"][str(stage_id)]
    if stage["status"] != StageStatus.AWAITING_HUMAN.value:
        raise ConflictError(
            f"Stage {stage_id} is not waiting for a decision right now."
        )

    _set_stage(
        state,
        stage_id,
        status=StageStatus.COMPLETE.value,
        progress=100,
        completed_at=demo_data.iso(),
        message=message,
    )
    state["blocked_on"] = None
    repo.save_pipeline(project_id, state)
    return state


def reopen_stage(repo: Repository, project_id: str, stage_id: int) -> dict[str, Any]:
    """Sends a stage back to idle, used when stage 7 requests a revision and
    stage 6 has to run again."""
    state = load_state(repo, project_id)
    _set_stage(
        state,
        stage_id,
        status=StageStatus.IDLE.value,
        progress=0,
        started_at=None,
        completed_at=None,
        message=None,
        error=None,
    )
    state["blocked_on"] = None
    repo.save_pipeline(project_id, state)
    return state


def run_cost(repo: Repository, project_id: str) -> dict[str, Any]:
    """Totals token spend across the stages that have run."""
    state = load_state(repo, project_id)
    by_stage = []
    for stage in state["stages"].values():
        metrics = stage.get("metrics")
        if not metrics or not metrics.get("tokens_used"):
            continue
        by_stage.append(
            {
                "stage": stage["id"],
                "tokens": metrics["tokens_used"],
                "cost_usd": metrics.get("cost_usd") or 0.0,
            }
        )

    return {
        "project_id": project_id,
        "total_tokens": sum(row["tokens"] for row in by_stage),
        "total_cost_usd": round(sum(row["cost_usd"] for row in by_stage), 3),
        "by_stage": by_stage,
    }
