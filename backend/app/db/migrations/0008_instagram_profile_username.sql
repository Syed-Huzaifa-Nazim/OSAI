-- ============================================================================
-- 0008 -- The scraped profile's own username
--
-- Run AFTER 0005, 0006 and 0007.
--
-- Apply by pasting into the Supabase SQL editor and running, or:
--     supabase db execute --file backend/app/db/migrations/0008_instagram_profile_username.sql
--
-- Safe to re-run: the column is added `if not exists`.
--
-- NON-DESTRUCTIVE. Adds one nullable column. No existing column or row
-- changes, and nothing outside instagram_posts is touched.
--
-- Why:
--   The results screen labelled each side with the `owner_username` of that
--   side's first post. On a collaboration post -- two accounts publishing the
--   same post together -- the author is the OTHER account, so a profile whose
--   newest post was a collaboration was displayed under a stranger's handle.
--
--   `owner_username` is still worth keeping: it is how a collaboration post is
--   recognised as one. What was missing is the profile's own identity, which
--   the Apify actor reports on the profile item itself and which this column
--   stores. The screen reads this; `owner_username` stays per-post.
--
--   Existing rows keep NULL. The scraper fills it on the next scrape, and the
--   screen falls back to the submitted profile link until then, so nothing is
--   left showing the wrong name.
-- ============================================================================

alter table public.instagram_posts
    add column if not exists profile_username text;

comment on column public.instagram_posts.profile_username is
    'The scraped profile''s own handle, from the actor''s profile item. What the '
    'screen labels this side with. owner_username is the per-post author, which '
    'differs on a collaboration post.';
