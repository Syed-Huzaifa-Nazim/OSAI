-- 0014: "What the business does" may be up to 500 characters (was 120).
-- Sellers write products, ordering terms and their address here, which did not fit in 120.
-- Safe to run more than once.

alter table public.projects
    drop constraint if exists projects_brand_description_check;

alter table public.projects
    add constraint projects_brand_description_check
    check (char_length(brand_description) between 1 and 500);
