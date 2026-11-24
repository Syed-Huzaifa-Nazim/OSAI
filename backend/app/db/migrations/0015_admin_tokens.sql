-- Apply after 0014. Admin bootstrap: insert a verified auth.users UUID into
-- public.admin_members using the Supabase SQL editor. Never grant by email.
create table if not exists public.admin_members (
    user_id uuid primary key references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);
alter table public.admin_members enable row level security;

create table if not exists public.token_wallets (
    user_id uuid primary key references auth.users(id) on delete cascade,
    balance integer not null default 0 check (balance >= 0),
    reserved integer not null default 0 check (reserved >= 0),
    starter_awarded boolean not null default false,
    updated_at timestamptz not null default now()
);
create table if not exists public.token_requests (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    amount integer not null check (amount between 1 and 1000),
    note text not null check (char_length(note) between 1 and 1000),
    status text not null default 'pending' check (status in ('pending','approved','rejected')),
    admin_response text,
    reviewed_by uuid references auth.users(id) on delete set null,
    created_at timestamptz not null default now(),
    reviewed_at timestamptz
);
create index if not exists token_requests_user_idx on public.token_requests(user_id, created_at desc);
create table if not exists public.token_runs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    -- Retain the project identifier in the audit trail even if its project is deleted.
    project_id text not null,
    status text not null default 'reserved' check (status in ('reserved','spent','released')),
    reason text,
    created_at timestamptz not null default now(),
    finished_at timestamptz
);
create unique index if not exists token_one_active_run on public.token_runs(project_id) where status='reserved';
create index if not exists token_runs_user_idx on public.token_runs(user_id, created_at desc);
create table if not exists public.token_ledger (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    event text not null check (event in ('starter','reserve','spend','release','admin_grant','admin_remove','request_grant')),
    delta integer not null,
    balance_after integer not null,
    run_id uuid references public.token_runs(id) on delete set null,
    request_id uuid references public.token_requests(id) on delete set null,
    actor_id uuid references auth.users(id) on delete set null,
    reason text,
    created_at timestamptz not null default now()
);
create index if not exists token_ledger_user_idx on public.token_ledger(user_id, created_at desc);
alter table public.token_wallets enable row level security;
alter table public.token_requests enable row level security;
alter table public.token_runs enable row level security;
alter table public.token_ledger enable row level security;
drop policy if exists token_wallet_read on public.token_wallets;
drop policy if exists token_requests_read on public.token_requests;
drop policy if exists token_runs_read on public.token_runs;
drop policy if exists token_ledger_read on public.token_ledger;
create policy token_wallet_read on public.token_wallets for select to authenticated using (user_id=auth.uid());
create policy token_requests_read on public.token_requests for select to authenticated using (user_id=auth.uid());
create policy token_runs_read on public.token_runs for select to authenticated using (user_id=auth.uid());
create policy token_ledger_read on public.token_ledger for select to authenticated using (user_id=auth.uid());

create or replace function public.is_admin() returns boolean language sql stable security definer
set search_path=public as $$ select exists(select 1 from public.admin_members where user_id=auth.uid()) $$;
revoke all on function public.is_admin() from public;
grant execute on function public.is_admin() to authenticated;

create or replace function public.set_admin_member(p_user_id uuid,p_enabled boolean) returns boolean
language plpgsql security definer set search_path=public as $$
begin
  if not public.is_admin() then raise exception 'Admin access required'; end if;
  perform pg_advisory_xact_lock(89424401);
  if p_enabled then
    if not exists(select 1 from auth.users where id=p_user_id and email_confirmed_at is not null) then
      raise exception 'User must be verified'; end if;
    insert into public.admin_members(user_id) values(p_user_id) on conflict do nothing;
  else
    if p_user_id=auth.uid() then raise exception 'Cannot remove your own admin access'; end if;
    if (select count(*) from public.admin_members)<=1 then raise exception 'Cannot remove the final admin'; end if;
    delete from public.admin_members where user_id=p_user_id;
  end if;
  return true;
end $$;
revoke all on function public.set_admin_member(uuid,boolean) from public;
grant execute on function public.set_admin_member(uuid,boolean) to authenticated;

