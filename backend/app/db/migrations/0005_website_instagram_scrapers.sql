-- ============================================================================
-- 0005 -- Website and Instagram scrapers
--
-- Run AFTER 0001, 0002, 0003 and 0004.
--
-- Apply by pasting into the Supabase SQL editor and running, or:
--     supabase db execute --file backend/app/db/migrations/0005_website_instagram_scrapers.sql
--
-- Safe to re-run: every table and index is created `if not exists`, and every
-- policy is dropped before it is recreated.
--
-- NON-DESTRUCTIVE. Adds four tables. No existing table, column or row changes,
-- and the e-commerce path is untouched.
--
-- What it stores, and why these tables:
--   A website comparison crawls pages; a social comparison reads posts. Both
--   already produce one `scraped_sources` row per page or post -- that is the
--   generic record the sources screen and the Insight Agent's citations use,
--   and `scraped_sources.kind` already allows 'landing_page' and 'social_post',
--   so it needs no change. What it cannot hold is the structure behind each
--   one: a page's headings and links, a post's hashtags, likes and comments.
--   These four tables are that structured copy, the same split the e-commerce
--   path uses between `scraped_sources` and `ecommerce_products`.
--
--   1. website_pages            one crawled page, cleaned and readable
--   2. instagram_posts          one public post on a scraped profile
--   3. instagram_post_media     a post's images and videos (carousels included)
--   4. instagram_post_comments  the public comments collected for a post
--
-- Text for retrieval lives in `text_fields` on the page/post row and is
-- embedded into the project's Chroma collection by stage 3, exactly as a
-- product listing's text is. No vector column is needed here.
-- ============================================================================


-- ------------------------------------------------- 1. crawled website pages --

create table if not exists public.website_pages (
    id              text primary key,
    project_id      text not null references public.projects (id) on delete cascade,
    -- The scraped_sources row this page produced, so a citation resolves to
    -- something the sources screen already lists.
    source_id       text references public.scraped_sources (id) on delete set null,
    -- Null for the user's own site, set for a competitor's.
    competitor_id   text references public.competitors (id) on delete set null,
    role            text not null check (role in ('own', 'competitor')),
    -- The link the user submitted; page_url is where this particular page was.
    submitted_url   text not null,
    page_url        text not null,
    canonical_url   text,
    status_code     integer,
    title           text,
    meta_description text,
    -- [{level, text}] in document order, and [{url, text}] as found on the page.
    headings        jsonb not null default '[]'::jsonb,
    links           jsonb not null default '[]'::jsonb,
    heading_count   integer not null default 0,
    link_count      integer not null default 0,
    -- The readable text, boilerplate removed. Kept on the row as well as in
    -- Chroma so a re-embed never needs a re-crawl.
    cleaned_text    text not null default '',
    word_count      integer not null default 0,
    content_hash    text,
    -- How the page was actually read.
    renderer        text not null default 'http' check (renderer in ('http', 'playwright')),
    -- Clicks from the submitted link; 0 is the page the user gave us.
    depth           smallint not null default 0,
    is_root         boolean not null default false,
    -- Chunkable content keyed by field type: page_text, headings, meta.
    text_fields     jsonb not null default '{}'::jsonb,
    scraped_at      timestamptz not null default now(),

    constraint website_pages_page_unique unique (project_id, page_url)
);

create index if not exists website_pages_project_idx
    on public.website_pages (project_id, role, depth);


-- ------------------------------------------------------ 2. Instagram posts --

create table if not exists public.instagram_posts (
    id              text primary key,
    project_id      text not null references public.projects (id) on delete cascade,
    source_id       text references public.scraped_sources (id) on delete set null,
    competitor_id   text references public.competitors (id) on delete set null,
    role            text not null check (role in ('own', 'competitor')),
    -- The profile link as submitted, and the profile the actor reported.
    submitted_url   text not null,
    profile_url     text,
    post_url        text,
    owner_username  text,
    caption         text not null default '',
    caption_length  integer not null default 0,
    caption_word_count integer not null default 0,
    hashtags        jsonb not null default '[]'::jsonb,
    hashtag_count   integer not null default 0,
    like_count      integer,
    comment_count   integer,
    -- likes + comments, stored so a ranking query needs no arithmetic.
    engagement_count integer not null default 0,
    video_view_count integer,
    media_type      text,
    media_url       text,
    media_count     integer not null default 0,
    location_name   text,
    is_sponsored    boolean not null default false,
    posted_at       timestamptz,
    -- How many comments were actually collected (the limit is configurable).
    collected_comment_count integer not null default 0,
    -- Chunkable content keyed by field type: caption, hashtags, comments.
    text_fields     jsonb not null default '{}'::jsonb,
    scraped_at      timestamptz not null default now(),

    constraint instagram_posts_post_unique unique (project_id, post_url)
);

create index if not exists instagram_posts_project_idx
    on public.instagram_posts (project_id, role, posted_at desc);


-- ------------------------------------------------ 3. Instagram post media --

create table if not exists public.instagram_post_media (
    id          text primary key,
    -- Re-scraping replaces the post, and the cascade takes its media with it.
    post_id     text not null references public.instagram_posts (id) on delete cascade,
    -- Denormalised so RLS checks ownership with the usual one join.
    project_id  text not null references public.projects (id) on delete cascade,
    -- 1-based. A carousel keeps its slide order.
    position    smallint not null check (position >= 1),
    media_type  text,
    -- Instagram's own CDN URL. Nothing is downloaded or re-hosted.
    media_url   text not null,
    created_at  timestamptz not null default now(),

    constraint instagram_post_media_position_unique unique (post_id, position)
);

create index if not exists instagram_post_media_project_idx
    on public.instagram_post_media (project_id, post_id, position);


-- --------------------------------------------- 4. Instagram post comments --

create table if not exists public.instagram_post_comments (
    id                 text primary key,
    post_id            text not null references public.instagram_posts (id) on delete cascade,
    project_id         text not null references public.projects (id) on delete cascade,
    position           smallint not null check (position >= 1),
    -- Public commenter handle as the platform shows it. No private data, no
    -- contact details, and nothing that needed a login to see.
    commenter_username text,
    comment_text       text not null default '',
    like_count         integer,
    posted_at          timestamptz,
    created_at         timestamptz not null default now(),

    constraint instagram_post_comments_position_unique unique (post_id, position)
);

create index if not exists instagram_post_comments_project_idx
    on public.instagram_post_comments (project_id, post_id, position);


-- ----------------------------------------------------------------- RLS ------

alter table public.website_pages            enable row level security;
alter table public.instagram_posts          enable row level security;
alter table public.instagram_post_media     enable row level security;
alter table public.instagram_post_comments  enable row level security;

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
