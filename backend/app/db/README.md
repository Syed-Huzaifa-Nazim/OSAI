# Database

`schema.sql` is the single source of truth for the Postgres side. Apply it to a
fresh Supabase project with either:

```bash
supabase db execute --file backend/app/db/schema.sql
```

or by pasting it into the SQL editor in the Supabase dashboard.

The file is idempotent, every `create` is `if not exists` and every policy is
dropped before being recreated, so re-running it after an edit is safe.

See `docs/database.md` for the table-by-table explanation and the RLS model.

## Migrations

`migrations/` holds numbered, ordered `.sql` files for changing a database that
already has data in it. `schema.sql` builds a database from nothing; a
migration moves an existing one forward. Both are kept in step, so:

- **new Supabase project** — run `schema.sql` only. It already contains
  everything the migrations add.
- **existing project with data** — run the migrations you have not applied yet,
  in numeric order. Do not re-run `schema.sql` expecting it to alter columns;
  its `create table if not exists` will skip a table that is already there.

When you change the schema, edit `schema.sql` *and* add a migration in the same
commit, or the two drift apart.

| File | What it does |
| --- | --- |
| `0001_ecommerce_scrapers.sql` | Adds the e-commerce comparison type (`projects.comparison_type`, `projects.ecommerce_platform`), extends `scraped_sources.kind`, and creates `ecommerce_products` with its indexes and RLS policy. Non-destructive: adds only, rewrites no existing row. |
| `0002_intake_fields_and_social_platform.sql` | Intake rule changes on `projects`: `brand_description` loses its 40-character minimum and is capped at 120; `target_audience` becomes optional, capped at 120; new `social_platform` column (`facebook` / `instagram`), required for social comparisons. Also *verifies* every link column is `text` — link length was never limited in the database. Existing rows over 120 characters would block it; the file header has the query to check. |
| `0003_ecommerce_product_images.sql` | New `ecommerce_product_images` table: one row per scraped product photo (`url`, 1-based `position`, `is_primary`, `source`), cascading from `ecommerce_products`, with its index and RLS policy. Stores Daraz's own image URLs only — no storage bucket. Non-destructive: adds one table. |
| `0007_website_page_signals.sql` | Adds `website_pages.signals` (JSONB): the checkable facts each page gives away (viewport, heading hierarchy, alt coverage, link counts, CTAs, forms, pricing and legal links, social proof wording, third-party analytics/chat/payment scripts, and robots/sitemap on the root page). The A-F website comparison parameters are derived from these at read time, so re-scoring never needs a re-crawl. Non-destructive: one column, default `{}`. |
| `0006_instagram_post_uniqueness.sql` | Widens `instagram_posts`' unique key from `(project_id, post_url)` to `(project_id, role, post_url)`. An Instagram collaboration post appears on every collaborator's profile under one URL, so comparing two related accounts collided and rejected the whole insert batch, leaving the run reporting success with nothing stored. Non-destructive: one constraint replaced. |
| `0005_website_instagram_scrapers.sql` | Storage for the website and Instagram scrapers: new `website_pages` (one crawled page: title, meta description, headings, links, readable text, renderer, depth), `instagram_posts` (one public post: caption, hashtags, likes, comments count, media), `instagram_post_media` and `instagram_post_comments`, each with its index and RLS policy. `scraped_sources` already allowed `landing_page` and `social_post`, so it is unchanged. Non-destructive: adds four tables. |
| `0008_instagram_profile_username.sql` | Adds `instagram_posts.profile_username`: the scraped profile's own handle, from the actor's profile item. The results screen labelled each side with the first post's `owner_username`, which on a collaboration post is the *other* account, so a profile could be displayed under a stranger's handle. `owner_username` stays per-post — it is how a collaboration is recognised. Non-destructive: one nullable column; existing rows fall back to the submitted link until re-scraped. |
| `0009_website_page_images.sql` | New `website_page_images` table: one row per image kept from a crawled page (`image_url`, 1-based `position`, `is_primary`, `alt_text`, `source` of `og_image`/`hero`/`content`, declared `width`/`height`), cascading from `website_pages`, with its index and RLS policy. Same rule as the other image tables — the site's own URL is stored, nothing is downloaded. Icons, logos, sprites and tracking pixels are filtered out before storage. Non-destructive: adds one table. |
| `0004_alibaba_platform.sql` | Adds Alibaba as an e-commerce platform: `'alibaba'` allowed in `projects.ecommerce_platform` and `ecommerce_products.platform`; `price`/`original_price` widened to `numeric(14,4)` for sub-cent unit prices; nullable B2B columns `max_price`, `moq`, `moq_unit`, `lead_time_days`; new `ecommerce_product_price_tiers` and `ecommerce_product_suppliers` tables with indexes and RLS. Non-destructive. |

Every migration here is written to be re-runnable — columns are added
`if not exists`, constraints and policies are dropped before being recreated —
so applying one twice is harmless.
