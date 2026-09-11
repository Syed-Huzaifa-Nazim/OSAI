"""Authentication: verify the Supabase JWT and identify the caller.

The token the browser holds is passed straight through to Supabase on every
data call, so Postgres row-level security, not application code, decides
what a user can read. This module only establishes *who* is asking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

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


#: Algorithms Supabase's asymmetric JWT signing keys use. Listed explicitly so
#: a token can never pick its own verification method (e.g. "none").
ASYMMETRIC_ALGORITHMS = ["ES256", "RS256", "EdDSA"]


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    """The project's public signing keys, fetched once and cached.

    Supabase projects created or migrated to *JWT signing keys* sign user
    sessions with an asymmetric key (ES256 here), published at this endpoint.
    Only the public half is fetched; nothing secret is involved.
    """
    return jwt.PyJWKClient(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
        headers={"apikey": settings.supabase_anon_key},
        timeout=10,
    )


def _decode(token: str) -> dict:
    """Verifies a Supabase session token, whichever way the project signs it.

    Supabase supports two signing schemes and a project can have either:

      * legacy: HS256 with the shared JWT secret
      * signing keys: ES256/RS256, verified against the public JWKS

    Accepting only HS256 -- as this used to -- rejects every login on a project
    using signing keys, even though the anon key (still HS256) verifies fine.
    The algorithm is read from the token header only to choose *which* key to
    check against; each branch still pins its allowed algorithms.
    """
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")

        if algorithm == "HS256":
            if not settings.supabase_jwt_secret:
                # Misconfiguration, not a client error, so say so plainly
                # rather than letting every request fail as "unauthorized".
                logger.error("SUPABASE_JWT_SECRET is not set; HS256 tokens cannot be verified")
                raise UnauthorizedError(
                    "The server cannot verify sessions right now.", code="auth_misconfigured"
                )
            key: object = settings.supabase_jwt_secret
            algorithms = ["HS256"]
        elif algorithm in ASYMMETRIC_ALGORITHMS:
            key = _jwks_client().get_signing_key_from_jwt(token).key
            algorithms = ASYMMETRIC_ALGORITHMS
        else:
            raise UnauthorizedError(
                "That session token is not valid.", code="invalid_token"
            )

        return jwt.decode(token, key, algorithms=algorithms, audience="authenticated")
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError(
            "Your session has expired. Please log in again.", code="token_expired"
        ) from exc
    except jwt.PyJWKClientConnectionError as exc:
        logger.error("Could not fetch Supabase signing keys: %s", exc)
        raise UnauthorizedError(
            "The server cannot verify sessions right now.", code="auth_unavailable"
        ) from exc
    except jwt.PyJWKClientError as exc:
        # Unknown key id: signed by a key this project does not publish.
        raise UnauthorizedError("That session token is not valid.", code="invalid_token") from exc
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
