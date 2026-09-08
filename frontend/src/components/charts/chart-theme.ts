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
 *   dark  surface #121212 · light surface #FFF9EB
 *
 * The categorical order is fixed and assigned in sequence, never cycled. Slot 1
 * is always the user's own brand, so the honey accent means "you" in every
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
  categorical: ['#c17d2a', '#4b8ad2', '#36a05c', '#b17acd'],
  sequential: ['#604524', '#8e6129', '#be7d2d', '#db9643', '#e8af68'],
  status: { good: '#36a05c', warning: '#e8af68', critical: '#cf5341' },
  surface: '#121212',
  grid: 'rgba(168, 159, 148, 0.14)',
  axis: 'rgba(168, 159, 148, 0.28)',
  text: '#f4e9d2',
  textMuted: '#a89f94',
}

const LIGHT: ChartTheme = {
  categorical: ['#af6d1d', '#2967ae', '#257e46', '#914ab5'],
  sequential: ['#ebd8c2', '#dfbc90', '#d69f5c', '#cb822a', '#9e621a'],
  status: { good: '#257e46', warning: '#9e621a', critical: '#b23c2b'},
  surface: '#fff9eb',
  grid: 'rgba(120, 108, 94, 0.16)',
  axis: 'rgba(120, 108, 94, 0.34)',
  text: '#171717',
  textMuted: '#5f584f',
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
