"""Account tokens and requests. Mutations are atomic Postgres functions."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.security import CurrentUser, get_current_user
from app.services.token_service import client_for, rpc

router = APIRouter(prefix="/tokens", tags=["tokens"])


class TokenRequestInput(BaseModel):
    amount: int = Field(ge=1, le=1000)
    note: str = Field(min_length=1, max_length=1000)


@router.get("/me")
async def my_tokens(user: CurrentUser = Depends(get_current_user)) -> dict:
    rpc(user, "release_stale_scrapes", {})
    client = client_for(user)
    wallet = (client.table("token_wallets").select("balance,reserved,starter_awarded")
              .eq("user_id", user.id).limit(1).execute().data or [])
    ledger = (client.table("token_ledger").select("id,event,delta,balance_after,run_id,request_id,reason,created_at")
              .eq("user_id", user.id).order("created_at", desc=True).limit(100).execute().data or [])
    requests = (client.table("token_requests").select("id,amount,note,status,admin_response,created_at,reviewed_at")
                .eq("user_id", user.id).order("created_at", desc=True).limit(100).execute().data or [])
    return {"wallet": wallet[0] if wallet else {"balance": 0, "reserved": 0, "starter_awarded": False},
            "ledger": ledger, "requests": requests}


@router.post("/requests", status_code=201)
async def request_tokens(payload: TokenRequestInput, user: CurrentUser = Depends(get_current_user)) -> dict:
    request_id = rpc(user, "request_tokens", {"p_amount": payload.amount, "p_note": payload.note})
    return {"id": request_id, "status": "pending"}
