"""The pipeline: stages 2 through 7.

Routes map 1:1 onto the stages so the API stays legible against the deck:

    POST /projects/{id}/scout/run           stage 2 (chains 3 and 4)
    GET  /projects/{id}/scout/status        stage 2 status
    GET  /projects/{id}/pipeline            all nine stages
    POST /projects/{id}/pipeline/reset      clear the run
    GET  /projects/{id}/sources             stage 2/3 output
    GET  /projects/{id}/gaps                stage 4 output
    PATCH /projects/{id}/gaps/{gap_id}      stage 5 triage
    POST /projects/{id}/gaps/review         stage 5: HITL #1 close
    GET  /projects/{id}/strategy            stage 6 output
    POST /projects/{id}/strategy/generate   stage 6 re-run
    POST /projects/{id}/strategy/approve    stage 7, HITL #2 approve
    POST /projects/{id}/strategy/revise     stage 7, HITL #2 send back
"""

from __future__ import annotations

import asyncio
import logging

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.errors import ConflictError, NotFoundError
from app.core.security import CurrentUser, get_current_user
from app.models.gap import Gap, GapPatch, GapReviewSubmit, HitlReview, ReviewDecision
from app.models.misc import RunCost
from app.models.pipeline import PipelineState, StageState
from app.models.project import ScrapedSource
from app.models.strategy import Strategy, StrategyReviewSubmit
from app.services import gap_service, pipeline_service, strategy_service
from app.services.repository import get_repository

logger = logging.getLogger("optistratix.pipeline.routes")

router = APIRouter(prefix="/projects/{project_id}", tags=["pipeline"])


def _schedule(tasks: BackgroundTasks, project_id: str, user_id: str, stage: int) -> None:
    """Runs the pipeline after the response has been sent.

    ``asyncio.run`` is used because BackgroundTasks executes sync callables in a
    worker thread, which has no running loop of its own.
    """

    def runner() -> None:
        try:
            asyncio.run(pipeline_service.run_from(project_id, user_id, stage))
        except Exception:  # noqa: BLE001 - a crashed task must not be silent
            logger.exception("Background pipeline run failed for %s", project_id)

    tasks.add_task(runner)


# ------------------------------------------------------------ stages 2-4 ----


@router.post("/scout/run", response_model=PipelineState)
async def run_scout(
    project_id: str,
    tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> PipelineState:
    """Starts the run at stage 2. Stages 3 and 4 chain automatically, and the
    runner parks at stage 5 for the first human checkpoint."""
    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)
    state = pipeline_service.start(repo, project_id)
    _schedule(tasks, project_id, user.id, 2)
    return PipelineState.model_validate(state)


