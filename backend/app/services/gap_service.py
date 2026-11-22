"""Gaps and HITL checkpoint #1 (stages 4-5)."""

from __future__ import annotations

from typing import Any

from app.core.errors import ConflictError
from app.models.gap import GapPatch, GapReviewSubmit
from app.services import demo_data, pipeline_service
from app.services.post_stills import post_stills, with_stills
from app.services.repository import Repository, new_id


def list_gaps(repo: Repository, project_id: str) -> list[dict[str, Any]]:
    repo.get_project(project_id)
    gaps = repo.list_gaps(project_id)
    if any((g.get("details") or {}).get("examples") or ((g.get("details") or {}).get("explanation") or {}).get("evidence")
           for g in gaps):
        gaps = with_stills(gaps, post_stills(repo, project_id))
    return gaps


def update_gap(
    repo: Repository, project_id: str, gap_id: str, patch: GapPatch
) -> dict[str, Any]:
    payload = patch.model_dump(exclude_none=True)
    if not payload:
        raise ConflictError("There is nothing to update in that request.")
    # reviewer_note is the one field a caller may deliberately clear.
    if patch.reviewer_note is not None:
        payload["reviewer_note"] = patch.reviewer_note
    return repo.update_gap(project_id, gap_id, payload)


def submit_review(
    repo: Repository,
    project_id: str,
    reviewer_id: str,
    reviewer_name: str,
    payload: GapReviewSubmit,
) -> dict[str, Any]:
    """Closes HITL #1.

    Refuses while any gap is still untriaged: letting an unreviewed finding
    through to the Strategist is exactly what this checkpoint exists to stop.
    """
    gaps = repo.list_gaps(project_id)
    if not gaps:
        raise ConflictError("There are no gaps to review on this project yet.")

    pending = [gap for gap in gaps if gap.get("decision") == "pending"]
    if pending:
        raise ConflictError(
            f"{len(pending)} gap(s) still need a decision. Every gap has to be kept or "
            "dropped before this checkpoint can close."
        )

    accepted = [gap for gap in gaps if gap.get("decision") == "accepted"]
    if not accepted:
        raise ConflictError(
            "At least one gap has to be kept. There is nothing to build a strategy from "
            "otherwise."
        )

    review = {
        "id": new_id("review"),
        "project_id": project_id,
        "stage": 5,
        "reviewer_id": reviewer_id,
        "reviewer_name": reviewer_name,
        "decision": "approved",
        "notes": payload.notes,
        "affected_ids": [gap["id"] for gap in accepted],
        "created_at": demo_data.iso(),
    }
    repo.insert_review(review)

    pipeline_service.close_checkpoint(
        repo, project_id, 5, f"{len(accepted)} gaps prioritised"
    )
    return review
