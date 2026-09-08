import type { Transition, Variants } from 'framer-motion'

/**
 * Shared motion vocabulary. Springs, not linear easing, every transition in
 * the app pulls from here so the product moves consistently.
 */

export const spring: Transition = { type: 'spring', stiffness: 260, damping: 30, mass: 0.9 }
export const springSoft: Transition = { type: 'spring', stiffness: 180, damping: 26 }
export const springSnappy: Transition = { type: 'spring', stiffness: 420, damping: 34 }

/** Page-level enter/exit, used by the route transition wrapper. */
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { ...spring, staggerChildren: 0.05 } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.18 } },
}

/** Parent of a list that should reveal its children in sequence. */
export const staggerContainer: Variants = {
  initial: {},
  animate: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
}

export const staggerItem: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: spring },
}

export const fadeIn: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.3 } },
}

export const scaleIn: Variants = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: spring },
}

/** Scroll-linked reveal used across the marketing pages. */
export const revealOnScroll: Variants = {
  initial: { opacity: 0, y: 28 },
  whileInView: { opacity: 1, y: 0, transition: springSoft },
}

export const viewportOnce = { once: true, margin: '-80px' } as const

/**
 * Collapses any variant set to opacity-only when the user prefers reduced
 * motion. Never returns "no animation at all". An element that fades is
 * still comprehensible; one that never appears is a bug.
 */
export function reduceVariants(variants: Variants, reduced: boolean): Variants {
  if (!reduced) return variants
  return Object.fromEntries(
    Object.entries(variants).map(([key, value]) => {
      const target = value as Record<string, unknown>
      return [key, { opacity: target.opacity ?? 1, transition: { duration: 0.15 } }]
    }),
  ) as Variants
}
