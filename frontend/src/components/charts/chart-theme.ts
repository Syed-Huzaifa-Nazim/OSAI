import { useThemeStore } from '@/stores/theme-store'

/**
 * Chart colour, kept separate from the UI tokens on purpose.
 *
 * Recharts writes SVG presentation attributes, which do not resolve `var()`,
 * so charts need concrete hex values rather than the CSS variables the rest of
 * the app uses. Every value below was checked with the dataviz validator
 * (lightness band, chroma floor, CVD separation under protanopia/deuteranopia,
 * normal-vision floor, and contrast against the mode's own surface) and each
 * mode passes all six checks on its own steps. Dark is not a flipped light.
 *
 *   dark  surface #17152A · light surface #FFFFFF (Violet theme)
 *
 * The categorical order is fixed and assigned in sequence, never cycled. Slot 1
 * is always the user's own brand, so the violet accent means "you" in every
 * comparison. Four slots is the ceiling: a fifth series folds into "Other".
 */

export interface ChartTheme {
  /** Fixed-order identity hues. Slot 0 is always the user's own brand. */
  categorical: readonly [string, string, string, string]
  /** Single-hue magnitude ramp, low -> high. */
  sequential: readonly [string, string, string, string, string]
  /** Reserved state colours: never reused as a series. */
  status: { good: string; warning: string; critical: string }
  /** Chart surface, used for the 2px gaps between adjoining marks. */
  surface: string
  grid: string
  axis: string
  text: string
  textMuted: string
}

const DARK: ChartTheme = {
  categorical: ['#8b73ff', '#5aa2f0', '#3fbf7a', '#f8c81c'],
  sequential: ['#2e2766', '#463a9c', '#6150d1', '#7b61ff', '#a594ff'],
  status: { good: '#3fbf7a', warning: '#f8c81c', critical: '#f0606e' },
  surface: '#17152a',
  grid: 'rgba(165, 148, 255, 0.14)',
  axis: 'rgba(165, 148, 255, 0.28)',
  text: '#f2efff',
  textMuted: '#a9a5c7',
}

const LIGHT: ChartTheme = {
  categorical: ['#5b3be6', '#2967ae', '#1f7f4f', '#a37800'],
  sequential: ['#ddd6fe', '#c4b5fd', '#a78bfa', '#7c5cf0', '#5b3be6'],
  status: { good: '#1f7f4f', warning: '#a37800', critical: '#c8283c' },
  surface: '#ffffff',
  grid: 'rgba(91, 59, 230, 0.10)',
  axis: 'rgba(70, 60, 120, 0.30)',
  text: '#13112b',
  textMuted: '#5b5878',
}

export function useChartTheme(): ChartTheme {
  const resolved = useThemeStore((state) => state.resolved)
  return resolved === 'dark' ? DARK : LIGHT
}

/**
 * Picks a step from the sequential ramp for a value in an ordered scale.
 * Used for priority (low -> critical), never for identity.
 */
export function sequentialStep(theme: ChartTheme, index: number, total: number): string {
  if (total <= 1) return theme.sequential[2] as string
  const position = Math.round((index / (total - 1)) * (theme.sequential.length - 1))
  return theme.sequential[Math.min(theme.sequential.length - 1, Math.max(0, position))] as string
}
