# Database

`schema.sql` is the single source of truth for the Postgres side. Apply it to a
fresh Supabase project with either:

```bash
supabase db execute --file backend/app/db/schema.sql
```

or by pasting it into the SQL editor in the Supabase dashboard.

The file is idempotent, every `create` is `if not exists` and every policy is
dropped before being recreated, so re-running it after an edit is safe.

There is no migration tool wired up yet. While the schema is still moving, edit
`schema.sql` and re-run it. Once real data exists, switch to numbered migration
files under `backend/app/db/migrations/` before changing a column in place.

See `docs/database.md` for the table-by-table explanation and the RLS model.
