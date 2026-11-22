-- 0010: profile-level numbers on instagram_posts, for the engagement model.
--
-- The engagement model (app/analysis/instagram/) grades a profile from its
-- followers, following, total posts, bio, website, highlights, verified badge
-- and category, as well as its posts. The posts run already returns these on
-- the profile item; this column keeps them, on every post row of that side,
-- the same way profile_username is kept (migration 0008).
--
-- Non-destructive: one column with a default. Existing rows get '{}', and the
-- analysis reports those sides as "not enough profile data" until re-scraped.

alter table public.instagram_posts
    add column if not exists profile_stats jsonb not null default '{}'::jsonb;