-- A verification transition, never a login, issues the starter grant.
create or replace function public.award_starter_tokens() returns trigger language plpgsql security definer
set search_path=public as $$
declare w public.token_wallets%rowtype;
begin
  if new.email_confirmed_at is null then return new; end if;
  insert into public.token_wallets(user_id) values(new.id) on conflict do nothing;
  select * into w from public.token_wallets where user_id=new.id for update;
  if not w.starter_awarded then
    update public.token_wallets set balance=balance+3, starter_awarded=true, updated_at=now() where user_id=new.id returning * into w;
    insert into public.token_ledger(user_id,event,delta,balance_after,reason)
      values(new.id,'starter',3,w.balance,'Verified account starter grant');
  end if;
  return new;
end $$;
drop trigger if exists award_starter_tokens on auth.users;
create trigger award_starter_tokens after insert or update of email_confirmed_at on auth.users
for each row execute function public.award_starter_tokens();

create or replace function public.reserve_scrape_token(p_project_id text) returns uuid language plpgsql security definer
set search_path=public as $$
declare w public.token_wallets%rowtype; r uuid;
begin
  if auth.uid() is null then raise exception 'Authentication required'; end if;
  if not exists(select 1 from public.projects where id=p_project_id and owner_id=auth.uid()) then raise exception 'Project not found'; end if;
  select * into w from public.token_wallets where user_id=auth.uid() for update;
  if not found or w.balance < 1 then raise exception 'No tokens available'; end if;
  if exists(select 1 from public.token_runs where project_id=p_project_id and status='reserved') then raise exception 'Scrape already running'; end if;
  insert into public.token_runs(user_id,project_id) values(auth.uid(),p_project_id) returning id into r;
  update public.token_wallets set balance=balance-1,reserved=reserved+1,updated_at=now() where user_id=auth.uid() returning * into w;
  insert into public.token_ledger(user_id,event,delta,balance_after,run_id)
    values(auth.uid(),'reserve',-1,w.balance,r);
  return r;
end $$;

-- Worker calls this through its service role. The state transition is locked
-- and idempotent, so a late worker cannot spend a cancelled reservation.
create or replace function public.finish_scrape_token(p_run_id uuid,p_success boolean,p_reason text default null)
returns text language plpgsql security definer set search_path=public as $$
declare r public.token_runs%rowtype; w public.token_wallets%rowtype;
begin
  select * into r from public.token_runs where id=p_run_id for update;
  if not found then raise exception 'Run not found'; end if;
  if r.status <> 'reserved' then return r.status; end if;
  select * into w from public.token_wallets where user_id=r.user_id for update;
  update public.token_runs set status=case when p_success then 'spent' else 'released' end,
    reason=left(p_reason,500),finished_at=now() where id=p_run_id;
  update public.token_wallets set reserved=reserved-1,
    balance=balance+case when p_success then 0 else 1 end,updated_at=now()
    where user_id=r.user_id returning * into w;
  insert into public.token_ledger(user_id,event,delta,balance_after,run_id,reason)
    values(r.user_id,case when p_success then 'spend' else 'release' end,
      case when p_success then 0 else 1 end,w.balance,p_run_id,left(p_reason,500));
  return case when p_success then 'spent' else 'released' end;
end $$;

create or replace function public.cancel_scrape_token(p_run_id uuid) returns text language plpgsql security definer
set search_path=public as $$
declare r public.token_runs%rowtype; w public.token_wallets%rowtype;
begin
  select * into r from public.token_runs where id=p_run_id for update;
  if not found or r.user_id<>auth.uid() then raise exception 'Run not found'; end if;
  if r.status <> 'reserved' then return r.status; end if;
  update public.token_runs set status='released',reason='Cancelled by user',finished_at=now() where id=p_run_id;
  update public.token_wallets set reserved=reserved-1,balance=balance+1,updated_at=now()
    where user_id=r.user_id returning * into w;
  insert into public.token_ledger(user_id,event,delta,balance_after,run_id,reason)
    values(r.user_id,'release',1,w.balance,p_run_id,'Cancelled by user');
  return 'released';
end $$;

-- A killed web worker cannot run a finally block. On the next account read or
-- reservation, release that account's abandoned reservations after four hours.
create or replace function public.release_stale_scrapes() returns integer language plpgsql security definer
set search_path=public as $$
declare r public.token_runs%rowtype; w public.token_wallets%rowtype; n integer := 0; completed boolean;
begin
  if auth.uid() is null then raise exception 'Authentication required'; end if;
  for r in select * from public.token_runs where user_id=auth.uid() and status='reserved'
      and created_at < now()-interval '4 hours' for update loop
    select * into w from public.token_wallets where user_id=r.user_id for update;
    select exists(select 1 from public.projects p join public.pipeline_states s on s.project_id=p.id
      where p.id=r.project_id and p.status='complete' and s.state->'stages'->'3'->>'status'='complete') into completed;
    update public.token_runs set status=case when completed then 'spent' else 'released' end,
      reason='Interrupted run reconciled',finished_at=now() where id=r.id;
    update public.token_wallets set reserved=reserved-1,balance=balance+case when completed then 0 else 1 end,updated_at=now()
      where user_id=r.user_id returning * into w;
    insert into public.token_ledger(user_id,event,delta,balance_after,run_id,reason)
      values(r.user_id,case when completed then 'spend' else 'release' end,
        case when completed then 0 else 1 end,w.balance,r.id,'Interrupted run reconciled');
    n := n+1;
  end loop;
  return n;
