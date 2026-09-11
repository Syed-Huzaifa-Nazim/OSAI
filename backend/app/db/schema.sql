-- ============================================================================
-- OptiStratixAI -- Supabase Postgres schema
--
-- Apply with:  supabase db execute --file backend/app/db/schema.sql
--        or:   paste into the Supabase SQL editor and run.
--
-- Two rules hold throughout:
--   1. Every table that holds user data carries a path back to auth.uid(), and
--      row-level security is what enforces ownership, not application code.
--   2. Child rows cascade from projects, so deleting a project genuinely
--      removes everything the run produced.
--
-- Documented in docs/database.md.
-- ============================================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------- projects --

create table if not exists public.projects (
    id                text primary key,
    owner_id          uuid not null references auth.users (id) on delete cascade,
    brand_name        text not null check (char_length(brand_name) between 2 and 120),
    -- The user's own link: a website, a social page or a product listing.
    -- Deliberately text with no length cap: marketplace links copied from
    -- search results carry over a kilobyte of tracking parameters.
    brand_website     text,
    brand_description text not null,
    industry          text not null check (industry in (
                          'saas','ecommerce','fintech','healthcare','education',
                          'hospitality','agency','manufacturing','other')),
    -- Optional since migration 0002.
    target_audience   text,
    objectives        jsonb not null default '[]'::jsonb,
    -- What the user is comparing themselves against. Stage 2 branches on this
    -- to pick a data-acquisition strategy.
    comparison_type   text not null default 'website' check (comparison_type in (
                          'website','social_media','ecommerce_product')),
    -- The marketplace, when comparison_type is 'ecommerce_product'. Null
    -- otherwise, and required when it is -- see the constraint below.
    ecommerce_platform text check (ecommerce_platform is null or ecommerce_platform in ('daraz')),
    -- The social platform, when comparison_type is 'social_media'. Null
    -- otherwise, and required when it is.
    social_platform   text,
    status            text not null default 'draft' check (status in (
                          'draft','running','awaiting_review','complete','failed','archived')),
    current_stage     smallint not null default 1 check (current_stage between 1 and 9),
    competitor_count  smallint not null default 0,
    gap_count         smallint not null default 0,
    is_demo           boolean not null default false,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now(),
    -- A platform only means something for an e-commerce comparison, and an
    -- e-commerce comparison is meaningless without one.
    constraint projects_platform_matches_type_check check (
        (comparison_type = 'ecommerce_product' and ecommerce_platform is not null)
        or (comparison_type <> 'ecommerce_product' and ecommerce_platform is null)),
    -- Required, up to 120 characters (no minimum since migration 0002).
    constraint projects_brand_description_check check (
        char_length(brand_description) between 1 and 120),
    constraint projects_target_audience_check check (
        target_audience is null or char_length(target_audience) <= 120),
    constraint projects_social_platform_check check (
        social_platform is null or social_platform in ('facebook', 'instagram')),
    constraint projects_social_platform_matches_type_check check (
        (comparison_type = 'social_media' and social_platform is not null)
        or (comparison_type <> 'social_media' and social_platform is null))
);

create index if not exists projects_owner_idx on public.projects (owner_id, updated_at desc);

-- ------------------------------------------------------------- competitors --

create table if not exists public.competitors (
    id                text primary key,
    project_id        text not null references public.projects (id) on delete cascade,
    name              text not null,
    landing_page_url  text not null,
    social_handles    jsonb not null default '[]'::jsonb,
    notes             text,
    created_at        timestamptz not null default now()
);

create index if not exists competitors_project_idx on public.competitors (project_id);

-- -------------------------------------------------- stage 2/3: sources -----

