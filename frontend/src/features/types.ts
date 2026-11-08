import type { LucideIcon } from 'lucide-react'
import type { ComponentType } from 'react'

/**
 * The contract a teammate's feature repo implements to plug into the app.
 * See docs/architecture.md, "Feature integration layer", for the full walkthrough.
 */
export interface FeatureRoute {
  /** Path relative to /app: e.g. 'seo-audit' becomes /app/seo-audit. */
  path: string
  /** Rendered inside the authenticated shell. Lazy-import it in the manifest. */
  component: ComponentType
}

export interface FeatureNavEntry {
  label: string
  icon: LucideIcon
  /** Must match one of the feature's own route paths. */
  to: string
  /** Where it appears in the sidebar. */
  section: 'main' | 'project' | 'settings'
}

export interface FeatureManifest {
  /** Stable key. Also the Supabase `integrations.feature_key` value. */
  key: string
  name: string
  description: string
  /** Owner, so it is obvious who to ask when something breaks. */
  owner: string
  routes: FeatureRoute[]
  nav: FeatureNavEntry[]
  /**
   * When false the feature is registered but hidden. Routes are not mounted
   * and nav entries are not shown. Lets a half-finished module sit in the tree
   * without affecting anyone.
   */
  enabled: boolean
}
