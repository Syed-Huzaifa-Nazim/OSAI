-- ============================================================================
-- 0006 -- One Instagram post can belong to both sides of a comparison
--
-- Run AFTER 0001 to 0005.
--
-- Apply by pasting into the Supabase SQL editor and running, or:
--     supabase db execute --file backend/app/db/migrations/0006_instagram_post_uniqueness.sql
--
-- Safe to re-run: the constraint is dropped before it is recreated.
--
-- NON-DESTRUCTIVE. Replaces one unique constraint with a wider one. No column
-- changes, no data rewritten, nothing dropped.
--
-- THE BUG THIS FIXES
--   `instagram_posts` was unique on (project_id, post_url), which assumed a
--   post belongs to one profile. Instagram collaboration posts appear on every
--   collaborator's profile under the same URL, so comparing two related
--   accounts produced the same post_url twice in one project.
--
--   Measured on a real run: 24 posts were scraped from two public profiles and
--   2 of them were shared by both. The whole batch is one insert, so that one
--   collision rejected all 24 rows, and the posts' media and comments then
--   failed their foreign key because no parent row existed. The scrape still
--   reported success, and the screen said "Nothing was collected".
--
--   The post genuinely belongs to both sides and has to be counted for both,
--   so the key becomes (project_id, role, post_url): one copy per side, and a
--   repeat within one side is still refused.
-- ============================================================================

alter table public.instagram_posts
    drop constraint if exists instagram_posts_post_unique;

alter table public.instagram_posts
    add constraint instagram_posts_post_unique unique (project_id, role, post_url);
