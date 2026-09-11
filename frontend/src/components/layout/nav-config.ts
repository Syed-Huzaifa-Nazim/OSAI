import {
  CreditCard,
  FileText,
  LayoutDashboard,
  Lightbulb,
  ListChecks,
  Plug,
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
 * An e-commerce comparison scrapes and displays only, so it gets its one page
 * and none of the pipeline's. Until the project has loaded, nothing is shown
 * rather than a list that might be wrong.
 */
export function projectNav(projectId: string, comparisonType?: ComparisonType): NavItem[] {
  const base = `/app/projects/${projectId}`
  if (comparisonType === undefined) return []
  if (comparisonType === 'ecommerce_product') {
    return [{ label: 'Product comparison', to: `${base}/comparison`, icon: Scale }]
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
  { label: 'Pricing', to: '/pricing' },
  { label: 'About', to: '/about' },
  { label: 'Contact', to: '/contact' },
]
