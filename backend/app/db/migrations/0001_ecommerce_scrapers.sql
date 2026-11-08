-- ============================================================================
-- 0001 -- E-commerce product comparisons (Daraz scraper integration)
--
-- Adds the third comparison type alongside website and social, and the table
-- that holds the listings the scrapers return.
--
-- Apply by pasting into the Supabase SQL editor and running, or:
--     supabase db execute --file backend/app/db/migrations/0001_ecommerce_scrapers.sql
--
-- Safe to re-run. Every create is `if not exists`, every column add is
-- `if not exists`, every constraint is dropped before being recreated and
-- every policy is dropped before being recreated.
--
-- NON-DESTRUCTIVE. It adds columns, one table and one constraint value.
-- No existing row is rewritten and no column is dropped or retyped; existing
-- projects get comparison_type 'website', which is what they already are.
--
-- Follows the same two rules as schema.sql: everything reaches auth.uid(), and
-- children cascade from projects.
-- ============================================================================

-- ------------------------------------------------------- 1. projects --------
-- What the user is comparing themselves against. Defaulted rather than
-- nullable so no code path has to treat "unset" as a third state.

alter table public.projects
    add column if not exists comparison_type text not null default 'website';

-- The marketplace, when comparison_type is 'ecommerce_product'. Null otherwise.
-- Adding a platform means extending this check list in a later migration and
-- registering the scraper in backend/app/scrapers/registry.py.
alter table public.projects
    add column if not exists ecommerce_platform text;

alter table public.projects
    drop constraint if exists projects_comparison_type_check;
alter table public.projects
    add constraint projects_comparison_type_check
    check (comparison_type in ('website', 'social_media', 'ecommerce_product'));

alter table public.projects
    drop constraint if exists projects_ecommerce_platform_check;
alter table public.projects
    add constraint projects_ecommerce_platform_check
    check (ecommerce_platform is null or ecommerce_platform in ('daraz'));

-- A platform only means something for an e-commerce comparison, and an
-- e-commerce comparison is meaningless without one. Enforced here so the rule
-- cannot be bypassed by anything that writes around the API.
alter table public.projects
    drop constraint if exists projects_platform_matches_type_check;
alter table public.projects
    add constraint projects_platform_matches_type_check
    check (
        (comparison_type = 'ecommerce_product' and ecommerce_platform is not null)
        or (comparison_type <> 'ecommerce_product' and ecommerce_platform is null)
    );

-- ------------------------------------------------- 2. scraped_sources -------
-- A scraped listing appears in the sources list like any other artefact, so
-- the existing kind check needs one more value.

alter table public.scraped_sources
    drop constraint if exists scraped_sources_kind_check;
alter table public.scraped_sources
    add constraint scraped_sources_kind_check
    check (kind in (
        'landing_page', 'social_post', 'review', 'forum_thread', 'news_article',
        'ecommerce_product'));

-- --------------------------------------------- 3. ecommerce_products --------
-- One row per scraped listing.
--
-- Deliberately NOT named daraz_products: the columns below are the fields
-- every marketplace has, so a second platform reuses this table and is told
-- apart by `platform`. Anything platform-specific lives in raw_metadata, which
-- is what the comparison engine reads.

create table if not exists public.ecommerce_products (
    id            text primary key,
    project_id    text not null references public.projects (id) on delete cascade,
    -- Null for the user's own listing, set for a competitor's.
    competitor_id text references public.competitors (id) on delete set null,
    -- The scraped_sources row this listing produced. Gap evidence cites it, so
    -- a citation resolves to a row the sources screen already shows.
    source_id     text references public.scraped_sources (id) on delete set null,
    platform      text not null check (platform in ('daraz')),
    role          text not null check (role in ('own', 'competitor')),
    url           text not null,
    product_name  text not null,

    -- --- fields every marketplace has, promoted to real columns so they can
    -- --- be filtered and sorted in SQL rather than dug out of jsonb ---------
    brand                      text,
    price                      numeric(12, 2),
    original_price             numeric(12, 2),
    discount_percent           numeric(6, 2),
    currency                   text not null default 'PKR',
    rating                     numeric(3, 2) check (rating is null or (rating >= 0 and rating <= 5)),
    review_count               integer not null default 0,
    image_count                integer not null default 0,
    seller_name                text,
    seller_rating              numeric(3, 2),
    stock_status               text,
    category                   text,
    content_completeness_score numeric(5, 2),

    -- --- everything else ----------------------------------------------------
    -- Chunkable content keyed by field type (title, description, specs,
    -- review, promo_tags, policy_text, category). Kept on the row so a
    -- re-embed never needs a re-scrape.
    text_fields   jsonb not null default '{}'::jsonb,
    -- The complete scraper output, including the ~40 fields with no column.
    raw_metadata  jsonb not null default '{}'::jsonb,

    scrape_method text not null default 'unknown'
                  check (scrape_method in ('bs4', 'playwright', 'bs4+playwright', 'unknown')),
    warnings      jsonb not null default '[]'::jsonb,
    chunk_count   integer not null default 0,
    scraped_at    timestamptz not null default now()
);

-- A project has exactly one listing of its own; competitors are one per
-- competitor row. This is what stops a re-run leaving two baselines behind.
create unique index if not exists ecommerce_products_own_idx
    on public.ecommerce_products (project_id)
    where role = 'own';

create index if not exists ecommerce_products_project_idx
    on public.ecommerce_products (project_id, role);
create index if not exists ecommerce_products_competitor_idx
    on public.ecommerce_products (competitor_id);
create index if not exists ecommerce_products_source_idx
    on public.ecommerce_products (source_id);

-- ----------------------------------------------------------- 4. RLS ---------

alter table public.ecommerce_products enable row level security;

drop policy if exists ecommerce_products_owner_all on public.ecommerce_products;
create policy ecommerce_products_owner_all on public.ecommerce_products
    for all using (exists (
        select 1 from public.projects p
        where p.id = ecommerce_products.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = ecommerce_products.project_id and p.owner_id = auth.uid()));
