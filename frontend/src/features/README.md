# Feature integration layer

This is where a teammate's separately-built feature repo plugs into the app.

Adding one touches **two files**: this folder, and one line in `registry.ts`.
No edits to the router, the sidebar, or any existing page.

## Adding a feature

1. **Drop the module in.** Create `src/features/<your-feature>/` and put the
   repo's UI inside it. Keep its own components, hooks and styles local to that
   folder: nothing outside it should import from within.

2. **Export a manifest.** Add `src/features/<your-feature>/index.ts`:

   ```ts
   import { BarChart3 } from 'lucide-react'
   import type { FeatureManifest } from '../types'
   import { SeoAuditPage } from './seo-audit-page'

   const manifest: FeatureManifest = {
     key: 'seo-audit',              // also the integrations.feature_key value
     name: 'SEO Audit Module',
     description: 'Technical SEO audit folded into the gap list.',
     owner: 'Muhammad Umar Khan',
     routes: [{ path: 'seo-audit', component: SeoAuditPage }],
     nav: [
       { label: 'SEO Audit', icon: BarChart3, to: 'seo-audit', section: 'main' },
     ],
     enabled: true,
   }

   export default manifest
   ```

3. **Register it.** In `registry.ts`:

   ```ts
   import seoAudit from './seo-audit'

   export const FEATURES: FeatureManifest[] = [seoAudit]
   ```

   The router mounts every route under `/app/`, and the sidebar renders every
   nav entry in the section it names. Both read from the registry.

4. **Mount the backend.** Add one line to `backend/app/api/v1/__init__.py`:

   ```python
   from app.features.seo_audit.routes import router as seo_audit_router
   api_router.include_router(seo_audit_router)
   ```

5. **Add the registry row.** Insert into `public.integrations` with the same
   `feature_key`, so the module appears on `/app/settings/integrations`.

## Rules

- **`enabled: false` hides it completely**: routes are not mounted and nav
  entries are not shown. Use it to land a half-finished module without
  affecting anyone.
- **A feature may import from `@/components/ui`, `@/lib` and `@/types`.**
  It must not import from `@/pages` or from another feature.
- **`key` is stable.** It is the join between the frontend registry, the
  backend router and the database row.

Nothing is registered yet. See `docs/architecture.md` for the full rationale.
