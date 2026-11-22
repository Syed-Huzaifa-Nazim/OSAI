import { Suspense } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useUiStore } from '@/stores/ui-store'
import { ErrorBoundary } from '@/components/shared/error-boundary'
import { RouteFallback } from '@/components/shared/route-fallback'
import { BackgroundJobs } from '@/components/shared/background-jobs'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { pageVariants, reduceVariants } from '@/lib/motion'
import { AppSidebar, SIDEBAR_WIDTHS } from './app-sidebar'
import { AppTopbar } from './app-topbar'

/** Authenticated shell: fixed left rail, sticky topbar, animated page slot. */
export function AppShell() {
  const expanded = useUiStore((state) => state.sidebarExpanded)
  const location = useLocation()
  const reduced = usePrefersReducedMotion()

  return (
    <div className="canvas-grain min-h-screen bg-background">
      <AppSidebar />
      {/* Scraping and gap analysis keep running on the server; this follows them from every page. */}
      <BackgroundJobs />
      <div
        className="relative z-10 transition-[padding] duration-300 ease-out md:pl-[var(--sidebar-w)]"
        style={
          {
            '--sidebar-w': `${expanded ? SIDEBAR_WIDTHS.expanded : SIDEBAR_WIDTHS.collapsed}px`,
          } as React.CSSProperties
        }
      >
        <AppTopbar />
        <main className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">
          <ErrorBoundary>
            {/* Suspense above AnimatePresence. See marketing-shell.tsx for why. */}
            <Suspense fallback={<RouteFallback />}>
              <AnimatePresence mode="wait">
                <motion.div
                  key={location.pathname}
                  variants={reduceVariants(pageVariants, reduced)}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                >
                  <Outlet />
                </motion.div>
              </AnimatePresence>
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
