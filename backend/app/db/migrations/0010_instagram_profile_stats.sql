alter table public.instagram_posts
    add column if not exists profile_stats jsonb not null default '{}'::jsonb;