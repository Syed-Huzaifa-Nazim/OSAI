"""Strategy and HITL checkpoint #2 (stages 6-7)."""

from __future__ import annotations

from typing import Any

from app.core.errors import ConflictError, NotFoundError
from app.models.gap import ReviewDecision
from app.models.strategy import StrategyReviewSubmit
from app.services import demo_data, pipeline_service
from app.services.repository import Repository, new_id


def get_strategy(repo: Repository, project_id: str) -> dict[str, Any] | None:
    repo.get_project(project_id)
    return repo.get_strategy(project_id)


def list_reviews(repo: Repository, project_id: str) -> list[dict[str, Any]]:
    repo.get_project(project_id)
    return repo.list_reviews(project_id)


def submit_review(
    repo: Repository,
    project_id: str,
    reviewer_id: str,
    reviewer_name: str,
    payload: StrategyReviewSubmit,
) -> tuple[dict[str, Any], int | None]:
    """Closes HITL #2.

    Returns the review and, when the decision sends work back to the agents,
    the stage the caller should restart the runner from.
    """
    strategy = repo.get_strategy(project_id)
    if strategy is None:
        raise NotFoundError("There is no strategy on this project to review.")

    review = {
        "id": new_id("review"),
        "project_id": project_id,
        "stage": 7,
        "reviewer_id": reviewer_id,
        "reviewer_name": reviewer_name,
        "decision": payload.decision.value,
        "notes": payload.notes,
        "affected_ids": payload.flagged_ids,
        "created_at": demo_data.iso(),
    }

    if payload.decision is ReviewDecision.APPROVED:
        repo.insert_review(review)
        repo.update_strategy(
            strategy["id"], {"status": "approved", "approved_at": demo_data.iso()}
        )
        pipeline_service.close_checkpoint(
            repo, project_id, 7, "Strategy approved for execution"
        )
        return review, 8

    # Rejected or revision requested: the strategy goes back to stage 6, which
    # produces a new version rather than editing the rejected one in place.
    if not payload.notes:
        raise ConflictError(
            "Say what needs to change. The Strategist and Critic use your notes as their brief."
        )

    repo.insert_review(review)
    repo.clear_strategies(project_id)
    pipeline_service.reopen_stage(repo, project_id, 7)
    pipeline_service.reopen_stage(repo, project_id, 6)
    return review, 6
