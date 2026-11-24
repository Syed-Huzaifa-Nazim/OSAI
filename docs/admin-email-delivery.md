# Admin users and email delivery

The Users page lets an administrator create a verified or unverified Supabase
account without setting a password. It queues an onboarding email for either
status. Only an address whose ownership is already known should be marked
verified; that status also triggers the verified-user starter token grant.

The user details modal has Overview, Activity, and Email tabs. The Email tab
offers welcome, verification, password setup, token update, announcement, and
custom drafts. Drafts are stored in public.admin_email_outbox, created by
0016_admin_email_outbox.sql. The table uses RLS and is accessed only through
admin-checked backend routes with the service role. Its initial status is
pending_provider. **No email is sent by this implementation.** The UI and
API both report that status explicitly.

## When GCP email delivery is added

1. Choose and configure a GCP mail delivery service and verified sender
   identity. Store credentials only in the backend hosting environment.
2. Build a background worker that claims pending outbox rows without duplicate
   delivery, sends through GCP, and records sent_at or a failure. Apply retry
   limits and an audit trail.
3. At send time, generate Supabase verification/password setup links for the
   intended account. Do not store action links or OTPs in the outbox. Replace
   placeholder onboarding text with the generated links.
4. Test delivery to verified and unverified test accounts, including expired
   links, retries, and failure states. Then enable the worker.

**Reminder for the next admin-email task:** GCP delivery and Supabase action-link
generation are still required. Queued drafts must never be described as sent.
