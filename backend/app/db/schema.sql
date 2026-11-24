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
    ecommerce_platform text,
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
    constraint projects_ecommerce_platform_check check (
        ecommerce_platform is null or ecommerce_platform in ('daraz', 'alibaba')),
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
    platform      text not null,
    role          text not null check (role in ('own','competitor')),
    url           text not null,
    product_name  text not null,

    -- fields every marketplace has, promoted to columns so they can be
    -- filtered and sorted in SQL rather than dug out of jsonb
    brand                      text,
    -- numeric(14,4): Alibaba quotes sub-cent unit prices (migration 0004).
    price                      numeric(14,4),
    original_price             numeric(14,4),
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
    scraped_at    timestamptz not null default now(),

    -- B2B order terms, for platforms that publish them (Alibaba; migration
    -- 0004). Null for Daraz. `price` is the lowest tier, max_price the highest.
    max_price       numeric(14,4),
    moq             integer,
    moq_unit        text,
    lead_time_days  smallint,

    constraint ecommerce_products_platform_check check (platform in ('daraz', 'alibaba')),
    constraint ecommerce_products_order_terms_check check (
        (max_price is null or max_price >= 0)
        and (moq is null or moq >= 1)
        and (lead_time_days is null or lead_time_days >= 0))
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

-- Quantity price breaks (Alibaba), lowest quantity first. (Migration 0004.)
create table if not exists public.ecommerce_product_price_tiers (
    id            text primary key,
    product_id    text not null references public.ecommerce_products (id) on delete cascade,
    project_id    text not null references public.projects (id) on delete cascade,
    position      smallint not null check (position >= 1),
    min_quantity  integer not null check (min_quantity >= 1),
    -- Null for the open-ended top tier ("1000+").
    max_quantity  integer,
    price         numeric(14,4) not null check (price >= 0),
    currency      text not null,
    unit          text,
    created_at    timestamptz not null default now(),
    constraint ecommerce_product_price_tiers_position_unique unique (product_id, position),
    constraint ecommerce_product_price_tiers_range_check
        check (max_quantity is null or max_quantity >= min_quantity)
);

create index if not exists ecommerce_product_price_tiers_project_idx
    on public.ecommerce_product_price_tiers (project_id, product_id, position);

-- The supplier's public trust credentials (Alibaba), one per listing. No
-- contact details. (Migration 0004.)
create table if not exists public.ecommerce_product_suppliers (
    id                    text primary key,
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
    response_rate         numeric(5,2) check (response_rate is null or response_rate between 0 and 100),
    historic_order_count  integer check (historic_order_count is null or historic_order_count >= 0),
    historic_gmv_label    text,
    main_products         text,
    created_at            timestamptz not null default now()
);

create index if not exists ecommerce_product_suppliers_project_idx
    on public.ecommerce_product_suppliers (project_id);

-- ------------------------------------------------- stage 4/5: gaps ---------

-- ------------------------------- stage 2: crawled pages and social posts ---

-- The structured copy of what the website and Instagram scrapers read.
--
-- Each page or post already has a generic `scraped_sources` row, which is what
-- the sources screen lists and what a gap's evidence cites. These tables hold
-- what that row cannot: a page's headings and links, a post's hashtags, likes
-- and comments. Same split as `scraped_sources` and `ecommerce_products`.
-- (Migration 0005.)
create table if not exists public.website_pages (
    id              text primary key,
    project_id      text not null references public.projects (id) on delete cascade,
    source_id       text references public.scraped_sources (id) on delete set null,
    competitor_id   text references public.competitors (id) on delete set null,
    role            text not null check (role in ('own', 'competitor')),
    submitted_url   text not null,
    page_url        text not null,
    canonical_url   text,
    status_code     integer,
    title           text,
    meta_description text,
    headings        jsonb not null default '[]'::jsonb,
    links           jsonb not null default '[]'::jsonb,
    heading_count   integer not null default 0,
    link_count      integer not null default 0,
    -- Kept on the row as well as in Chroma, so a re-embed needs no re-crawl.
    cleaned_text    text not null default '',
    word_count      integer not null default 0,
    content_hash    text,
    renderer        text not null default 'http' check (renderer in ('http', 'playwright')),
    -- Clicks from the submitted link; 0 is the page the user gave us.
    depth           smallint not null default 0,
    is_root         boolean not null default false,
    text_fields     jsonb not null default '{}'::jsonb,
    -- The checkable facts the A-F comparison parameters are derived from:
    -- viewport, heading hierarchy, alt coverage, CTAs, forms, legal links,
    -- third-party scripts, and (on the root page) robots.txt and sitemap.
    -- Facts only; the scoring lives in app/scrapers/website/metrics.py.
    -- (Migration 0007.)
    signals         jsonb not null default '{}'::jsonb,
    scraped_at      timestamptz not null default now(),
    constraint website_pages_page_unique unique (project_id, page_url)
);

create index if not exists website_pages_project_idx
    on public.website_pages (project_id, role, depth);

-- A page's own marketing images, most representative first. Same shape and
-- same rule as ecommerce_product_images: the site's URL is stored, nothing is
-- downloaded or re-hosted. (Migration 0009.)
create table if not exists public.website_page_images (
    id          text primary key,
    -- Re-crawling replaces the page, and the cascade takes its images.
    page_id     text not null references public.website_pages (id) on delete cascade,
    -- Denormalised so RLS checks ownership with the usual one join.
    project_id  text not null references public.projects (id) on delete cascade,
    -- 1-based. Position 1 is the page's most representative image.
    position    smallint not null check (position >= 1),
    image_url   text not null,
    alt_text    text,
    -- Where on the page it was found, most deliberate first.
    source      text not null default 'content' check (source in (
                    'og_image','hero','content')),
    -- As declared in the markup, when it is declared at all.
    width       integer,
    height      integer,
    is_primary  boolean not null default false,
    created_at  timestamptz not null default now(),
    constraint website_page_images_position_unique unique (page_id, position),
    constraint website_page_images_primary_is_first check (is_primary = (position = 1))
);

