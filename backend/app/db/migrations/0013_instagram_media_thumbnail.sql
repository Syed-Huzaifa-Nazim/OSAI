-- 0013: the cover picture of each Instagram post item.
--
-- For a reel, media_url is the video file, so the profile grid had nothing to show but a play icon.
-- Instagram's own still picture (the cover frame) is kept beside it, and the grid shows it.
--
-- Non-destructive and re-runnable: one nullable column. Existing rows get NULL and show the play
-- icon until the project is scraped again.

alter table public.instagram_post_media
    add column if not exists thumbnail_url text;
ost:h