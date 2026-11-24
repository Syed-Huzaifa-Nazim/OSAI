"""Token operations. Postgres RPCs own all balance and run transitions."""
from __future__ import annotations

from app.core.errors import AppError, ConflictError, ForbiddenError, ServiceUnavailableError
from app.core.security import CurrentUser
from app.core.supabase import get_service_client, get_user_client


def client_for(user: CurrentUser):
    if user.is_demo:
        raise ServiceUnavailableError("Tokens require a configured account.")
    return get_user_client(user.token)


def rpc(user: CurrentUser, name: str, params: dict):
    try:
        return client_for(user).rpc(name, params).execute().data
    except AppError:
        raise
    except Exception as exc:
        raise ConflictError(f"Token operation failed: {exc}") from exc


def require_admin(user: CurrentUser) -> None:
    if user.is_demo:
        raise ForbiddenError("Admin access requires a verified account.")
    if client_for(user).rpc("is_admin").execute().data is not True:
        raise ForbiddenError("Admin access required.")


def reserve(user: CurrentUser, project_id: str) -> str:
    rpc(user, "release_stale_scrapes", {})
    return str(rpc(user, "reserve_scrape_token", {"p_project_id": project_id}))


def finish(run_id: str, success: bool, reason: str | None = None) -> str:
    return str(get_service_client().rpc("finish_scrape_token", {
        "p_run_id": run_id, "p_success": success, "p_reason": reason,
    }).execute().data)


def run_status(run_id: str) -> str:
    rows = (get_service_client().table("token_runs").select("status")
            .eq("id", run_id).limit(1).execute().data or [])
    return rows[0]["status"] if rows else "missing"


def cancel(user: CurrentUser, run_id: str) -> str:
    return str(rpc(user, "cancel_scrape_token", {"p_run_id": run_id}))
