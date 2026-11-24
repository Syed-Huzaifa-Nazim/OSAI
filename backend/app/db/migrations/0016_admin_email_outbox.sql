-- Admin email drafts wait here until a GCP mail transport is configured.
-- No row in this table means an email was delivered.
create table if not exists public.admin_email_outbox (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    recipient_email text not null,
    email_type text not null check (email_type in (
        'account_verified', 'verification', 'password_setup',
        'token_update', 'announcement', 'custom'
    )),
    subject text not null check (char_length(subject) between 1 and 200),
    body text not null check (char_length(body) between 1 and 10000),
    status text not null default 'pending_provider' check (status in ('pending_provider', 'sent', 'failed')),
    created_by uuid references auth.users(id) on delete set null,
    created_at timestamptz not null default now(),
    sent_at timestamptz,
    failure_reason text
);
create index if not exists admin_email_outbox_user_idx
    on public.admin_email_outbox(user_id, created_at desc);
alter table public.admin_email_outbox enable row level security;
-- Only the backend service role can read and write queued mail. Admin access
-- is checked by the API before it uses that role.
