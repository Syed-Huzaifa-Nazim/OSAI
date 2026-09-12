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
| `0004_alibaba_platform.sql` | Adds Alibaba as an e-commerce platform: `'alibaba'` allowed in `projects.ecommerce_platform` and `ecommerce_products.platform`; `price`/`original_price` widened to `numeric(14,4)` for sub-cent unit prices; nullable B2B columns `max_price`, `moq`, `moq_unit`, `lead_time_days`; new `ecommerce_product_price_tiers` and `ecommerce_product_suppliers` tables with indexes and RLS. Non-destructive. |

Every migration here is written to be re-runnable — columns are added
`if not exists`, constraints and policies are dropped before being recreated —
so applying one twice is harmless.
