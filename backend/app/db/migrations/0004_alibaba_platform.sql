-- ============================================================================
-- 0004 -- Alibaba as a second e-commerce platform
--
-- Run AFTER 0001, 0002 and 0003.
--
-- Apply by pasting into the Supabase SQL editor and running, or:
--     supabase db execute --file backend/app/db/migrations/0004_alibaba_platform.sql
--
-- Safe to re-run: columns and tables are added `if not exists`, and every
-- constraint and policy is dropped before it is recreated.
--
-- NON-DESTRUCTIVE. Adds columns and tables, widens two numeric columns, and
-- extends two allowed-value lists. No existing row is rewritten, nothing is
-- dropped, and Daraz data keeps working exactly as before.
--
-- What it changes:
--   1. 'alibaba' becomes an allowed value for projects.ecommerce_platform and
--      ecommerce_products.platform.
--   2. ecommerce_products.price / original_price widen from numeric(12,2) to
--      numeric(14,4): Alibaba quotes unit prices below one cent (US$0.0035),
--      which two decimal places would round away. Widening loses nothing.
--   3. ecommerce_products gains four nullable B2B order-term columns:
--      max_price, moq, moq_unit, lead_time_days. Daraz rows leave them null.
--   4. New table ecommerce_product_price_tiers: one row per quantity price
--      break ("100-499 pieces: US$0.77").
--   5. New table ecommerce_product_suppliers: one row per listing, holding the
--      supplier's public trust credentials. No contact details are stored.
--
-- Scraper output is still kept whole in ecommerce_products.raw_metadata, which
-- is what the comparison engine reads; these columns and tables are the
-- structured, queryable copy.
-- ============================================================================


-- ------------------------------------- 1. allow 'alibaba' as a platform ------
-- The original lists were written inline, so Postgres named them. Rather than
-- guess those names, drop the check constraints whose definition lists 'daraz'
-- (only the platform lists do) and add them back with fixed names.

do $$
declare
    constraint_row record;
begin
    for constraint_row in
        select conrelid::regclass as table_name, conname
        from pg_constraint
        where conrelid in ('public.projects'::regclass, 'public.ecommerce_products'::regclass)
          and contype = 'c'
          and pg_get_constraintdef(oid) ilike '%''daraz''%'
    loop
        execute format('alter table %s drop constraint %I', constraint_row.table_name, constraint_row.conname);
    end loop;
end $$;

alter table public.projects
    add constraint projects_ecommerce_platform_check
    check (ecommerce_platform is null or ecommerce_platform in ('daraz', 'alibaba'));

alter table public.ecommerce_products
    add constraint ecommerce_products_platform_check
    check (platform in ('daraz', 'alibaba'));


-- ------------------------------------------ 2. sub-cent unit prices ---------

alter table public.ecommerce_products
    alter column price type numeric(14, 4);
alter table public.ecommerce_products
    alter column original_price type numeric(14, 4);


-- ------------------------------------------ 3. B2B order-term columns -------

alter table public.ecommerce_products
    add column if not exists max_price numeric(14, 4);
alter table public.ecommerce_products
    add column if not exists moq integer;
alter table public.ecommerce_products
    add column if not exists moq_unit text;
alter table public.ecommerce_products
    add column if not exists lead_time_days smallint;

alter table public.ecommerce_products
    drop constraint if exists ecommerce_products_order_terms_check;
alter table public.ecommerce_products
    add constraint ecommerce_products_order_terms_check
    check (
        (max_price is null or max_price >= 0)
        and (moq is null or moq >= 1)
        and (lead_time_days is null or lead_time_days >= 0)
    );


-- ------------------------------------------ 4. quantity price breaks --------

create table if not exists public.ecommerce_product_price_tiers (
    id            text primary key,
    -- Re-scraping replaces the listing; the cascade takes its old tiers.
    product_id    text not null references public.ecommerce_products (id) on delete cascade,
    -- Denormalised so RLS checks ownership with the usual one join.
    project_id    text not null references public.projects (id) on delete cascade,
    -- 1-based, lowest quantity first.
    position      smallint not null check (position >= 1),
    min_quantity  integer not null check (min_quantity >= 1),
    -- Null for the open-ended top tier ("1000+").
    max_quantity  integer,
    price         numeric(14, 4) not null check (price >= 0),
    currency      text not null,
    unit          text,
    created_at    timestamptz not null default now(),
    constraint ecommerce_product_price_tiers_position_unique unique (product_id, position),
    constraint ecommerce_product_price_tiers_range_check
        check (max_quantity is null or max_quantity >= min_quantity)
);

create index if not exists ecommerce_product_price_tiers_project_idx
    on public.ecommerce_product_price_tiers (project_id, product_id, position);


-- ------------------------------------------ 5. supplier trust profiles ------

create table if not exists public.ecommerce_product_suppliers (
    id                    text primary key,
    -- One profile per listing: the business that sells this product.
    product_id            text not null unique references public.ecommerce_products (id) on delete cascade,
    project_id            text not null references public.projects (id) on delete cascade,
    name                  text not null,
    country_code          text,
    country_name          text,
    years_on_platform     smallint check (years_on_platform is null or years_on_platform >= 0),
    gold_supplier         boolean not null default false,
    verified              boolean not null default false,
    trade_assurance       boolean not null default false,
    transaction_level     smallint check (transaction_level is null or transaction_level >= 0),
    -- Percentage of inquiries answered, 0-100.
    response_rate         numeric(5, 2) check (response_rate is null or response_rate between 0 and 100),
    historic_order_count  integer check (historic_order_count is null or historic_order_count >= 0),
    -- As the platform words it, e.g. "$70,000+".
    historic_gmv_label    text,
    main_products         text,
    created_at            timestamptz not null default now()
);

create index if not exists ecommerce_product_suppliers_project_idx
    on public.ecommerce_product_suppliers (project_id);


-- ----------------------------------------------------------------- RLS ------

alter table public.ecommerce_product_price_tiers enable row level security;
alter table public.ecommerce_product_suppliers  enable row level security;

drop policy if exists ecommerce_product_price_tiers_owner_all on public.ecommerce_product_price_tiers;
create policy ecommerce_product_price_tiers_owner_all on public.ecommerce_product_price_tiers
    for all using (exists (
        select 1 from public.projects p
        where p.id = ecommerce_product_price_tiers.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = ecommerce_product_price_tiers.project_id and p.owner_id = auth.uid()));

drop policy if exists ecommerce_product_suppliers_owner_all on public.ecommerce_product_suppliers;
create policy ecommerce_product_suppliers_owner_all on public.ecommerce_product_suppliers
    for all using (exists (
        select 1 from public.projects p
        where p.id = ecommerce_product_suppliers.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = ecommerce_product_suppliers.project_id and p.owner_id = auth.uid()));
