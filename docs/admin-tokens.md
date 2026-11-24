# Admin portal and token workflow

Apply `backend/app/db/migrations/0015_admin_tokens.sql` to the configured Supabase project after migrations 0001–0014. It creates the role, wallet, request, run, and ledger tables and their RLS policies and RPCs. The frontend and API must be released together after the migration; until then, scrape starts will fail safely instead of running without a token reservation.

Bootstrap the first admin with a **verified** Supabase Auth user ID in the SQL editor:

```sql
insert into public.admin_members (user_id)
values ('REPLACE_WITH_VERIFIED_AUTH_USER_UUID')
on conflict do nothing;
```

Alternatively, after the migration is applied and `backend/.env` points at the
same Supabase project, run `python scripts/bootstrap_admin.py` from `backend/`.
It prompts for the password without echoing or saving it, creates or updates
`admin@optistratixai.com`, grants admin membership, and verifies the row.

No email or client claim grants admin access. Subsequent role changes go through the protected admin API. A user cannot remove their own role or the final admin role.

Newly verified accounts receive three tokens from the verification trigger once. Existing accounts are deliberately not granted retroactive starter tokens; an admin can grant them with a recorded reason. A scrape reserves a token before work starts, spends it only after stages 2 and 3 succeed, and releases it on cancellation or failure. An interrupted reservation expires after four hours when the account next reads its token page or starts another scrape. Later analysis and strategy steps do not charge tokens.

The admin portal is at `/admin`. User token balance, requests, and ledger are at `/app/settings/tokens`. Admin management uses the service role only after a database-backed role check. Keep `SUPABASE_SERVICE_ROLE_KEY` on the backend only. No payment provider is connected.

The Postgres functions use row locks and unique active-run constraints. A retry of a finished run is idempotent; a duplicate active scrape cannot reserve a second token for the same project. A late worker cannot spend a reservation released by cancellation.
