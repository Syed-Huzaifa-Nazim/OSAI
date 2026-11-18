import {
  CreditCard,
  FileSearch,
  FileText,
  LayoutDashboard,
  Lightbulb,
  Plug,
  Radar,
  Settings,
  Swords,
  User,
  type LucideIcon,
} from 'lucide-react'
import type { ComparisonType } from '@/types/domain'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /** Matches nested routes too, e.g. /app/projects/:id. */
  matchPrefix?: boolean
}

export const MAIN_NAV: NavItem[] = [
  { label: 'Dashboard', to: '/app/dashboard', icon: LayoutDashboard },
  { label: 'Projects', to: '/app/projects', icon: Radar, matchPrefix: true },
]

export const SETTINGS_NAV: NavItem[] = [
  { label: 'Profile', to: '/app/settings/profile', icon: User },
  { label: 'Account', to: '/app/settings/account', icon: Settings },
  { label: 'Integrations', to: '/app/settings/integrations', icon: Plug },
  { label: 'Billing', to: '/app/settings/billing', icon: CreditCard },
]

/**
 * Per-project workspace nav, shown only while inside a project.
 *
 * Every real comparison scrapes and displays, and none of them runs the agent
 * pipeline, so each gets its one page and none of the pipeline's: a product
 * comparison its comparison page, a website or social one its scraped-data
 * page. Only the seeded demo project still walks the nine stages, so only it
 * gets their screens. Until the project has loaded, nothing is shown rather
 * than a list that might be wrong.
 */
export function projectNav(
  projectId: string,
  comparisonType?: ComparisonType,
): NavItem[] {
  const base = `/app/projects/${projectId}`
  if (comparisonType === undefined) return []
  const evidenceRoute = comparisonType === 'ecommerce_product' ? 'comparison' : 'sources'
  const evidenceLabel = comparisonType === 'ecommerce_product' ? 'Product comparison' : 'Evidence'

  // Keep the nine technical stages inside the pages. The project sidebar is
  // organised around the user's decisions: understand, inspect, decide,
  // approve, and export.
  return [
    { label: 'Overview', to: `${base}/overview`, icon: LayoutDashboard },
    { label: evidenceLabel, to: `${base}/${evidenceRoute}`, icon: FileSearch },
    { label: 'Findings', to: `${base}/findings`, icon: Lightbulb },
    { label: 'Strategy', to: `${base}/strategy`, icon: Swords },
    { label: 'Deliverables', to: `${base}/deliverables`, icon: FileText },
  ]
}

export const MARKETING_NAV: { label: string; to: string }[] = [
  { label: 'How it works', to: '/how-it-works' },
  { label: 'Features', to: '/features' },
  { label: 'Pricing', to: '/pricing' },
  { label: 'About', to: '/about' },
  { label: 'Contact', to: '/contact' },
]
