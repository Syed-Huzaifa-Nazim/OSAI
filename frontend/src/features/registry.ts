import type { FeatureManifest, FeatureNavEntry, FeatureRoute } from './types'

/**
 * FEATURE INTEGRATION POINT
 * =========================
 * Teammates' separately-built features register here and nowhere else. Adding
 * one is a single line in the array below plus a folder beside this file. No
 * edits to the router, the sidebar, or any existing page.
 *
 * To add a feature:
 *   1. Drop the repo's UI into `src/features/<your-feature>/`.
 *   2. Export a `FeatureManifest` as the folder's default export.
 *   3. Import it here and add it to `FEATURES`.
 *   4. Mount its backend router in `backend/app/api/v1/__init__.py` (also one line).
 *
 * Nothing is registered yet. See docs/architecture.md before adding the first.
 */
export const FEATURES: FeatureManifest[] = [
  // Example (do not uncomment until the feature folder exists):
  // seoAuditFeature,
]

export function enabledFeatures(): FeatureManifest[] {
  return FEATURES.filter((feature) => feature.enabled)
}

export function featureRoutes(): (FeatureRoute & { featureKey: string })[] {
  return enabledFeatures().flatMap((feature) =>
    feature.routes.map((route) => ({ ...route, featureKey: feature.key })),
  )
}

export function featureNavEntries(section: FeatureNavEntry['section']): FeatureNavEntry[] {
  return enabledFeatures()
    .flatMap((feature) => feature.nav)
    .filter((entry) => entry.section === section)
}

export function findFeature(key: string): FeatureManifest | undefined {
  return FEATURES.find((feature) => feature.key === key)
}