create table if not exists public.scraped_sources (
    id            text primary key,
    project_id    text not null references public.projects (id) on delete cascade,
    competitor_id text references public.competitors (id) on delete set null,
    kind          text not null check (kind in (
                      'landing_page','social_post','review','forum_thread','news_article',
                      'ecommerce_product')),
    url           text not null,
    title         text not null,
    excerpt       text not null default '',
    status        text not null default 'pending' check (status in (
                      'pending','scraped','embedded','failed')),
    chunk_count   integer not null default 0,
    scraped_at    timestamptz not null default now()
);

create index if not exists sources_project_idx on public.scraped_sources (project_id);

-- ------------------------------------------- stage 2: scraped listings -----

-- One row per scraped marketplace listing.
--
-- Deliberately not named daraz_products: the columns here are the fields every
-- marketplace has, so a second platform reuses this table and is told apart by
-- `platform`. Anything platform-specific lives in raw_metadata, which is what
-- the comparison engine in app/scrapers/<platform>/metrics.py reads.
create table if not exists public.ecommerce_products (
    id            text primary key,
    project_id    text not null references public.projects (id) on delete cascade,
    -- Null for the user's own listing, set for a competitor's.
    competitor_id text references public.competitors (id) on delete set null,
    -- The scraped_sources row this listing produced, so gap evidence cites a
    -- row the sources screen already shows.
    source_id     text references public.scraped_sources (id) on delete set null,
    platform      text not null check (platform in ('daraz')),
    role          text not null check (role in ('own','competitor')),
    url           text not null,
    product_name  text not null,

    -- fields every marketplace has, promoted to columns so they can be
    -- filtered and sorted in SQL rather than dug out of jsonb
    brand                      text,
    price                      numeric(12,2),
    original_price             numeric(12,2),
    discount_percent           numeric(6,2),
    currency                   text not null default 'PKR',
    rating                     numeric(3,2) check (rating is null or (rating >= 0 and rating <= 5)),
    review_count               integer not null default 0,
    image_count                integer not null default 0,
    seller_name                text,
    seller_rating              numeric(3,2),
    stock_status               text,
    category                   text,
    content_completeness_score numeric(5,2),

    -- Chunkable content keyed by field type. Kept on the row so a re-embed
    -- never needs a re-scrape.
    text_fields   jsonb not null default '{}'::jsonb,
    -- The complete scraper output, including fields with no column.
    raw_metadata  jsonb not null default '{}'::jsonb,

    scrape_method text not null default 'unknown' check (scrape_method in (
                      'bs4','playwright','bs4+playwright','unknown')),
    warnings      jsonb not null default '[]'::jsonb,
    chunk_count   integer not null default 0,
    scraped_at    timestamptz not null default now()
);

-- A project has exactly one listing of its own. This is what stops a re-run
-- leaving two baselines behind.
create unique index if not exists ecommerce_products_own_idx
    on public.ecommerce_products (project_id) where role = 'own';
create index if not exists ecommerce_products_project_idx
    on public.ecommerce_products (project_id, role);
create index if not exists ecommerce_products_competitor_idx
    on public.ecommerce_products (competitor_id);
create index if not exists ecommerce_products_source_idx
    on public.ecommerce_products (source_id);

-- One row per product photo, main image first. Only the platform's own image
-- URLs are stored; nothing is downloaded or re-hosted. (Migration 0003.)
create table if not exists public.ecommerce_product_images (
    id          text primary key,
    -- Re-scraping replaces the listing; the cascade takes its old photos.
    product_id  text not null references public.ecommerce_products (id) on delete cascade,
    -- Denormalised so RLS checks ownership with the usual one join.
    project_id  text not null references public.projects (id) on delete cascade,
    -- 1-based gallery order. Position 1 is the main image.
    position    smallint not null check (position >= 1),
    url         text not null,
    is_primary  boolean not null default false,
    source      text not null default 'gallery' check (source in (
                    'gallery','structured_data','page','og_image')),
    created_at  timestamptz not null default now(),
    constraint ecommerce_product_images_position_unique unique (product_id, position),
    constraint ecommerce_product_images_primary_is_first check (is_primary = (position = 1))
);

