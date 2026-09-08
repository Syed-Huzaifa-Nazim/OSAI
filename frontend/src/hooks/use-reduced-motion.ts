import { useReducedMotion as useFramerReducedMotion } from 'framer-motion'

/**
 * Single source of truth for motion preference. Components import this rather
 * than framer's hook directly, so the policy can change in one place.
 */
export function usePrefersReducedMotion(): boolean {
  return useFramerReducedMotion() ?? false
}
