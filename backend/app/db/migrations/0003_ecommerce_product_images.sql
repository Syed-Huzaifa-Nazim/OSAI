-- ============================================================================
-- 0003 -- Product images for scraped e-commerce listings
--
-- Run AFTER 0001 and 0002.
--
-- Apply by pasting into the Supabase SQL editor and running, or:
--     supabase db execute --file backend/app/db/migrations/0003_ecommerce_product_images.sql
--
-- Safe to re-run: the table and indexes are created `if not exists`, and the
-- policy is dropped before it is recreated.
--
-- NON-DESTRUCTIVE. Adds one table. No existing table, column or row changes.
--
-- What it stores: the product photos the scraper reads from each listing, one
-- row per photo, main image first. Only the platform's own image URLs are
-- kept (Daraz's CDN) -- nothing is downloaded or re-hosted, so there is no
-- storage bucket to create.
--
-- Listings scraped before this migration simply have no image rows; press
-- "Scrape again" on a comparison to collect them.
-- ============================================================================

create table if not exists public.ecommerce_product_images (
    id          text primary key,
    -- The listing this photo belongs to. Re-scraping replaces the listing,
    -- and the cascade takes its old photos with it.
    product_id  text not null references public.ecommerce_products (id) on delete cascade,
    -- Denormalised from the product so the RLS policy below can check
    -- ownership with the same one-join pattern every other table uses.
    project_id  text not null references public.projects (id) on delete cascade,
    -- 1-based gallery order. Position 1 is the main image.
    position    smallint not null check (position >= 1),
    -- The image's URL on the platform's CDN. text, not varchar: no length cap.
    url         text not null,
    is_primary  boolean not null default false,
    -- Where on the page the photo was found, most trustworthy first.
    source      text not null default 'gallery' check (source in (
                    'gallery', 'structured_data', 'page', 'og_image')),
    created_at  timestamptz not null default now(),

    constraint ecommerce_product_images_position_unique unique (product_id, position),
    -- The main image is the first one. Stated as a rule so the two can never
    -- disagree.
    constraint ecommerce_product_images_primary_is_first check (is_primary = (position = 1))
);

-- Reading a comparison loads every photo in a project, in gallery order.
create index if not exists ecommerce_product_images_project_idx
    on public.ecommerce_product_images (project_id, product_id, position);


-- ----------------------------------------------------------------- RLS ------

alter table public.ecommerce_product_images enable row level security;

drop policy if exists ecommerce_product_images_owner_all on public.ecommerce_product_images;
create policy ecommerce_product_images_owner_all on public.ecommerce_product_images
    for all using (exists (
        select 1 from public.projects p
        where p.id = ecommerce_product_images.project_id and p.owner_id = auth.uid()))
    with check (exists (
        select 1 from public.projects p
        where p.id = ecommerce_product_images.project_id and p.owner_id = auth.uid()));
