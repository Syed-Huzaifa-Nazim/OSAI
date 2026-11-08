"""Supabase clients.

Two are available and the distinction matters:

  * ``get_user_client(token)``. Runs as the signed-in user. Row-level security
    applies, so a query can only ever return that user's rows. Use this on
    every request path.

  * ``get_service_client()``. Runs as the service role and BYPASSES RLS. Only
    the background pipeline worker uses it, because it acts on a project after
    the request that started it has already returned. It must never be reachable
    from a request handler.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import settings
from app.core.errors import ServiceUnavailableError

logger = logging.getLogger("optistratix.supabase")

try:  # pragma: no cover - import guard so the app runs without the package
    from supabase import Client, create_client
except ImportError:  # pragma: no cover
    Client = object  # type: ignore[assignment,misc]
    create_client = None  # type: ignore[assignment]


def _require_client_library() -> None:
    if create_client is None:
        raise ServiceUnavailableError(
            "The supabase package is not installed. Run: pip install -r requirements.txt"
        )


def get_user_client(token: str) -> "Client":
    """A client scoped to one user's JWT. RLS decides what it can see."""
    if not settings.has_supabase:
        raise ServiceUnavailableError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY, "
            "or run with DEMO_MODE=true."
        )
    _require_client_library()

    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    # Every PostgREST call now carries the user's token, so RLS policies apply.
    client.postgrest.auth(token)
    return client


@lru_cache
def get_service_client() -> "Client":
    """Service-role client. Bypasses RLS, background jobs only."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ServiceUnavailableError(
            "SUPABASE_SERVICE_ROLE_KEY is not configured; background jobs cannot run."
        )
    _require_client_library()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
