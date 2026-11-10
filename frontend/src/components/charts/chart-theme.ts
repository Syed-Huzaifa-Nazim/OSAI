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
  categorical: ['#FBB02D', '#038666', '#70C9A7', '#EBF2FA'],
  sequential: ['#123d2c', '#1a6247', '#038666', '#47b997', '#a1e2ca'],
  status: { good: '#70C9A7', warning: '#FBB02D', critical: '#f07167' },
  surface: '#10271d',
  grid: 'rgba(235, 242, 250, 0.14)',
  axis: 'rgba(235, 242, 250, 0.28)',
  text: '#EBF2FA',
  textMuted: '#a1c0b2',
}

const LIGHT: ChartTheme = {
  categorical: ['#FBB02D', '#038666', '#184322', '#5c8f7a'],
  sequential: ['#d8f0e7', '#a2d6c3', '#55b998', '#038666', '#184322'],
  status: { good: '#184322', warning: '#c17e00', critical: '#b23c2b' },
  surface: '#ffffff',
  grid: 'rgba(8, 28, 21, 0.12)',
  axis: 'rgba(8, 28, 21, 0.28)',
  text: '#081C15',
  textMuted: '#4e6d60',
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
