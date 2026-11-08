"""Stage 9: content suggestions."""

from __future__ import annotations

from typing import Any

from app.core.errors import ConflictError, NotFoundError
from app.models.document import ContentSuggestionPatch
from app.services import demo_data
from app.services.repository import Repository


def list_suggestions(repo: Repository, project_id: str) -> list[dict[str, Any]]:
    repo.get_project(project_id)
    return repo.list_suggestions(project_id)


def generate(repo: Repository, project_id: str) -> list[dict[str, Any]]:
    repo.get_project(project_id)
    strategy = repo.get_strategy(project_id)
    if strategy is None:
        raise ConflictError(
            "There is no strategy to generate content against. Work through the pipeline first."
        )

    suggestions = demo_data.build_suggestions(project_id, strategy)
    repo.replace_suggestions(project_id, suggestions)
    return suggestions


def update(
    repo: Repository, project_id: str, suggestion_id: str, patch: ContentSuggestionPatch
) -> dict[str, Any]:
    payload = patch.model_dump(exclude_none=True)
    if not payload:
        raise ConflictError("There is nothing to update in that request.")
    return repo.update_suggestion(project_id, suggestion_id, payload)


def draft(repo: Repository, project_id: str, suggestion_id: str) -> dict[str, Any]:
    """Generates the full asset body for one suggestion."""
    suggestions = repo.list_suggestions(project_id)
    match = next((item for item in suggestions if item["id"] == suggestion_id), None)
    if match is None:
        raise NotFoundError("That content suggestion does not exist on this project.")

    return repo.update_suggestion(
        project_id,
        suggestion_id,
        {"status": "generated", "body": demo_data.draft_suggestion_body(match)},
    )
