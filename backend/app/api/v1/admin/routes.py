"""Admin management API. Every entry point checks the database-backed role."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import Literal
from supabase_auth.errors import AuthApiError

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ServiceUnavailableError
from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_service_client
from app.services.token_service import require_admin, rpc

router = APIRouter(prefix="/admin", tags=["admin"])

# Expose only fields useful for management; never return raw metadata, config,
# auth tokens, password hashes, or scraper payloads through generic endpoints.
RESOURCES = {
    "projects": ("id,owner_id,brand_name,industry,comparison_type,status,current_stage,created_at,updated_at", "brand_name", {"brand_name", "status"}),
    "competitors": ("id,project_id,name,landing_page_url,notes,created_at", "name", {"name", "notes"}),
    "sources": ("id,project_id,kind,url,title,status,scraped_at", "title", {"title", "status"}),
    "products": ("id,project_id,role,product_name,url,scraped_at", "product_name", {"product_name"}),
    "website-pages": ("id,project_id,role,page_url,title,depth,scraped_at", "title", {"title"}),
    "instagram-posts": ("id,project_id,role,post_url,caption,posted_at", "caption", {"caption"}),
    "gaps": ("id,project_id,title,category,decision,user_priority,created_at", "title", {"title", "decision", "user_priority"}),
    "strategies": ("id,project_id,title,status,generated_at", "title", {"title", "status"}),
    "reviews": ("id,project_id,stage,decision,created_at", "decision", set()),
    "documents": ("id,project_id,title,generated_at", "title", {"title"}),
    "suggestions": ("id,project_id,title,status,created_at", "title", {"title", "status"}),
    "integrations": ("id,owner_id,feature_key,name,status,created_at", "name", {"name", "status"}),
    "contacts": ("id,name,email,organisation,message,created_at", "email", set()),
}
TABLES = {"sources": "scraped_sources", "products": "ecommerce_products", "website-pages": "website_pages",
          "instagram-posts": "instagram_posts", "gaps": "gaps_opportunities", "reviews": "hitl_reviews",
          "documents": "strategy_documents", "suggestions": "content_suggestions",
          "contacts": "contact_submissions"}


def admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    require_admin(user)
    return user


def resource(name: str):
    if name not in RESOURCES:
        raise NotFoundError("Unknown management area.")
    return TABLES.get(name, name), RESOURCES[name]


def all_accounts(client):
    page = 1
    while True:
        batch = client.auth.admin.list_users(page=page, per_page=200)
        yield from batch
        if len(batch) < 200:
            return
        page += 1


@router.get("/me")
async def admin_me(user: CurrentUser = Depends(admin)) -> dict:
    client = get_service_client()
    # 24-hour completed run count powers a non-blocking cost reminder.
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    runs = (client.table("token_runs").select("id", count="exact")
            .eq("user_id", user.id).eq("status", "spent").gte("finished_at", since)
            .limit(1).execute())
    return {"isAdmin": True, "completedRuns24h": runs.count or 0}


@router.get("/summary")
async def summary(user: CurrentUser = Depends(admin)) -> dict:
    client = get_service_client()
    result = {}
    for name, table in (("projects", "projects"), ("requests", "token_requests"),
                        ("contacts", "contact_submissions"), ("runs", "token_runs")):
        result[name] = client.table(table).select("id", count="exact").limit(1).execute().count or 0
    result["users"] = sum(1 for _ in all_accounts(client))
    return result


@router.get("/users")
async def users(q: str = Query("", max_length=120), user: CurrentUser = Depends(admin)) -> list[dict]:
    client = get_service_client()
    members = {row["user_id"] for row in (client.table("admin_members").select("user_id").execute().data or [])}
    wallets = {row["user_id"]: row for row in (client.table("token_wallets").select("user_id,balance,reserved,starter_awarded").execute().data or [])}
    result = []
    for account in all_accounts(client):
        email = account.email or ""
        if q and q.lower() not in email.lower() and q.lower() not in str(account.id).lower():
            continue
        result.append({"id": str(account.id), "email": email,
                       "verified": account.email_confirmed_at is not None,
                       "created_at": str(account.created_at), "is_admin": str(account.id) in members,
                       "wallet": wallets.get(str(account.id), {"balance": 0, "reserved": 0})})
    return result


class UserPatch(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    is_admin: bool | None = None


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    full_name: str = Field(min_length=1, max_length=120)
    verified: bool = False


@router.post("/users", status_code=201)
async def create_user(payload: UserCreate, user: CurrentUser = Depends(admin)) -> dict:
    client = get_service_client()
    if not payload.full_name.strip():
        raise ConflictError("Enter a full name.")
    try:
        # Fail before creating an auth account if the delivery queue is absent.
        client.table("admin_email_outbox").select("id").limit(1).execute()
    except Exception as exc:
        raise ServiceUnavailableError("Apply migration 0016 before creating users.") from exc
    try:
        created = client.auth.admin.create_user({
            "email": payload.email.strip().lower(),
            "email_confirm": payload.verified,
            "user_metadata": {"full_name": payload.full_name.strip()},
        }).user
    except AuthApiError as exc:
        if exc.status in (400, 409, 422) or str(exc.code) == "email_exists":
            raise ConflictError("This email already has an account or cannot be created.") from exc
        raise
    if created is None:
        raise ServiceUnavailableError("Supabase did not return the new account.")
    kind = "account_verified" if payload.verified else "verification"
    subject = "Your OptiStratixAI account is ready" if payload.verified else "Verify your OptiStratixAI account"
    body = ("An administrator created your verified OptiStratixAI account. "
            "A password setup email will follow when mail delivery is enabled." if payload.verified else
            "An administrator created your OptiStratixAI account. "
            "A verification and password setup email will follow when mail delivery is enabled.")
    try:
        client.table("admin_email_outbox").insert({
            "user_id": str(created.id), "recipient_email": payload.email.strip().lower(),
            "email_type": kind, "subject": subject, "body": body,
            "created_by": user.id,
        }).execute()
    except Exception as exc:
        # The account already exists. Return its ID so the admin can open it
        # and retry the email instead of blindly creating a duplicate.
        return {"id": str(created.id), "verified": payload.verified,
                "email_status": "queue_failed"}
    return {"id": str(created.id), "verified": payload.verified,
            "email_status": "pending_provider"}


EmailType = Literal["account_verified", "verification", "password_setup",
                    "token_update", "announcement", "custom"]


class UserEmail(BaseModel):
    email_type: EmailType
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)


@router.get("/users/{user_id}/emails")
async def user_emails(user_id: str, user: CurrentUser = Depends(admin)) -> list[dict]:
    client = get_service_client()
    if client.auth.admin.get_user_by_id(user_id).user is None:
        raise NotFoundError("User not found.")
    return (client.table("admin_email_outbox")
            .select("id,email_type,subject,body,status,created_at,sent_at,failure_reason")
            .eq("user_id", user_id).order("created_at", desc=True)
            .limit(100).execute().data or [])


@router.post("/users/{user_id}/emails", status_code=201)
async def queue_user_email(user_id: str, payload: UserEmail,
                           user: CurrentUser = Depends(admin)) -> dict:
    if not payload.subject.strip() or not payload.body.strip():
        raise ConflictError("Email subject and message are required.")
    client = get_service_client()
    account = client.auth.admin.get_user_by_id(user_id).user
    if account is None or not account.email:
        raise NotFoundError("User with an email address not found.")
    row = (client.table("admin_email_outbox").insert({
        "user_id": user_id, "recipient_email": account.email,
        "email_type": payload.email_type,
        "subject": payload.subject.strip(), "body": payload.body.strip(),
        "created_by": user.id,
    }).execute().data or [])[0]
    return {"id": row["id"], "status": row["status"]}


@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UserPatch, user: CurrentUser = Depends(admin)) -> dict:
    client = get_service_client()
    if payload.is_admin is not None:
        rpc(user, "set_admin_member", {"p_user_id": user_id, "p_enabled": payload.is_admin})
    if payload.full_name is not None:
        account = client.auth.admin.get_user_by_id(user_id).user
        if account is None:
            raise NotFoundError("User not found.")
        client.auth.admin.update_user_by_id(user_id, {"user_metadata": {
            **(account.user_metadata or {}), "full_name": payload.full_name}})
    return {"updated": True}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: CurrentUser = Depends(admin)) -> dict:
    if user.id == user_id:
        raise ForbiddenError("You cannot delete your own admin account.")
    client = get_service_client()
    if client.table("admin_members").select("user_id").eq("user_id", user_id).execute().data:
        raise ForbiddenError("Remove admin access before deleting this account.")
    if client.table("token_runs").select("id").eq("user_id", user_id).eq("status", "reserved").execute().data:
        raise ConflictError("Cancel this user's active scrape before deleting the account.")
    client.auth.admin.delete_user(user_id)
    return {"deleted": True}


@router.get("/users/{user_id}")
async def user_detail(user_id: str, user: CurrentUser = Depends(admin)) -> dict:
    client = get_service_client()
    account = client.auth.admin.get_user_by_id(user_id).user
    if account is None:
        raise NotFoundError("User not found.")
    wallet = client.table("token_wallets").select("*").eq("user_id", user_id).limit(1).execute().data or []
    ledger = client.table("token_ledger").select("id,event,delta,balance_after,reason,created_at").eq("user_id", user_id).order("created_at", desc=True).limit(100).execute().data or []
    runs = client.table("token_runs").select("id,project_id,status,created_at,finished_at").eq("user_id", user_id).order("created_at", desc=True).limit(100).execute().data or []
    requests = client.table("token_requests").select("id,amount,note,status,created_at,reviewed_at").eq("user_id", user_id).order("created_at", desc=True).limit(100).execute().data or []
    projects = client.table("projects").select("id,brand_name,status,created_at").eq("owner_id", user_id).order("created_at", desc=True).limit(100).execute().data or []
    return {"id": str(account.id), "email": account.email, "verified": account.email_confirmed_at is not None,
            "created_at": str(account.created_at), "full_name": (account.user_metadata or {}).get("full_name"),
            "email_confirmed_at": str(account.email_confirmed_at) if account.email_confirmed_at else None,
            "last_sign_in_at": str(account.last_sign_in_at) if account.last_sign_in_at else None,
            "updated_at": str(account.updated_at) if account.updated_at else None,
            "is_admin": bool(client.table("admin_members").select("user_id").eq("user_id", user_id).execute().data),
            "wallet": wallet[0] if wallet else {"balance": 0, "reserved": 0}, "ledger": ledger,
            "runs": runs, "requests": requests, "projects": projects}


class Adjustment(BaseModel):
    delta: int = Field(ge=-1000, le=1000)
    reason: str = Field(min_length=1, max_length=500)


@router.post("/users/{user_id}/tokens")
async def adjust(user_id: str, payload: Adjustment, user: CurrentUser = Depends(admin)) -> dict:
    if payload.delta == 0:
        raise ConflictError("Choose a nonzero token adjustment.")
    return {"balance": rpc(user, "adjust_tokens", {"p_user_id": user_id,
                                                   "p_delta": payload.delta, "p_reason": payload.reason})}


@router.get("/token-requests")
async def token_requests(status: str = Query("", pattern="^(|pending|approved|rejected)$"),
                         user: CurrentUser = Depends(admin)) -> list[dict]:
    query = get_service_client().table("token_requests").select("id,user_id,amount,note,status,admin_response,created_at,reviewed_at")
    if status:
        query = query.eq("status", status)
    return query.order("created_at", desc=True).limit(200).execute().data or []


class ReviewInput(BaseModel):
    approve: bool
    response: str = Field(min_length=1, max_length=1000)


@router.post("/token-requests/{request_id}/review")
async def review(request_id: str, payload: ReviewInput, user: CurrentUser = Depends(admin)) -> dict:
    return {"status": rpc(user, "review_token_request", {"p_request_id": request_id,
                    "p_approve": payload.approve, "p_response": payload.response})}


@router.get("/ledger")
async def ledger(q: str = Query("", max_length=120), user: CurrentUser = Depends(admin)) -> list[dict]:
    query = get_service_client().table("token_ledger").select("id,user_id,event,delta,balance_after,reason,created_at,run_id,request_id")
    if q:
        query = query.eq("user_id", q)
    return query.order("created_at", desc=True).limit(300).execute().data or []


@router.get("/resources/{name}")
async def list_resource(name: str, q: str = Query("", max_length=120),
                        user: CurrentUser = Depends(admin)) -> list[dict]:
    table, (columns, search, _) = resource(name)
    query = get_service_client().table(table).select(columns)
    if q:
        query = query.ilike(search, f"%{q.replace('%', '').replace('_', '')}%")
    return query.limit(200).execute().data or []


class ResourcePatch(BaseModel):
    changes: dict[str, str | None]


@router.patch("/resources/{name}/{record_id}")
async def update_resource(name: str, record_id: str, payload: ResourcePatch,
                          user: CurrentUser = Depends(admin)) -> dict:
    table, (_, _, allowed) = resource(name)
    if not payload.changes or set(payload.changes) - allowed:
        raise ConflictError("Those fields cannot be edited here.")
    rows = get_service_client().table(table).update(payload.changes).eq("id", record_id).execute().data or []
    if not rows:
        raise NotFoundError("Record not found.")
    return {"updated": True}


@router.delete("/resources/{name}/{record_id}")
async def delete_resource(name: str, record_id: str, user: CurrentUser = Depends(admin)) -> dict:
    table, _ = resource(name)
    if name == "reviews":
        raise ConflictError("Review history is immutable.")
    if name == "projects":
        active = get_service_client().table("token_runs").select("id").eq("project_id", record_id).eq("status", "reserved").execute().data
        if active:
            raise ConflictError("Cancel the active scrape before deleting this project.")
    rows = get_service_client().table(table).delete().eq("id", record_id).execute().data or []
    if not rows:
        raise NotFoundError("Record not found.")
    return {"deleted": True}
