import type { Gap } from '@/types/domain'

/** The category buttons on the review page. Every gap belongs to exactly one. */
export type GapCategory =
  | 'format'
  | 'schedule'
  | 'captions'
  | 'photos'
  | 'reels'
  | 'weak'
  | 'profile'
  /** Daraz listings */
  | 'price'
  | 'title'
  | 'listing_photos'
  | 'details'
  | 'reviews'

export const GAP_CATEGORIES: {
  key: GapCategory
  label: string
  hint: string
}[] = [
  {
    key: 'format',
    label: 'Content format',
    hint: 'Reels, photos or carousels',
  },
  { key: 'schedule', label: 'Posting schedule', hint: 'When and how often' },
  {
    key: 'captions',
    label: 'Captions & hashtags',
    hint: 'What the captions say',
  },
  { key: 'photos', label: 'Photos & visuals', hint: 'How the pictures look' },
  { key: 'reels', label: 'Reels', hint: 'Openings, editing and reach' },
  { key: 'weak', label: 'Your weak spots', hint: 'Measured on your own posts' },
  { key: 'profile', label: 'Profile', hint: 'Your Instagram profile' },
]

/** The category buttons for a Daraz listing comparison. */
export const DARAZ_CATEGORIES: typeof GAP_CATEGORIES = [
  { key: 'price', label: 'Price & offers', hint: 'Price, discount and Daraz badges' },
  { key: 'title', label: 'Title & search words', hint: 'The words buyers search for' },
  { key: 'listing_photos', label: 'Photos', hint: 'How many photos and what they show' },
  { key: 'details', label: 'Listing details', hint: 'Description and options' },
  { key: 'reviews', label: 'What customers say', hint: 'Read from the reviews' },
]

export function isDarazGap(gap: Gap): boolean {
  return (gap.details?.kind ?? '').startsWith('daraz_')
}

/** Daraz projects get the Daraz categories, everything else the Instagram ones. */
export function categoriesFor(gaps: Gap[]): typeof GAP_CATEGORIES {
  return gaps.some(isDarazGap) ? DARAZ_CATEGORIES : GAP_CATEGORIES
}

/** A picture/video score gap is about reels or videos when its title says so. */
function isAboutVideo(gap: Gap): boolean {
  return /\b(reels?|videos?)\b/i.test(gap.title)
}

/** Media gaps measured only on the seller's own posts have no competitor value. */
function isOwnOnly(gap: Gap): boolean {
  const first = gap.details?.numbers?.[0]
  return first !== undefined && first.competitor === null
}

export function categoryOf(gap: Gap): GapCategory {
  switch (gap.details?.kind) {
    case 'daraz_price':
    case 'daraz_offer':
      return 'price'
    case 'daraz_title':
      return 'title'
    case 'daraz_photos':
      return 'listing_photos'
    case 'daraz_content':
      return 'details'
    case 'daraz_reviews':
      return 'reviews'
    case 'format':
      return 'format'
    case 'timing':
      return 'schedule'
    case 'caption':
    case 'topic':
    case 'hashtag':
      return 'captions'
    case 'picture':
      return 'photos'
    case 'reel':
    case 'reach':
      return 'reels'
    case 'media':
      if (isOwnOnly(gap)) return 'weak'
      return isAboutVideo(gap) ? 'reels' : 'photos'
    case 'weakness':
      return 'weak'
    case 'profile':
    case 'habit':
      return 'profile'
    default:
      return 'format'
  }
}

export function groupByCategory(gaps: Gap[]): Record<GapCategory, Gap[]> {
  const out = Object.fromEntries(
    [...GAP_CATEGORIES, ...DARAZ_CATEGORIES].map((c) => [c.key, [] as Gap[]]),
  ) as Record<GapCategory, Gap[]>
  for (const gap of gaps) out[categoryOf(gap)].push(gap)
  return out
}
