-- ============================================================================
-- 0007 -- The signals behind a website comparison
--
-- Run AFTER 0001 to 0006.
--
-- Apply by pasting into the Supabase SQL editor and running, or:
--     supabase db execute --file backend/app/db/migrations/0007_website_page_signals.sql
--
-- Safe to re-run: the column is added `if not exists`.
--
-- NON-DESTRUCTIVE. Adds one column. Nothing is dropped or rewritten, and pages
-- scraped before it simply have an empty object: scrape again to fill them.
--
-- What it stores: the checkable facts each page gives away -- viewport tag,
-- heading hierarchy, alt-text coverage, internal and external link counts,
-- call-to-action and form counts, pricing and legal links, social proof and
-- certification wording, and the third-party analytics, chat and payment
-- scripts it loads. The root page also carries the site-level probes
-- (robots.txt and sitemap).
--
-- These are facts, not judgements: the A-F comparison parameters are derived
-- from them at read time in app/scrapers/website/metrics.py, so changing how a
-- parameter scores never needs a re-crawl or another migration.
-- ============================================================================

alter table public.website_pages
    add column if not exists signals jsonb not null default '{}'::jsonb;
