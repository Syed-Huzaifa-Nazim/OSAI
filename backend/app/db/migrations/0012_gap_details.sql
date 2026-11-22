-- 0012: plain-language details on each gap.
--
-- The Review Gaps screen now shows, for each gap, how sure we are, example posts
-- (picture, date, likes, link), a small numbers table and optional technical notes.
-- They are kept as one JSON column beside the existing evidence column.
--
-- Non-destructive: one column with a default. Existing gaps get '{}' and keep
-- their old layout.

alter table public.gaps_opportunities
    add column if not exists details jsonb not null default '{}'::jsonb;
