import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { useUiStore } from '@/stores/ui-store'
import { ErrorBoundary } from '@/components/shared/error-boundary'
import { RouteFallback } from '@/components/shared/route-fallback'
import { AppSidebar, SIDEBAR_WIDTHS } from './app-sidebar'
import { AppTopbar } from './app-topbar'

/** Authenticated shell: fixed left rail and sticky topbar. */
export function AppShell() {
  const expanded = useUiStore((state) => state.sidebarExpanded)

  return (
    <div className="canvas-grain min-h-screen bg-background">
      <AppSidebar />
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
            {/* Keep the shell visible while lazy pages load. Page-level motion
             * belongs inside each page; the route wrapper must never be able
             * to leave the entire content area at opacity: 0. */}
            <Suspense fallback={<RouteFallback />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
