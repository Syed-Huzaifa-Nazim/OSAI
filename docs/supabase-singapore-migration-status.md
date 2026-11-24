# Supabase Ireland to Singapore migration status

Checked 2026-11-24 and updated 2026-11-25 with Supabase CLI 2.122.0 and PostgreSQL client 17.12. The Singapore database contains a verified staging copy. Production database settings still point to Ireland; the current code release request does not change Supabase credentials.

## Projects

| Role | Project ref | Region | State |
| --- | --- | --- | --- |
| Source | `gmequvuherrpmjkxmadv` | `eu-west-1` (Ireland) | `ACTIVE_HEALTHY`, linked locally |
| Destination | `ujethcxwlyjlqnspphkt` | `ap-southeast-1` (Singapore) | `ACTIVE_HEALTHY`, staging copy; unlinked locally |

Before import, the destination had no application tables or auth users. Neither project has Storage buckets/objects or deployed Edge Functions.

## Database inventory

| Object | Source | Destination |
| --- | ---: | ---: |
| Public tables | 28 | 28 |
| Public table rows, exact total | 2,925 | 2,925 |
| Auth users / identities | 4 / 4 | 4 / 4 |
| Auth sessions / MFA factors | 5 / 0 | 5 / 0 |
| Public primary keys / foreign keys | 28 / 48 | 28 / 48 |
| Public unique constraints / indexes | 10 / 67 | 10 / 67 |
| Public RLS policies | 26 | 26 |
| Public table grant rows / routine grant rows | 784 / 523 | 784 / 523 |
| Application functions in public | 12 | 12 |
| Custom triggers in public / auth | 1 / 1 | 1 / 1 |
| Public views / materialized views / sequences | 0 / 0 / 1 | 0 / 0 / 1 |
| Storage buckets / objects / policies | 0 / 0 / 0 | 0 / 0 / 0 |
| Realtime publication tables in public | 0 | 0 |
| Cron extension | Absent | Absent |
| Vault secrets | 0 | 0 |

Both projects have `vector` 0.8.2, `pg_stat_statements`, `pgcrypto`, `supabase_vault`, and `uuid-ossp`. The source has `supabase_vault` 0.3.1 and the destination has 0.3.2; neither has Vault secrets. Both have the `supabase_realtime` publication, with no public tables subscribed. The custom triggers are `auth.users:award_starter_tokens` and `public.projects:projects_touch_updated_at` in both projects.

Exact source rows by table: `admin_email_outbox` 0; `admin_members` 1; `competitors` 9; `contact_submissions` 0; `content_suggestions` 5; `critic_feedback` 0; `ecommerce_product_images` 30; `ecommerce_product_price_tiers` 0; `ecommerce_product_suppliers` 0; `ecommerce_products` 4; `gaps_opportunities` 33; `hitl_reviews` 3; `instagram_post_chunks` 1,080; `instagram_post_comments` 343; `instagram_post_media` 621; `instagram_posts` 384; `integrations` 0; `pipeline_states` 9; `projects` 9; `scraped_sources` 388; `strategies` 1; `strategy_documents` 1; `token_ledger` 2; `token_requests` 0; `token_runs` 0; `token_wallets` 2; `website_page_images` 0; `website_pages` 0.

## Recovery point and staging restore

PostgreSQL 17 was prepended to the Windows User PATH. Open a new terminal to resolve `pg_dump` and `psql` by name.

PostgreSQL 17.12 `pg_dump`, `pg_restore`, and `psql` are installed at `C:\Program Files\PostgreSQL\17\bin`, matching both projects' PostgreSQL major version. On 2026-11-25, a full custom-format source archive was created outside Git at `C:\Users\Yousuf Traders\AppData\Local\Temp\osai-supabase-migration\source-full-20261125-014533.dump` (2,468,193 bytes; SHA-256 `A3C1A0F3B2DF6CCE73C80A39F40A078288B7B5C5DA72B74724436669BD1C11BA`). `pg_dump`, `pg_restore --list`, and full archive expansion succeeded. The archive has 991 entries and 68 table-data entries, including `auth.users` and `public.projects`. A durable Windows DPAPI encrypted copy was written outside Git to `C:\Users\Yousuf Traders\AppData\Local\OSAI\backups\supabase-ireland-20261125.dump.dpapi`; it was decrypted in memory and its SHA-256 matched the source archive. DPAPI CurrentUser protection ties recovery to this Windows user profile, so preserve the profile or make another secure backup before losing access to it. Both files contain sensitive database data and must never be committed or shared. A temporary Supabase CLI database login was used privately; no password was written to the repository.