create index if not exists ecommerce_product_images_project_idx
    on public.ecommerce_product_images (project_id, product_id, position);

-- ------------------------------------------------- stage 4/5: gaps ---------

create table if not exists public.gaps_opportunities (
    id            text primary key,
    project_id    text not null references public.projects (id) on delete cascade,
    title         text not null,
    description   text not null,
    category      text not null check (category in (
                      'content','seo','social_engagement','positioning',
                      'audience','conversion','pricing')),
    priority      text not null check (priority in ('critical','high','medium','low')),
    -- Set by the human at HITL #1; overrides the agent's own call.
    user_priority text check (user_priority in ('critical','high','medium','low')),
    confidence    numeric(4,3) not null check (confidence between 0 and 1),
    -- Each entry: {source_id, source_url, source_title, quote, relevance}.
    -- No agent claim ships without at least one.
    evidence      jsonb not null default '[]'::jsonb,
    opportunity   text not null,
    decision      text not null default 'pending' check (decision in (
                      'pending','accepted','rejected')),
    reviewer_note text,
    created_at    timestamptz not null default now()
);

create index if not exists gaps_project_idx on public.gaps_opportunities (project_id);
create index if not exists gaps_decision_idx on public.gaps_opportunities (project_id, decision);

-- ------------------------------------- stage 6: strategy + critic ----------

create table if not exists public.strategies (
    id                 text primary key,
    project_id         text not null references public.projects (id) on delete cascade,
    version            integer not null default 1,
    title              text not null,
    executive_summary  text not null,
    status             text not null default 'draft' check (status in (
                           'generating','draft','critiqued','awaiting_approval',
                           'approved','revision_requested')),
    initiatives        jsonb not null default '[]'::jsonb,
    -- The Critic's interventions, each keeping `before` and `after`. This is
    -- what the transparency panel renders; dropping it would make the
    -- product's central claim unverifiable.
    critic_feedback    jsonb not null default '[]'::jsonb,
    addressed_gap_ids  jsonb not null default '[]'::jsonb,
    generated_at       timestamptz not null default now(),
    approved_at        timestamptz,
    unique (project_id, version)
);

create index if not exists strategies_project_idx on public.strategies (project_id, version desc);

-- Kept as a separate table as well as inline JSON, so critic activity can be
-- queried across projects for the evaluation chapter of the report.
create table if not exists public.critic_feedback (
    id                   text primary key,
    strategy_id          text not null references public.strategies (id) on delete cascade,
    target_initiative_id text,
    verdict              text not null check (verdict in (
                             'strengthened','challenged','rejected','approved')),
    dimension            text not null check (dimension in (
                             'strength','clarity','feasibility','evidence')),
    comment              text not null,
    before_text          text,
    after_text           text,
    severity             text not null default 'info' check (severity in ('info','minor','major')),
    created_at           timestamptz not null default now()
);

create index if not exists critic_strategy_idx on public.critic_feedback (strategy_id);

-- --------------------------------------- HITL audit trail (stages 5 & 7) ---

create table if not exists public.hitl_reviews (
    id            text primary key,
    project_id    text not null references public.projects (id) on delete cascade,
    -- 5 = gap refinement, 7 = final strategy approval.
    stage         smallint not null check (stage in (5, 7)),
    reviewer_id   uuid not null references auth.users (id) on delete cascade,
    reviewer_name text not null default '',
    decision      text not null check (decision in (
                      'approved','rejected','revision_requested')),
    notes         text,
    affected_ids  jsonb not null default '[]'::jsonb,
    created_at    timestamptz not null default now()
);

create index if not exists reviews_project_idx on public.hitl_reviews (project_id, created_at);

-- ------------------------------------------------ stage 8: documents ------

