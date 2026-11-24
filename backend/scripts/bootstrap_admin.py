"""One-time admin bootstrap for the Supabase project in backend/.env.

Run only after migration 0015. The password is read without echoing it and is
never written to disk or included in command-line arguments.
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


EMAIL = "admin@optistratixai.com"


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Configure the Supabase URL and service-role key in backend/.env first.", file=sys.stderr)
        return 1
    client = create_client(url, key)

    # Check the migration before creating or changing any Auth account.
    try:
        client.table("admin_members").select("user_id").limit(1).execute()
    except Exception:
        print("Admin migration 0015 is not accessible in the configured project.", file=sys.stderr)
        return 1

    password = getpass.getpass(f"Password for {EMAIL}: ")
    if len(password) < 12:
        print("Password must have at least 12 characters.", file=sys.stderr)
        return 1

    page = 1
    account = None
    while True:
        users = client.auth.admin.list_users(page=page, per_page=200)
        account = next((user for user in users if (user.email or "").lower() == EMAIL), None)
        if account or len(users) < 200:
            break
        page += 1

    if account:
        account = client.auth.admin.update_user_by_id(
            str(account.id), {"password": password, "email_confirm": True}
        ).user
    else:
        account = client.auth.admin.create_user(
            {"email": EMAIL, "password": password, "email_confirm": True}
        ).user
    password = ""
    if account is None:
        print("Auth did not return an account; admin membership was not changed.", file=sys.stderr)
        return 1

    client.table("admin_members").upsert({"user_id": str(account.id)}, on_conflict="user_id").execute()
    rows = (client.table("admin_members").select("user_id")
            .eq("user_id", str(account.id)).limit(1).execute().data or [])
    if not rows:
        print("Account exists, but admin membership could not be verified.", file=sys.stderr)
        return 1
    print(f"Verified admin membership for {EMAIL}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
