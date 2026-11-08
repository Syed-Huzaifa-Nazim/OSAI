-- ============================================================================
-- 0002 -- Intake form field rules + social media platform
--
-- Run AFTER 0001 (or after a schema.sql that already contains 0001).
--
-- Apply by pasting into the Supabase SQL editor and running, or:
--     supabase db execute --file backend/app/db/migrations/0002_intake_fields_and_social_platform.sql
--
-- Safe to re-run: columns are added `if not exists`, and every constraint is
-- dropped before it is recreated.
--
-- What it changes, all on public.projects:
--   1. brand_description  no 40-character minimum any more; maximum 120
--   2. target_audience    now optional (nullable); maximum 120
--   3. social_platform    new column: 'facebook' | 'instagram', required for
--                         a social_media comparison and null for every other
--
-- What it deliberately does NOT change -- link columns:
--   The "link is too long" error was never a database limit. Every column that
--   stores a link is already `text`, which has no length cap in Postgres:
--       projects.brand_website, competitors.landing_page_url,
--       scraped_sources.url, ecommerce_products.url
--   The 500-character caps were in the frontend form (zod) and the backend
--   request model (Pydantic); both are fixed in code, so no column needs to be
--   retyped here. The block at the bottom verifies that assumption and stops
--   with an error if any of those columns is not text.
--
-- EXISTING ROWS: the new 120-character limits are validated against rows
-- already in the table. When this was written the projects table was empty.
-- If you have created projects since, check first:
--     select id, char_length(brand_description) as description_chars,
--            char_length(target_audience)   as audience_chars
--     from public.projects
--     where char_length(brand_description) > 120
--        or char_length(target_audience)   > 120;
-- Any row returned will make step 1 or 2 fail; shorten those values first.
-- ============================================================================


-- ---------------------------------------------- 1. brand_description --------
-- The original limit was written as an unnamed column check, so Postgres named
-- it itself. Rather than guess that name, drop every check constraint on
-- projects that mentions brand_description, then add one with a fixed name.

do $$
declare
    constraint_row record;
begin
    for constraint_row in
        select conname
        from pg_constraint
        where conrelid = 'public.projects'::regclass
          and contype = 'c'
          and pg_get_constraintdef(oid) ilike '%brand_description%'
    loop
        execute format('alter table public.projects drop constraint %I', constraint_row.conname);
    end loop;
end $$;

alter table public.projects
    add constraint projects_brand_description_check
    check (char_length(brand_description) between 1 and 120);


-- ------------------------------------------------ 2. target_audience --------

alter table public.projects
    alter column target_audience drop not null;

alter table public.projects
    drop constraint if exists projects_target_audience_check;
alter table public.projects
    add constraint projects_target_audience_check
    check (target_audience is null or char_length(target_audience) <= 120);


-- ------------------------------------------------ 3. social_platform --------
-- Kept separate from ecommerce_platform so this migration only adds: nothing
-- that 0001 created is renamed or retyped.

alter table public.projects
    add column if not exists social_platform text;

alter table public.projects
    drop constraint if exists projects_social_platform_check;
alter table public.projects
    add constraint projects_social_platform_check
    check (social_platform is null or social_platform in ('facebook', 'instagram'));

-- A platform only means something for a social comparison, and a social
-- comparison is meaningless without one. Existing social_media rows (if any)
-- have no platform yet, so this would fail on them; there were none when this
-- was written.
alter table public.projects
    drop constraint if exists projects_social_platform_matches_type_check;
alter table public.projects
    add constraint projects_social_platform_matches_type_check
    check (
        (comparison_type = 'social_media' and social_platform is not null)
        or (comparison_type <> 'social_media' and social_platform is null)
    );


-- ------------------------------------ 4. verify: link columns are text -------
-- Changes nothing. Raises an error naming the column if any link column has a
-- length-limited type, so a schema that drifted from schema.sql is caught
-- here instead of as a failed insert later.

do $$
declare
    bad record;
begin
    for bad in
        select table_name, column_name, data_type, character_maximum_length
        from information_schema.columns
        where table_schema = 'public'
          and (table_name, column_name) in (
              ('projects', 'brand_website'),
              ('competitors', 'landing_page_url'),
              ('scraped_sources', 'url'),
              ('ecommerce_products', 'url'))
          and data_type <> 'text'
    loop
        raise exception 'Link column %.% is % (max %), expected text',
            bad.table_name, bad.column_name, bad.data_type, bad.character_maximum_length;
    end loop;
end $$;