create table if not exists public.strategy_documents (
    id                text primary key,
    project_id        text not null references public.projects (id) on delete cascade,
    strategy_id       text not null references public.strategies (id) on delete cascade,
    title             text not null,
    content           text not null default '',
    sections          jsonb not null default '[]'::jsonb,
    available_formats jsonb not null default '["markdown"]'::jsonb,
    word_count        integer not null default 0,
    generated_at      timestamptz not null default now()
);

create index if not exists documents_project_idx on public.strategy_documents (project_id);

-- ---------------------------------------------- stage 9: content assets ----

create table if not exists public.content_suggestions (
    id                     text primary key,
    project_id             text not null references public.projects (id) on delete cascade,
    kind                   text not null check (kind in (
                               'blog','social_post','ad_copy','seo_brief','email')),
    title                  text not null,
    angle                  text not null,
    linked_initiative_id   text,
    target_keywords        jsonb not null default '[]'::jsonb,
    channel                text not null default '',
    estimated_effort_hours smallint not null default 0,
    status                 text not null default 'suggested' check (status in (
                               'suggested','queued','generated','dismissed')),
    body                   text,
    created_at             timestamptz not null default now()
);

create index if not exists suggestions_project_idx on public.content_suggestions (project_id);

-- ------------------------------------------------- pipeline run state ------

-- One row per project. The whole nine-stage state is stored as a JSON document
-- because it is always read and written as a unit, and the shape has to stay in
-- lockstep with the frontend's PipelineState type.
create table if not exists public.pipeline_states (
    project_id text primary key references public.projects (id) on delete cascade,
    state      jsonb not null,
    updated_at timestamptz not null default now()
);

-- ------------------------------------------- feature integration layer -----

-- Registry of teammates' separately-built modules. `feature_key` matches the
-- key in frontend/src/features/registry.ts. See docs/architecture.md.
create table if not exists public.integrations (
    id           text primary key,
    owner_id     uuid references auth.users (id) on delete cascade,
    feature_key  text not null,
    name         text not null,
    description  text not null default '',
    status       text not null default 'available' check (status in (
                     'available','connected','coming_soon','error')),
    connected_at timestamptz,
    config       jsonb,
    created_at   timestamptz not null default now(),
    unique (owner_id, feature_key)
);

-- ---------------------------------------------------------------- contact --

-- Public form. No RLS read policy: submissions are written by anyone and read
-- only through the service role, since there is no admin UI yet.
create table if not exists public.contact_submissions (
    id           uuid primary key default gen_random_uuid(),
    name         text not null,
    email        text not null,
    organisation text,
    message      text not null,
    created_at   timestamptz not null default now()
);

-- ============================================================================
-- ROW-LEVEL SECURITY
--
-- Every policy resolves ownership through projects.owner_id = auth.uid(), so a
-- user can only ever reach their own rows. The API adds no ownership filter of
-- its own -- this is the single enforcement point.
-- ============================================================================

alter table public.projects            enable row level security;
alter table public.competitors         enable row level security;
alter table public.scraped_sources     enable row level security;
alter table public.gaps_opportunities  enable row level security;
alter table public.ecommerce_products  enable row level security;
alter table public.ecommerce_product_images enable row level security;
alter table public.strategies          enable row level security;
alter table public.critic_feedback     enable row level security;
alter table public.hitl_reviews        enable row level security;
alter table public.strategy_documents  enable row level security;
alter table public.content_suggestions enable row level security;
alter table public.pipeline_states     enable row level security;
alter table public.integrations        enable row level security;
alter table public.contact_submissions enable row level security;

-- --- projects: the root of every ownership check -----------------------------
drop policy if exists projects_owner_all on public.projects;
create policy projects_owner_all on public.projects
    for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- --- child tables: ownership via the parent project --------------------------
-- Written as a repeated pattern rather than a helper function so each policy is
-- readable on its own in the Supabase dashboard.

