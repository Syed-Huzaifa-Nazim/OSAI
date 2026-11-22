import { Suspense } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useUiStore } from '@/stores/ui-store'
import { ErrorBoundary } from '@/components/shared/error-boundary'
import { RouteFallback } from '@/components/shared/route-fallback'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { pageVariants, reduceVariants } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { MarketingTopNav } from './marketing-topnav'
import { MarketingSideNav, MARKETING_RAIL_WIDTH } from './marketing-sidenav'
import { MarketingFooter } from './marketing-footer'
import { NavVariantSwitcher } from './nav-variant-switcher'

/**
 * Public site shell. Renders whichever navigation variant is selected. Both
 * were built so the two can be compared directly (see NavVariantSwitcher).
 */
export function MarketingShell() {
  const variant = useUiStore((state) => state.marketingNav)
  const location = useLocation()
  const reduced = usePrefersReducedMotion()
  const vertical = variant === 'vertical'

  return (
    <div className="canvas-grain min-h-screen bg-background">
      {vertical ? <MarketingSideNav /> : <MarketingTopNav />}

      <div
        className={cn('relative z-10', vertical && 'lg:pl-[var(--rail-w)]')}
        style={vertical ? ({ '--rail-w': `${MARKETING_RAIL_WIDTH}px` } as React.CSSProperties) : undefined}
      >
        <ErrorBoundary>
          {/*
           * Suspense sits ABOVE AnimatePresence, not inside it.
           *
           * With the boundary inside, a lazily-loaded page mounts into the
           * transition while its chunk is still in flight, and the enter
           * animation can start against a subtree React has suspended. Hoisting
           * it means the chunk resolves first, then the page animates in with
           * something real to show.
           *
           * This ordering has not been observed to fail here, it survived a
           * browser check with 400ms artificial latency on every module, but
           * it is the ordering that stays correct as chunks get slower, so it
           * is the one worth keeping.
           */}
          <Suspense fallback={<RouteFallback />}>
            <AnimatePresence mode="wait">
              <motion.main
                key={location.pathname}
                variants={reduceVariants(pageVariants, reduced)}
                initial="initial"
                animate="animate"
                exit="exit"
              >
                <Outlet />
              </motion.main>
            </AnimatePresence>
          </Suspense>
        </ErrorBoundary>
        <MarketingFooter />
      </div>

      {import.meta.env.VITE_SHOW_NAV_SWITCH === 'true' ? <NavVariantSwitcher /> : null}
    </div>
  )
}
