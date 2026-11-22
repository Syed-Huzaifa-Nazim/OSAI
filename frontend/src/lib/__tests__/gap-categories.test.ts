import { describe, expect, it } from 'vitest'
import {
  categoriesFor,
  categoryOf,
  DARAZ_CATEGORIES,
  groupByCategory,
  GAP_CATEGORIES,
} from '@/lib/gap-categories'
import type { Gap, GapDetails } from '@/types/domain'

function gap(kind: GapDetails['kind'], title = 'A gap', numbers?: GapDetails['numbers']): Gap {
  return { id: `${kind}-${title}`, title, details: { kind, numbers } } as unknown as Gap
}

describe('gap categories', () => {
  it('puts every kind of gap in one category button', () => {
    expect(categoryOf(gap('format'))).toBe('format')
    expect(categoryOf(gap('timing'))).toBe('schedule')
    expect(categoryOf(gap('caption'))).toBe('captions')
    expect(categoryOf(gap('hashtag'))).toBe('captions')
    expect(categoryOf(gap('topic'))).toBe('captions')
    expect(categoryOf(gap('picture'))).toBe('photos')
    expect(categoryOf(gap('reel'))).toBe('reels')
    expect(categoryOf(gap('reach'))).toBe('reels')
    expect(categoryOf(gap('weakness'))).toBe('weak')
    expect(categoryOf(gap('profile'))).toBe('profile')
  })

  it('splits picture/video scores into photos, reels and your own weak spots', () => {
    const row = { label: 'x', you: '3.1', competitor: '3.6', typical: null }
    expect(
      categoryOf(gap('media', "Your competitor's photos look better made than yours.", [row])),
    ).toBe('photos')
    expect(
      categoryOf(gap('media', "Your competitor's reels look better made than yours.", [row])),
    ).toBe('reels')
    const own = { label: 'Link', you: 'correlation 0.4', competitor: null, typical: null }
    expect(
      categoryOf(gap('media', 'Your lower-quality photos get fewer likes and comments.', [own])),
    ).toBe('weak')
  })

  it('groups gaps with an empty list for categories that found nothing', () => {
    const groups = groupByCategory([gap('format'), gap('reel'), gap('reel', 'b')])
    expect(Object.keys(groups)).toEqual([...GAP_CATEGORIES, ...DARAZ_CATEGORIES].map((c) => c.key))
    expect(groups.reels).toHaveLength(2)
    expect(groups.profile).toEqual([])
  })

  it('gives Daraz listings their own category buttons', () => {
    expect(categoryOf(gap('daraz_price'))).toBe('price')
    expect(categoryOf(gap('daraz_offer'))).toBe('price')
    expect(categoryOf(gap('daraz_title'))).toBe('title')
    expect(categoryOf(gap('daraz_photos'))).toBe('listing_photos')
    expect(categoryOf(gap('daraz_content'))).toBe('details')
    expect(categoryOf(gap('daraz_reviews'))).toBe('reviews')
    expect(categoriesFor([gap('daraz_price')])).toBe(DARAZ_CATEGORIES)
    expect(categoriesFor([gap('format')])).toBe(GAP_CATEGORIES)
  })
})
