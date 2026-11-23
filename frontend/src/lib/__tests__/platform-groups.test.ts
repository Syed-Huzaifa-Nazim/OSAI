import { describe, expect, it } from 'vitest'
import { groupByPlatform, platformOf } from '../platform-groups'
import type { Project } from '@/types/domain'

const base = {
  isDemo: false,
  comparisonType: 'social_media',
  socialPlatform: 'instagram',
  ecommercePlatform: null,
} as unknown as Project

const p = (id: string, patch: Partial<Project>) => ({ ...base, id, ...patch }) as Project

describe('platform groups', () => {
  it('puts each project under its platform', () => {
    expect(platformOf(p('a', {}))).toBe('instagram')
    expect(platformOf(p('b', { comparisonType: 'ecommerce_product', socialPlatform: null, ecommercePlatform: 'daraz' }))).toBe('daraz')
    expect(platformOf(p('c', { comparisonType: 'ecommerce_product', socialPlatform: null, ecommercePlatform: 'alibaba' }))).toBe('alibaba')
    expect(platformOf(p('d', { comparisonType: 'website', socialPlatform: null }))).toBe('website')
    expect(platformOf(p('e', { isDemo: true, comparisonType: 'website' }))).toBe('demo')
  })

  it('orders the groups Instagram, Daraz, ... and keeps the order inside each group', () => {
    const daraz = { comparisonType: 'ecommerce_product', socialPlatform: null, ecommercePlatform: 'daraz' } as const
    const groups = groupByPlatform([p('d1', daraz), p('i1', {}), p('d2', daraz), p('demo', { isDemo: true })])
    expect(groups.map((g) => g.label)).toEqual(['Instagram', 'Daraz', 'Sample project'])
    expect(groups[1]?.projects.map((x) => x.id)).toEqual(['d1', 'd2'])
  })
})