@router.post("/analysis/run", response_model=PipelineState)
async def run_instagram_analysis(
    project_id: str,
    tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> PipelineState:
    """Analyses a scraped Instagram comparison (stage 4) and parks at the first
    checkpoint, so the gaps can be reviewed. Real projects only."""
    repo = get_repository(user.id, user.token)
    state = pipeline_service.start_analysis(repo, project_id)

    def runner() -> None:
        try:
            asyncio.run(pipeline_service.run_analysis(project_id, user.id))
        except Exception:  # noqa: BLE001 - a crashed task must not be silent
            logger.exception("Background analysis failed for %s", project_id)

    tasks.add_task(runner)
    return PipelineState.model_validate(state)


@router.get("/scout/status", response_model=StageState)
async def scout_status(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> StageState:
    repo = get_repository(user.id, user.token)
    state = pipeline_service.load_state(repo, project_id)
    return StageState.model_validate(state["stages"]["2"])


@router.get("/pipeline", response_model=PipelineState)
async def get_pipeline(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> PipelineState:
    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)
    return PipelineState.model_validate(pipeline_service.load_state(repo, project_id))


@router.post("/pipeline/reset", response_model=PipelineState)
async def reset_pipeline(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> PipelineState:
    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)
    return PipelineState.model_validate(pipeline_service.reset(repo, project_id))


@router.get("/sources", response_model=list[ScrapedSource])
async def list_sources(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> list[ScrapedSource]:
    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)
    return [ScrapedSource.model_validate(row) for row in repo.list_sources(project_id)]


@router.get("/cost", response_model=RunCost)
async def get_run_cost(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> RunCost:
    """Token and dollar spend for this run, by stage."""
    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)
    return RunCost.model_validate(pipeline_service.run_cost(repo, project_id))


# ------------------------------------------------- stage 5: HITL #1 ---------


@router.get("/gaps", response_model=list[Gap])
async def list_gaps(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> list[Gap]:
    repo = get_repository(user.id, user.token)
    return [Gap.model_validate(row) for row in gap_service.list_gaps(repo, project_id)]


@router.patch("/gaps/{gap_id}", response_model=Gap)
async def update_gap(
    project_id: str,
    gap_id: str,
    payload: GapPatch,
    user: CurrentUser = Depends(get_current_user),
) -> Gap:
    """Triage one gap at the first checkpoint: keep, drop, reprioritise, annotate."""
    repo = get_repository(user.id, user.token)
    return Gap.model_validate(gap_service.update_gap(repo, project_id, gap_id, payload))


@router.post("/gaps/review", response_model=HitlReview)
async def submit_gap_review(
    project_id: str,
    payload: GapReviewSubmit,
    tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> HitlReview:
    """Closes HITL #1 and releases stage 6.

    Rejected if any gap is still untriaged. See gap_service.submit_review.
    """
    repo = get_repository(user.id, user.token)
    project = repo.get_project(project_id)
    review = gap_service.submit_review(
        repo, project_id, user.id, user.email or "Reviewer", payload
    )
    if project.get("is_demo"):
        # The seeded sample walks the whole pipeline with sample content.
        _schedule(tasks, project_id, user.id, 6)
    else:
        # Real projects stop here. Stages 6-9 (Strategist, Critic, document,
        # automation) are not built yet, and nothing placeholder is run on
        # real data.
        repo.update_project(project_id, {"status": "complete", "current_stage": 5})
    return HitlReview.model_validate(review)


@router.post("/gaps/{gap_id}/explain")
async def explain_gap(
    project_id: str,
    gap_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Grounded explanation of one gap (Instagram).

    Retrieves the closest post chunks for each side from pgvector
    (instagram_post_chunks) and asks the LLM to explain the gap using only
    those, citing them. Citations to anything not retrieved are rejected.
    """
    from app.analysis.instagram import explain
    from app.analysis.instagram.llm import get_llm

    repo = get_repository(user.id, user.token)
    project = repo.get_project(project_id)
    if project.get("social_platform") != "instagram":
        raise ConflictError("Explanations are available for Instagram comparisons.")

    try:
        result = await asyncio.to_thread(
            explain.explain_gap, repo, project_id, gap_id, get_llm()
        )
    except (ConflictError, NotFoundError):
        raise
    except Exception as exc:  # noqa: BLE001 - show the real reason, not a bare 500
        logger.exception("Explain failed for gap %s", gap_id)
        raise ConflictError(f"Explain failed: {type(exc).__name__}: {exc}") from exc
    return {
        "gapId": result["gap_id"],
        "explanation": result["explanation"],
        "grounded": result["grounded"],
        "evidenceUsed": result["evidence_used"],
        "unknownCitations": result["unknown_citations"],
        "evidence": [
            {
                "id": e["id"],
                "side": e["side"],
                "fieldType": e["field_type"],
                "text": e["text"],
                "postUrl": e["post_url"],
                "similarity": e["similarity"],
                "format": e.get("format", ""),
            }
            for e in result["evidence"]
        ],
    }


# ---------------------------------------- stage 6 and stage 7: HITL #2 ------


@router.get("/strategy", response_model=Strategy | None)
async def get_strategy(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> Strategy | None:
    repo = get_repository(user.id, user.token)
    row = strategy_service.get_strategy(repo, project_id)
    return Strategy.model_validate(row) if row else None


@router.post("/strategy/generate", response_model=PipelineState)
async def generate_strategy(
    project_id: str,
    tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> PipelineState:
    """Re-runs stage 6 against the gaps already accepted at HITL #1."""
    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)

    gaps = repo.list_gaps(project_id)
    if not any(gap.get("decision") == "accepted" for gap in gaps):
        raise ConflictError(
            "No gaps have been accepted yet. Complete the first human checkpoint before "
            "generating a strategy."
        )

    state = pipeline_service.reopen_stage(repo, project_id, 6)
    _schedule(tasks, project_id, user.id, 6)
    return PipelineState.model_validate(state)


@router.get("/reviews", response_model=list[HitlReview])
async def list_reviews(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> list[HitlReview]:
    """The audit trail: every human decision recorded on this project."""
    repo = get_repository(user.id, user.token)
    return [
        HitlReview.model_validate(row) for row in strategy_service.list_reviews(repo, project_id)
    ]


@router.post("/strategy/approve", response_model=HitlReview)
async def approve_strategy(
    project_id: str,
    payload: StrategyReviewSubmit,
    tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> HitlReview:
    """Closes HITL #2 with an approval and releases stages 8 and 9."""
    if payload.decision is not ReviewDecision.APPROVED:
        raise ConflictError("Use /strategy/revise to send a strategy back.")

    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)
    review, next_stage = strategy_service.submit_review(
        repo, project_id, user.id, user.email or "Reviewer", payload
    )
    if next_stage is not None:
        _schedule(tasks, project_id, user.id, next_stage)
    return HitlReview.model_validate(review)


@router.post("/strategy/revise", response_model=HitlReview)
async def revise_strategy(
    project_id: str,
    payload: StrategyReviewSubmit,
    tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> HitlReview:
    """Closes HITL #2 with a rejection or revision request, and re-runs stage 6."""
    if payload.decision is ReviewDecision.APPROVED:
        raise ConflictError("Use /strategy/approve to approve a strategy.")

    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)
    review, next_stage = strategy_service.submit_review(
        repo, project_id, user.id, user.email or "Reviewer", payload
    )
    if next_stage is not None:
        _schedule(tasks, project_id, user.id, next_stage)
    return HitlReview.model_validate(review)