The first restore rehearsal was rolled back after a managed-role default-grant conflict. Source and destination default grants were confirmed identical, so those redundant statements were omitted. The second rehearsal passed and was rolled back, leaving Singapore empty. The selective PostgreSQL 17 restore was then committed in one transaction. It restored public schema, public and auth data, and the custom auth trigger without modifying Supabase-managed baseline migrations. A restore text conversion had altered function line endings; all 12 public function definitions were reapplied from the original archive and their source/destination digests now match.

The source is live. This staging snapshot will become stale as soon as users write new data. Before production cutover, arrange a short write freeze and final consistent sync. Singapore's ES256 signing key differs from Ireland's, so existing sessions will need a fresh sign-in. The owner accepted this as long as users retain the same accounts and data. All four original auth user IDs, emails, password hashes, identities, ownership links, project history, and related data were copied exactly; users must sign in to their existing accounts, not sign up again.

## Deployment references

Both local `backend/.env` and `frontend/.env` still reference Ireland. Railway production service `OSAI` in project `truthful-abundance` has the Supabase URL and keys configured; those production values were not changed. The frontend uses `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`; verify Vercel production variables during the later database cutover. Singapore's API keys were retrieved privately for staging tests, but were not printed, saved in Git, or applied to deployment settings. The subsequent request authorizes a code release after tests, not a database credential cutover.

## Staging verification completed

- Exact row counts and content digests match for all 55 public/auth tables after the restore and after the temporary-login smoke test: 2,925 public rows, four auth users, four identities, nine projects, and 1,080 Instagram chunks.
- Public column, constraint, index, RLS policy, grant, sequence-value, and all 12 function-definition digests match. Triggers and extension versions were checked; `supabase_vault` has a newer patch version in Singapore, with no secrets in either project.
- Auth configuration was compared privately: site URL, redirect allowlist, signup, email confirmation, JWT expiry, SMTP presence, and external provider enablement match. Both projects currently use `http://localhost:3000` as the Auth site URL, which should be corrected for production at cutover.
- An authenticated migrated owner can read eight owned projects and zero other users' projects through RLS.
- Using Singapore keys in memory, anonymous REST access returned zero projects, service-role REST access returned a project, and the backend's Supabase service client read a project with `DEMO_MODE=False`.
- A temporary Singapore auth user was created with email confirmation, signed in with a password, and its ES256 JWT passed the backend verifier. Its user-scoped project query returned zero rows. The temporary user was deleted; affected sequences were reset and all 55 table digests were rechecked with zero mismatches. No confirmation email was sent for this admin API test.
- A fresh post-migration check matched row counts and content digests for all 55 public/auth tables and both identity sequences. Eight metadata categories also matched: 593 columns, 258 constraints, 179 indexes, 26 policies, 12 application functions, two custom triggers, 55 RLS flags, and 967 visible table grants.
- Authenticated owner access, an owner update, and token reservation/cancellation passed in a rolled-back Singapore transaction; the wallet balance returned to its starting value.
- The local backend exercised 17 admin/token API calls against Singapore: non-admin denial, admin summary/users/details, nine migrated projects, verified and unverified user creation, custom email drafts held pending provider, token requests/approval/adjustment, and ledger reads. Three disposable users were deleted; both advanced sequences were restored. The final 55 table digests and both sequences still match Ireland.
- Backend tests: 458 passed, three skipped. Frontend tests: 197 passed. Frontend production build passed.

## Remaining before production cutover

- When deployment changes are authorized, freeze writes and repeat the final source-to-Singapore sync; verify row/content digests again so new Ireland writes are not lost.
- Set the Singapore URL and project-specific keys in Railway backend and Vercel frontend through private environment settings. Review the Auth site URL and redirect allowlist for the production domain. Do not reuse Ireland API keys as Singapore API keys.
- Deploy and run live login, project, admin, and Daraz/Instagram workflow checks, then monitor. Keep the Ireland configuration available for rollback, accounting for any new Singapore writes before reverting.

The source project, local `.env` files, Railway/Vercel database settings, and production database cutover were not changed during staging verification. The Singapore staging database was intentionally populated and verified.