create index if not exists website_page_images_project_idx
    on public.website_page_images (project_id, page_id, position);

create table if not exists public.instagram_posts (
    id              text primary key,
    project_id      text not null references public.projects (id) on delete cascade,
    source_id       text references public.scraped_sources (id) on delete set null,
    competitor_id   text references public.competitors (id) on delete set null,
    role            text not null check (role in ('own', 'competitor')),
    submitted_url   text not null,
    profile_url     text,
    post_url        text,
    -- The scraped profile's own handle, from the profile item the actor
    -- returned. What the screen labels this side with. (Migration 0008.)
    profile_username text,
    -- Followers, following, posts, bio, website, highlights, verified and
    -- category of the scraped profile, for the engagement model. (Migration 0010.)
    profile_stats   jsonb not null default '{}'::jsonb,
    -- Who wrote this particular post: the profile owner, except on a
    -- collaboration post, where it is the other collaborator.
    owner_username  text,
    caption         text not null default '',
    caption_length  integer not null default 0,
    caption_word_count integer not null default 0,
    hashtags        jsonb not null default '[]'::jsonb,
    hashtag_count   integer not null default 0,
    like_count      integer,
    comment_count   integer,
    engagement_count integer not null default 0,
    video_view_count integer,
    media_type      text,
    media_url       text,
    media_count     integer not null default 0,
    location_name   text,
    is_sponsored    boolean not null default false,
    posted_at       timestamptz,
    collected_comment_count integer not null default 0,
    text_fields     jsonb not null default '{}'::jsonb,
    scraped_at      timestamptz not null default now(),
    -- One copy per side: a collaboration post appears on every collaborator's
    -- profile under the same URL, so the same post can legitimately belong to
    -- both sides of a comparison. (Widened by migration 0006.)
    constraint instagram_posts_post_unique unique (project_id, role, post_url)
);

create index if not exists instagram_posts_project_idx
    on public.instagram_posts (project_id, role, posted_at desc);

create table if not exists public.instagram_post_media (
    id          text primary key,
    post_id     text not null references public.instagram_posts (id) on delete cascade,
    project_id  text not null references public.projects (id) on delete cascade,
    position    smallint not null check (position >= 1),
    media_type  text,
    -- Instagram's own CDN URL. Nothing is downloaded or re-hosted.
    media_url   text not null,
    -- The still picture; for a video, its cover frame (migration 0013).
    thumbnail_url text,
    created_at  timestamptz not null default now(),
    constraint instagram_post_media_position_unique unique (post_id, position)
);

create index if not exists instagram_post_media_project_idx
    on public.instagram_post_media (project_id, post_id, position);

create table if not exists public.instagram_post_comments (
    id                 text primary key,
    post_id            text not null references public.instagram_posts (id) on delete cascade,
    project_id         text not null references public.projects (id) on delete cascade,
    position           smallint not null check (position >= 1),
    -- Public commenter handle only: no contact details, nothing that needed a
    -- login to see.
    commenter_username text,
    comment_text       text not null default '',
    like_count         integer,
    posted_at          timestamptz,
    created_at         timestamptz not null default now(),
    constraint instagram_post_comments_position_unique unique (post_id, position)
);

create index if not exists instagram_post_comments_project_idx
    on public.instagram_post_comments (project_id, post_id, position);

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
    -- Plain-language extras: how sure, example posts, numbers, technical notes. (Migration 0012.)
    details       jsonb not null default '{}'::jsonb,
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
alter table public.ecommerce_product_price_tiers enable row level security;
alter table public.ecommerce_product_suppliers enable row level security;
alter table public.website_pages enable row level security;
alter table public.website_page_images enable row level security;
alter table public.instagram_posts enable row level security;
alter table public.instagram_post_media enable row level security;
alter table public.instagram_post_comments enable row level security;
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

drop policy if exists website_page_images_owner_all on public.website_page_images;
create policy website_page_images_owner_all on public.website_page_images
    for all using (exists (
        select 1 from public.projects p
        where p.id = website_page_images.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = website_page_images.project_id and p.owner_id = auth.uid()));

drop policy if exists website_pages_owner_all on public.website_pages;
create policy website_pages_owner_all on public.website_pages
    for all using (exists (
        select 1 from public.projects p
        where p.id = website_pages.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = website_pages.project_id and p.owner_id = auth.uid()));

drop policy if exists instagram_posts_owner_all on public.instagram_posts;
create policy instagram_posts_owner_all on public.instagram_posts
    for all using (exists (
        select 1 from public.projects p
        where p.id = instagram_posts.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = instagram_posts.project_id and p.owner_id = auth.uid()));

drop policy if exists instagram_post_media_owner_all on public.instagram_post_media;
create policy instagram_post_media_owner_all on public.instagram_post_media
    for all using (exists (
        select 1 from public.projects p
        where p.id = instagram_post_media.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = instagram_post_media.project_id and p.owner_id = auth.uid()));

drop policy if exists instagram_post_comments_owner_all on public.instagram_post_comments;
create policy instagram_post_comments_owner_all on public.instagram_post_comments
    for all using (exists (
        select 1 from public.projects p
        where p.id = instagram_post_comments.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = instagram_post_comments.project_id and p.owner_id = auth.uid()));

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

-- ============================================================================
-- Admin access and scrape tokens (migration 0015)
-- ============================================================================

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

-- Admin mail drafts are held until the GCP delivery worker is integrated.
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
