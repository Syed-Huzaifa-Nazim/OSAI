import { Globe, Instagram, PlayCircle, ShoppingBag, Store, Users, type LucideIcon } from 'lucide-react'
import type { Project } from '@/types/domain'

/** The platform a project belongs to, for grouping lists: Instagram, Daraz, Alibaba, other shops, other social
 *  platforms, websites and the sample project. */
export type PlatformKey = 'instagram' | 'daraz' | 'alibaba' | 'shop' | 'social' | 'website' | 'demo'

export interface PlatformInfo {
  key: PlatformKey
  label: string
  icon: LucideIcon
  /** Icon colours (background + text). */
  tone: string
  /** The platform's own logo (same files as the new-project page); the icon is used when there is none. */
  logo?: string
}

const INFO: Record<PlatformKey, Omit<PlatformInfo, 'key'>> = {
  instagram: { label: 'Instagram', icon: Instagram, tone: 'bg-primary/10 text-primary', logo: '/hero/instagram.png' },
  daraz: { label: 'Daraz', icon: ShoppingBag, tone: 'bg-warning/15 text-warning-ink', logo: '/hero/daraz-mark.png' },
  alibaba: { label: 'Alibaba', icon: Store, tone: 'bg-warning/15 text-warning-ink', logo: '/hero/alibaba-mark.png' },
  shop: { label: 'Other marketplaces', icon: Store, tone: 'bg-warning/15 text-warning-ink' },
  social: { label: 'Other social media', icon: Users, tone: 'bg-primary/10 text-primary' },
  website: { label: 'Websites', icon: Globe, tone: 'bg-success/10 text-success' },
  demo: { label: 'Sample project', icon: PlayCircle, tone: 'bg-muted text-muted-foreground' },
}

/** The order the groups are shown in. */
const ORDER: PlatformKey[] = ['instagram', 'daraz', 'alibaba', 'shop', 'social', 'website', 'demo']

export function platformOf(
  project: Pick<Project, 'isDemo' | 'comparisonType' | 'socialPlatform' | 'ecommercePlatform'>,
): PlatformKey {
  if (project.isDemo) return 'demo'
  if (project.comparisonType === 'social_media') {
    return project.socialPlatform === 'instagram' ? 'instagram' : 'social'
  }
  if (project.comparisonType === 'ecommerce_product') {
    if (project.ecommercePlatform === 'daraz') return 'daraz'
    if (project.ecommercePlatform === 'alibaba') return 'alibaba'
    return 'shop'
  }
  return 'website'
}

export function platformInfo(key: PlatformKey): PlatformInfo {
  return { key, ...INFO[key] }
}

/** Projects grouped by platform, in a fixed order; empty groups are left out. The order inside a group is kept. */
export function groupByPlatform<T extends Project>(projects: T[]): (PlatformInfo & { projects: T[] })[] {
  return ORDER.map((key) => ({ ...platformInfo(key), projects: projects.filter((p) => platformOf(p) === key) })).filter(
    (group) => group.projects.length > 0,
  )
}
