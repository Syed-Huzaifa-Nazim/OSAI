import {
  CreditCard,
  FileBarChart,
  FileSearch,
  FileText,
  LayoutDashboard,
  Lightbulb,
  ListChecks,
  Radar,
  Scale,
  Settings,
  ShieldCheck,
  Sparkles,
  Swords,
  User,
  Workflow,
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
  { label: 'My reports', to: '/app/reports', icon: FileBarChart },
]

export const SETTINGS_NAV: NavItem[] = [
  { label: 'Profile', to: '/app/settings/profile', icon: User },
  { label: 'Account', to: '/app/settings/account', icon: Settings },
  { label: 'Billing', to: '/app/settings/billing', icon: CreditCard },
  { label: 'Tokens', to: '/app/settings/tokens', icon: CreditCard },
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
  isDemo = false,
): NavItem[] {
  const base = `/app/projects/${projectId}`
  if (comparisonType === undefined) return []
  if (!isDemo) {
    if (comparisonType === 'ecommerce_product') {
      return [{ label: 'Product comparison', to: `${base}/comparison`, icon: Scale }]
    }
    // A website is scored against its competitor on the same page that lists
    // what was scraped; a social comparison has no parameters yet.
    return [
      {
        label: comparisonType === 'website' ? 'Website comparison' : 'Scraped data',
        to: `${base}/sources`,
        icon: FileSearch,
      },
    ]
  }
  return [
    { label: 'Pipeline', to: `${base}/pipeline`, icon: Workflow },
    { label: 'Insights', to: `${base}/insights`, icon: Lightbulb },
    { label: 'Review gaps', to: `${base}/review-gaps`, icon: ListChecks },
    { label: 'Strategy', to: `${base}/strategy`, icon: Swords },
    { label: 'Final approval', to: `${base}/review-strategy`, icon: ShieldCheck },
    { label: 'Document', to: `${base}/document`, icon: FileText },
    { label: 'Automation', to: `${base}/automation`, icon: Sparkles },
  ]
}

export const MARKETING_NAV: { label: string; to: string }[] = [
  { label: 'How it works', to: '/how-it-works' },
  { label: 'Features', to: '/features' },
  { label: 'About', to: '/about' },
  { label: 'Contact', to: '/contact' },
]
