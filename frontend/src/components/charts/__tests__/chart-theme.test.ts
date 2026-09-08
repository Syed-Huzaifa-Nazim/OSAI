import { describe, expect, it } from 'vitest'
import { sequentialStep } from '@/components/charts/chart-theme'
import type { ChartTheme } from '@/components/charts/chart-theme'

const THEME = {
  sequential: ['#111111', '#333333', '#555555', '#777777', '#999999'],
} as unknown as ChartTheme

describe('sequentialStep', () => {
  it('maps the ends of the scale to the ends of the ramp', () => {
    expect(sequentialStep(THEME, 0, 5)).toBe('#111111')
    expect(sequentialStep(THEME, 4, 5)).toBe('#999999')
  })

  it('interpolates positions in between', () => {
    expect(sequentialStep(THEME, 2, 5)).toBe('#555555')
  })

  it('handles a single-item scale without dividing by zero', () => {
    expect(sequentialStep(THEME, 0, 1)).toBe('#555555')
  })

  it('clamps an out-of-range index rather than returning undefined', () => {
    // Reading past the ramp would hand an undefined fill to Recharts, which
    // renders an invisible mark instead of failing loudly.
    expect(sequentialStep(THEME, 99, 5)).toBe('#999999')
    expect(sequentialStep(THEME, -3, 5)).toBe('#111111')
  })
})
