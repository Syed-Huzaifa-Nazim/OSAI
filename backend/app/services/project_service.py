"""Project CRUD (stage 1)."""

from __future__ import annotations

from typing import Any

from app.models.project import ProjectCreate
from app.services import demo_data
from app.services.pipeline_service import empty_state
from app.services.repository import Repository, new_id
from app.vectorstore import chroma


def list_projects(repo: Repository) -> list[dict[str, Any]]:
    return repo.list_projects()


def get_project(repo: Repository, project_id: str) -> dict[str, Any]:
    return repo.get_project(project_id)


def create_project(repo: Repository, owner_id: str, payload: ProjectCreate) -> dict[str, Any]:
    """Writes the project, its competitors, and an empty pipeline in one go."""
    project_id = new_id("proj")
    now = demo_data.iso()

    project = {
        "id": project_id,
        "owner_id": owner_id,
        "brand_name": payload.brand_name,
        "brand_website": payload.brand_website or None,
        "brand_description": payload.brand_description,
        "industry": payload.industry.value,
        "target_audience": payload.target_audience,
        "objectives": payload.objectives,
        "comparison_type": payload.comparison_type.value,
        # Each platform is null except on its own comparison type; ProjectCreate
        # clears the other one.
        "ecommerce_platform": payload.ecommerce_platform,
        "social_platform": payload.social_platform.value if payload.social_platform else None,
        "status": "draft",
        "current_stage": 1,
        "competitor_count": len(payload.competitors),
        "gap_count": 0,
        "is_demo": False,
        "created_at": now,
        "updated_at": now,
    }
    repo.insert_project(project)

    repo.insert_competitors(
        [
            {
                "id": new_id("comp"),
                "project_id": project_id,
                "name": competitor.name,
                "landing_page_url": competitor.landing_page_url,
                "social_handles": [handle.model_dump() for handle in competitor.social_handles],
                "notes": competitor.notes,
                "created_at": now,
            }
            for competitor in payload.competitors
        ]
    )

    repo.save_pipeline(project_id, empty_state(project_id))
    return project


def delete_project(repo: Repository, project_id: str) -> None:
    repo.delete_project(project_id)
    chroma.delete_collection(project_id)


def list_competitors(repo: Repository, project_id: str) -> list[dict[str, Any]]:
    # Reading the project first turns a cross-tenant id into a clean 404 rather
    # than an empty list, which is a clearer answer for the client.
    repo.get_project(project_id)
    return repo.list_competitors(project_id)