drop policy if exists competitors_owner_all on public.competitors;
create policy competitors_owner_all on public.competitors
    for all using (exists (
        select 1 from public.projects p
        where p.id = competitors.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = competitors.project_id and p.owner_id = auth.uid()));

drop policy if exists sources_owner_all on public.scraped_sources;
create policy sources_owner_all on public.scraped_sources
    for all using (exists (
        select 1 from public.projects p
        where p.id = scraped_sources.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = scraped_sources.project_id and p.owner_id = auth.uid()));

drop policy if exists ecommerce_products_owner_all on public.ecommerce_products;
create policy ecommerce_products_owner_all on public.ecommerce_products
    for all using (exists (
        select 1 from public.projects p
        where p.id = ecommerce_products.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = ecommerce_products.project_id and p.owner_id = auth.uid()));

drop policy if exists ecommerce_product_images_owner_all on public.ecommerce_product_images;
create policy ecommerce_product_images_owner_all on public.ecommerce_product_images
    for all using (exists (
        select 1 from public.projects p
        where p.id = ecommerce_product_images.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = ecommerce_product_images.project_id and p.owner_id = auth.uid()));

drop policy if exists gaps_owner_all on public.gaps_opportunities;
create policy gaps_owner_all on public.gaps_opportunities
    for all using (exists (
        select 1 from public.projects p
        where p.id = gaps_opportunities.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = gaps_opportunities.project_id and p.owner_id = auth.uid()));

drop policy if exists strategies_owner_all on public.strategies;
create policy strategies_owner_all on public.strategies
    for all using (exists (
        select 1 from public.projects p
        where p.id = strategies.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = strategies.project_id and p.owner_id = auth.uid()));

drop policy if exists critic_owner_all on public.critic_feedback;
create policy critic_owner_all on public.critic_feedback
    for all using (exists (
        select 1 from public.strategies s
        join public.projects p on p.id = s.project_id
        where s.id = critic_feedback.strategy_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.strategies s
        join public.projects p on p.id = s.project_id
        where s.id = critic_feedback.strategy_id and p.owner_id = auth.uid()));

drop policy if exists reviews_owner_all on public.hitl_reviews;
create policy reviews_owner_all on public.hitl_reviews
    for all using (exists (
        select 1 from public.projects p
        where p.id = hitl_reviews.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = hitl_reviews.project_id and p.owner_id = auth.uid()));

drop policy if exists documents_owner_all on public.strategy_documents;
create policy documents_owner_all on public.strategy_documents
    for all using (exists (
        select 1 from public.projects p
        where p.id = strategy_documents.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = strategy_documents.project_id and p.owner_id = auth.uid()));

drop policy if exists suggestions_owner_all on public.content_suggestions;
create policy suggestions_owner_all on public.content_suggestions
    for all using (exists (
        select 1 from public.projects p
        where p.id = content_suggestions.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = content_suggestions.project_id and p.owner_id = auth.uid()));

drop policy if exists pipeline_owner_all on public.pipeline_states;
create policy pipeline_owner_all on public.pipeline_states
    for all using (exists (
        select 1 from public.projects p
        where p.id = pipeline_states.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = pipeline_states.project_id and p.owner_id = auth.uid()));

-- --- integrations: owned directly --------------------------------------------
drop policy if exists integrations_owner_all on public.integrations;
create policy integrations_owner_all on public.integrations
    for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- --- contact: anyone may write, nobody may read ------------------------------
-- Reading is deliberately left to the service role. Without an admin UI, a read
-- policy would be a way to harvest submitted addresses.
drop policy if exists contact_insert_any on public.contact_submissions;
create policy contact_insert_any on public.contact_submissions
    for insert with check (true);

-- ============================================================================
-- updated_at maintenance
-- ============================================================================

create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists projects_touch_updated_at on public.projects;
create trigger projects_touch_updated_at
    before update on public.projects
    for each row execute function public.touch_updated_at();
