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
from app.services import demo_data
from app.services.repository import Repository, get_worker_repository, new_id
from app.vectorstore import chroma

logger = logging.getLogger("optistratix.pipeline")

#: Stages the runner drives on its own. 1 is the intake form, 5 and 7 are human.
AUTOMATED_STAGES = (2, 3, 4, 6, 8, 9)

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
        result = await get_agent(2).run(context)
        repo.replace_sources(project_id, result.payload)
        message = f"{result.items_processed} sources collected"

    elif stage_id == 3:
        context["sources"] = repo.list_sources(project_id)
        result = await get_agent(3).run(context)
        message = f"{result.items_processed} chunks embedded into the project collection"

    elif stage_id == 4:
        context["sources"] = repo.list_sources(project_id)
        result = await get_agent(4).run(context)
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


# ------------------------------------------------------------- transitions ---


def start(repo: Repository, project_id: str) -> dict[str, Any]:
    """Opens a run. The caller schedules ``run_from`` as a background task."""
    state = load_state(repo, project_id)
    if state["stages"]["2"]["status"] == StageStatus.RUNNING.value:
        raise ConflictError("This pipeline is already running.")

    repo.update_project(project_id, {"status": "running", "current_stage": 2})
    return state


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
