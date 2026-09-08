"""Stages 8 and 9: the strategy document, its exports, and content assets."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response

from app.core.errors import ServiceUnavailableError
from app.core.security import CurrentUser, get_current_user
from app.models.document import (
    ContentSuggestion,
    ContentSuggestionPatch,
    DocumentFormat,
    StrategyDocument,
)
from app.models.pipeline import PipelineState
from app.services import automation_service, document_service, pipeline_service
from app.services.repository import get_repository

logger = logging.getLogger("optistratix.documents.routes")

router = APIRouter(prefix="/projects/{project_id}", tags=["documents"])

_MEDIA_TYPES = {
    DocumentFormat.PDF: "application/pdf",
    DocumentFormat.DOCX: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    DocumentFormat.MARKDOWN: "text/markdown; charset=utf-8",
}

_EXTENSIONS = {
    DocumentFormat.PDF: "pdf",
    DocumentFormat.DOCX: "docx",
    DocumentFormat.MARKDOWN: "md",
}


@router.get("/document", response_model=StrategyDocument | None)
async def get_document(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> StrategyDocument | None:
    repo = get_repository(user.id, user.token)
    row = document_service.get_document(repo, project_id)
    return StrategyDocument.model_validate(row) if row else None


@router.post("/document/generate", response_model=PipelineState)
async def generate_document(
    project_id: str,
    tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> PipelineState:
    """Re-runs stage 8 against the current strategy."""
    repo = get_repository(user.id, user.token)
    repo.get_project(project_id)
    state = pipeline_service.reopen_stage(repo, project_id, 8)

    def runner() -> None:
        import asyncio

        try:
            asyncio.run(pipeline_service.run_from(project_id, user.id, 8))
        except Exception:  # noqa: BLE001
            logger.exception("Document generation failed for %s", project_id)

    tasks.add_task(runner)
    return PipelineState.model_validate(state)


@router.get("/document/export")
async def export_document(
    project_id: str,
    format: DocumentFormat = Query(default=DocumentFormat.PDF),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    """Streams the document as PDF, DOCX or Markdown.

    A missing rendering library is a deployment gap, not a client error, so it
    comes back as 503 with an actionable message rather than a 500.
    """
    repo = get_repository(user.id, user.token)
    document = document_service.require_document(repo, project_id)

    try:
        if format is DocumentFormat.PDF:
            payload = document_service.render_pdf(document)
        elif format is DocumentFormat.DOCX:
            payload = document_service.render_docx(document)
        else:
            payload = document_service.render_markdown(document)
    except ImportError as exc:
        raise ServiceUnavailableError(
            f"The {format.value.upper()} renderer is not installed on the server. "
            "Run: pip install -r requirements.txt"
        ) from exc

    slug = "".join(
        char if char.isalnum() else "-" for char in document["title"].lower()
    ).strip("-")[:80]
    filename = f"{slug or 'strategy'}.{_EXTENSIONS[format]}"

    return Response(
        content=payload,
        media_type=_MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ------------------------------------------------------- stage 9: assets ----


@router.get("/automation", response_model=list[ContentSuggestion])
async def list_suggestions(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> list[ContentSuggestion]:
    repo = get_repository(user.id, user.token)
    return [
        ContentSuggestion.model_validate(row)
        for row in automation_service.list_suggestions(repo, project_id)
    ]


@router.post("/automation/suggest", response_model=list[ContentSuggestion])
async def generate_suggestions(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> list[ContentSuggestion]:
    repo = get_repository(user.id, user.token)
    return [
        ContentSuggestion.model_validate(row)
        for row in automation_service.generate(repo, project_id)
    ]


@router.patch("/automation/{suggestion_id}", response_model=ContentSuggestion)
async def update_suggestion(
    project_id: str,
    suggestion_id: str,
    payload: ContentSuggestionPatch,
    user: CurrentUser = Depends(get_current_user),
) -> ContentSuggestion:
    repo = get_repository(user.id, user.token)
    return ContentSuggestion.model_validate(
        automation_service.update(repo, project_id, suggestion_id, payload)
    )


@router.post("/automation/{suggestion_id}/draft", response_model=ContentSuggestion)
async def draft_suggestion(
    project_id: str,
    suggestion_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> ContentSuggestion:
    """Generates the full asset body for one suggestion."""
    repo = get_repository(user.id, user.token)
    return ContentSuggestion.model_validate(
        automation_service.draft(repo, project_id, suggestion_id)
    )
