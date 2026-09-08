import { describe, expect, it } from 'vitest'
import {
  cn,
  formatCompactNumber,
  formatDate,
  formatDuration,
  formatPercent,
  formatUsd,
  initials,
  prettyUrl,
  titleCase,
  truncate,
} from '@/lib/utils'

describe('cn', () => {
  it('merges conflicting tailwind classes, last one winning', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
  })

  it('drops falsy values', () => {
    expect(cn('a', false && 'b', undefined, 'c')).toBe('a c')
  })
})

describe('formatters', () => {
  it('formats durations across the unit boundaries', () => {
    expect(formatDuration(420)).toBe('420ms')
    expect(formatDuration(4200)).toBe('4.2s')
    expect(formatDuration(125_000)).toBe('2m 5s')
  })

  it('formats small costs with more precision than large ones', () => {
    // Sub-dollar run costs are the common case, and rounding them to cents
    // would show most stages as $0.00.
    expect(formatUsd(0.421)).toBe('$0.421')
    expect(formatUsd(12.5)).toBe('$12.50')
  })

  it('formats compact numbers', () => {
    expect(formatCompactNumber(1200)).toBe('1.2K')
    expect(formatCompactNumber(184_260)).toBe('184.3K')
  })

  it('formats confidence as a whole percentage', () => {
    expect(formatPercent(0.91)).toBe('91%')
    expect(formatPercent(1)).toBe('100%')
  })

  it('returns an em dash for an unparseable date rather than throwing', () => {
    expect(formatDate('not-a-date')).toBe('-')
  })
})

describe('text helpers', () => {
  it('builds initials from at most two words', () => {
    expect(initials('Syed Huzaifa Nazim')).toBe('SH')
    expect(initials('Hadia')).toBe('H')
    expect(initials('')).toBe('')
  })

  it('strips protocol and trailing slash for display', () => {
    expect(prettyUrl('https://verdantroast.example/')).toBe('verdantroast.example')
    expect(prettyUrl('http://a.com/path')).toBe('a.com/path')
  })

  it('truncates only when over the limit', () => {
    expect(truncate('short', 10)).toBe('short')
    expect(truncate('a much longer string', 10)).toBe('a much lo…')
  })

  it('title-cases snake and kebab case', () => {
    expect(titleCase('social_engagement')).toBe('Social Engagement')
    expect(titleCase('review-gaps')).toBe('Review Gaps')
  })
})
