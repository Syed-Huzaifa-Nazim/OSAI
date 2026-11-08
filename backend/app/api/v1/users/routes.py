"""User-scoped settings: integrations."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.errors import ConflictError
from app.core.security import CurrentUser, get_current_user
from app.models.misc import Integration
from app.services import demo_data
from app.services.repository import get_repository

router = APIRouter(tags=["users"])


@router.get("/integrations", response_model=list[Integration])
async def list_integrations(user: CurrentUser = Depends(get_current_user)) -> list[Integration]:
    """Feature modules available to connect. See docs/architecture.md."""
    repo = get_repository(user.id, user.token)
    return [Integration.model_validate(row) for row in repo.list_integrations()]


@router.post("/integrations/{integration_id}/toggle", response_model=Integration)
async def toggle_integration(
    integration_id: str, user: CurrentUser = Depends(get_current_user)
) -> Integration:
    repo = get_repository(user.id, user.token)
    current = next(
        (row for row in repo.list_integrations() if row["id"] == integration_id), None
    )
    if current is None:
        raise ConflictError("That integration does not exist.", status_code=404, code="not_found")
    if current.get("status") == "coming_soon":
        raise ConflictError("That module is not available yet.")

    connecting = current.get("status") != "connected"
    updated = repo.update_integration(
        integration_id,
        {
            "status": "connected" if connecting else "available",
            "connected_at": demo_data.iso() if connecting else None,
        },
    )
    return Integration.model_validate(updated)
