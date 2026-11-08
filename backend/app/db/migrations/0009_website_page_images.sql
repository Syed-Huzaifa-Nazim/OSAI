-- ============================================================================
-- 0009 -- Images collected from crawled website pages
--
-- Run AFTER 0005, 0006, 0007 and 0008.
--
-- Apply by pasting into the Supabase SQL editor and running, or:
--     supabase db execute --file backend/app/db/migrations/0009_website_page_images.sql
--
-- Safe to re-run: the table, its index and its policy are all guarded.
--
-- NON-DESTRUCTIVE. Adds one table. No existing table, column or row changes.
--
-- What it stores, and why a table rather than a column:
--   A website comparison judges how a site presents itself, and that includes
--   what it shows, not only what it says. The crawler now keeps each page's
--   social preview image, its hero/banner, and the prominent content images --
--   icons, logos, sprites and tracking pixels are filtered out by
--   app/scrapers/website/images.py.
--
--   One row per image, exactly like ecommerce_product_images and
--   instagram_post_media: the same storage rule (keep the site's own URL,
--   download nothing), the same cascade, the same RLS shape. A jsonb column
--   would have been a third pattern for the same kind of data.
-- ============================================================================

create table if not exists public.website_page_images (
    id          text primary key,
    -- Re-crawling replaces the page, and the cascade takes its images with it.
    page_id     text not null references public.website_pages (id) on delete cascade,
    -- Denormalised so RLS checks ownership with the usual one join.
    project_id  text not null references public.projects (id) on delete cascade,
    -- 1-based. Position 1 is the page's most representative image.
    position    smallint not null check (position >= 1),
    -- The site's own URL. Nothing is downloaded or re-hosted.
    image_url   text not null,
    -- The alt text as written, which is also what the A-F accessibility
    -- signals are measured from.
    alt_text    text,
    -- Where on the page it was found, most deliberate first: og_image is the
    -- preview a site chose for itself, hero is the banner, content is body.
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


-- ----------------------------------------------------------------- RLS ------

alter table public.website_page_images enable row level security;

drop policy if exists website_page_images_owner_all on public.website_page_images;
create policy website_page_images_owner_all on public.website_page_images
    for all using (exists (
        select 1 from public.projects p
        where p.id = website_page_images.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = website_page_images.project_id and p.owner_id = auth.uid()));
