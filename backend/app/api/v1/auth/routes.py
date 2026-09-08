"""Auth-adjacent endpoints.

Sign-up, sign-in, password reset and session refresh are all handled by Supabase
Auth directly from the browser: the backend never sees a password. What lives
here is only what the API itself needs: confirming who a token belongs to, and
the public contact form.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response, status

from app.core.security import CurrentUser, get_current_user
from app.models.misc import ContactSubmission, UserProfile
from app.services import demo_data
from app.services.repository import get_repository

logger = logging.getLogger("optistratix.auth")

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=UserProfile)
async def whoami(user: CurrentUser = Depends(get_current_user)) -> UserProfile:
    """Confirms a token is valid and returns who it belongs to."""
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name="Demo Reviewer" if user.is_demo else None,
        avatar_url=None,
        created_at=demo_data.iso(),
    )


@router.post(
    "/contact",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def submit_contact(payload: ContactSubmission) -> Response:
    """Public contact form.

    Stores the submission. Outbound email is NOT configured. Nothing is sent
    anywhere, and the UI says so. Wiring a transactional provider is tracked in
    docs/project-status.md.
    """
    repo = get_repository(user_id="anonymous", token="")
    repo.insert_contact(
        {
            "name": payload.name,
            "email": str(payload.email),
            "organisation": payload.organisation,
            "message": payload.message,
            "created_at": demo_data.iso(),
        }
    )
    logger.info("Contact submission stored from %s", payload.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
