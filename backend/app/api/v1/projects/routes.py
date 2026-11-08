"""Projects and competitors (stage 1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.core.security import CurrentUser, get_current_user
from app.models.project import Competitor, Project, ProjectCreate
from app.services import project_service
from app.services.repository import get_repository

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[Project])
async def list_projects(user: CurrentUser = Depends(get_current_user)) -> list[Project]:
    repo = get_repository(user.id, user.token)
    return [Project.model_validate(row) for row in project_service.list_projects(repo)]


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, user: CurrentUser = Depends(get_current_user)
) -> Project:
    """Stage 1. Creates the project, its competitors and an empty pipeline.

    Nothing runs yet: the client starts the pipeline explicitly, so the intake
    can be reviewed before any scraping happens.
    """
    repo = get_repository(user.id, user.token)
    return Project.model_validate(project_service.create_project(repo, user.id, payload))


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> Project:
    repo = get_repository(user.id, user.token)
    return Project.model_validate(project_service.get_project(repo, project_id))


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_project(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> Response:
    repo = get_repository(user.id, user.token)
    project_service.delete_project(repo, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/competitors", response_model=list[Competitor])
async def list_competitors(
    project_id: str, user: CurrentUser = Depends(get_current_user)
) -> list[Competitor]:
    repo = get_repository(user.id, user.token)
    return [
        Competitor.model_validate(row)
        for row in project_service.list_competitors(repo, project_id)
    ]