end $$;

create or replace function public.request_tokens(p_amount integer,p_note text) returns uuid language plpgsql security definer
set search_path=public as $$
declare r uuid;
begin
  if auth.uid() is null or p_amount is null or p_amount not between 1 and 1000
     or p_note is null or length(trim(p_note)) not between 1 and 1000 then
    raise exception 'Invalid token request'; end if;
  if not exists(select 1 from auth.users where id=auth.uid() and email_confirmed_at is not null) then
    raise exception 'Verify your account before requesting tokens'; end if;
  insert into public.token_requests(user_id,amount,note) values(auth.uid(),p_amount,trim(p_note)) returning id into r;
  return r;
end $$;

create or replace function public.adjust_tokens(p_user_id uuid,p_delta integer,p_reason text)
returns integer language plpgsql security definer set search_path=public as $$
declare w public.token_wallets%rowtype;
begin
  if not public.is_admin() then raise exception 'Admin access required'; end if;
  if p_delta is null or p_delta=0 or abs(p_delta)>1000 or p_reason is null
     or length(trim(p_reason)) not between 1 and 500 then raise exception 'Invalid adjustment'; end if;
  insert into public.token_wallets(user_id) values(p_user_id) on conflict do nothing;
  select * into w from public.token_wallets where user_id=p_user_id for update;
  if w.balance+p_delta<0 then raise exception 'Insufficient available tokens'; end if;
  update public.token_wallets set balance=balance+p_delta,updated_at=now() where user_id=p_user_id returning * into w;
  insert into public.token_ledger(user_id,event,delta,balance_after,actor_id,reason)
    values(p_user_id,case when p_delta>0 then 'admin_grant' else 'admin_remove' end,p_delta,w.balance,auth.uid(),trim(p_reason));
  return w.balance;
end $$;

create or replace function public.review_token_request(p_request_id uuid,p_approve boolean,p_response text)
returns text language plpgsql security definer set search_path=public as $$
declare r public.token_requests%rowtype; w public.token_wallets%rowtype;
begin
  if not public.is_admin() then raise exception 'Admin access required'; end if;
  if p_response is null or length(trim(p_response)) not between 1 and 1000 then
    raise exception 'An admin response is required'; end if;
  select * into r from public.token_requests where id=p_request_id for update;
  if not found or r.status<>'pending' then raise exception 'Request already reviewed or missing'; end if;
  update public.token_requests set status=case when p_approve then 'approved' else 'rejected' end,
    admin_response=left(trim(p_response),1000),reviewed_by=auth.uid(),reviewed_at=now() where id=p_request_id;
  if p_approve then
    insert into public.token_wallets(user_id) values(r.user_id) on conflict do nothing;
    select * into w from public.token_wallets where user_id=r.user_id for update;
    update public.token_wallets set balance=balance+r.amount,updated_at=now() where user_id=r.user_id returning * into w;
    insert into public.token_ledger(user_id,event,delta,balance_after,request_id,actor_id,reason)
      values(r.user_id,'request_grant',r.amount,w.balance,p_request_id,auth.uid(),left(trim(p_response),500));
  end if;
  return case when p_approve then 'approved' else 'rejected' end;
end $$;

revoke all on function public.reserve_scrape_token(text),public.finish_scrape_token(uuid,boolean,text),
  public.cancel_scrape_token(uuid),public.request_tokens(integer,text),public.adjust_tokens(uuid,integer,text),
  public.review_token_request(uuid,boolean,text),public.release_stale_scrapes() from public;
grant execute on function public.reserve_scrape_token(text),public.cancel_scrape_token(uuid),
  public.request_tokens(integer,text),public.adjust_tokens(uuid,integer,text),
  public.review_token_request(uuid,boolean,text),public.release_stale_scrapes() to authenticated;
grant execute on function public.finish_scrape_token(uuid,boolean,text) to service_role;
