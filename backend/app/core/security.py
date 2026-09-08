"""Authentication: verify the Supabase JWT and identify the caller.

The token the browser holds is passed straight through to Supabase on every
data call, so Postgres row-level security, not application code, decides
what a user can read. This module only establishes *who* is asking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.errors import UnauthorizedError

logger = logging.getLogger("optistratix.security")

# auto_error=False so a missing header raises our own envelope, not FastAPI's.
bearer_scheme = HTTPBearer(auto_error=False)

DEMO_USER_ID = "demo-user-0001"
DEMO_USER_EMAIL = "demo@optistratix.ai"


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    """The raw JWT, forwarded to Supabase so RLS applies to every query."""
    token: str
    is_demo: bool = False


def _decode(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError(
            "Your session has expired. Please log in again.", code="token_expired"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("That session token is not valid.", code="invalid_token") from exc


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Resolves the caller, or raises 401.

    In demo mode there is no Supabase project to verify against, so a fixed
    demo identity is returned and every request operates on the in-memory
    dataset. This is what lets the API run with zero configuration.
    """
    if settings.is_demo:
        return CurrentUser(
            id=DEMO_USER_ID, email=DEMO_USER_EMAIL, token="demo-token", is_demo=True
        )

    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("You need to be signed in to do that.")

    if not settings.supabase_jwt_secret:
        # Misconfiguration, not a client error, say so plainly rather than
        # letting every request fail as "unauthorized".
        logger.error("SUPABASE_JWT_SECRET is not set; tokens cannot be verified")
        raise UnauthorizedError(
            "The server cannot verify sessions right now.", code="auth_misconfigured"
        )

    payload = _decode(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("That session token is missing a subject.", code="invalid_token")

    request.state.user_id = user_id
    return CurrentUser(
        id=user_id,
        email=payload.get("email", ""),
        token=credentials.credentials,
    )
