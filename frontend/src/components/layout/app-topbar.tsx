import { Link, useMatches } from 'react-router-dom'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/shared/theme-toggle'
import { DemoBadge } from '@/components/shared/demo-badge'
import { useUiStore } from '@/stores/ui-store'
import { isDemoMode } from '@/lib/config'
import { UserMenu } from './user-menu'

interface RouteHandle {
  crumb?: string
}

/** Floating glass topbar with breadcrumbs, theme control and the account menu. */
export function AppTopbar() {
  const setMobileOpen = useUiStore((state) => state.setMobileNavOpen)
  const matches = useMatches()

  const crumbs = matches
    .map((match) => (match.handle as RouteHandle | undefined)?.crumb)
    .filter((crumb): crumb is string => Boolean(crumb))

  return (
    <header className="glass sticky top-0 z-30 flex h-16 items-center gap-3 rounded-none border-x-0 border-t-0 px-4 sm:px-6">
      <Button
        variant="ghost"
        size="icon-sm"
        className="md:hidden"
        onClick={() => {
          setMobileOpen(true)
        }}
        aria-label="Open navigation"
      >
        <Menu />
      </Button>

      <nav aria-label="Breadcrumb" className="min-w-0 flex-1">
        <ol className="flex items-center gap-2 text-sm">
          <li>
            <Link to="/app/dashboard" className="text-muted-foreground hover:text-foreground">
              App
            </Link>
          </li>
          {crumbs.map((crumb, index) => (
            <li key={`${crumb}-${index}`} className="flex min-w-0 items-center gap-2">
              <span className="text-muted-foreground/50" aria-hidden="true">
                /
              </span>
              <span
                className="truncate"
                aria-current={index === crumbs.length - 1 ? 'page' : undefined}
              >
                {crumb}
              </span>
            </li>
          ))}
        </ol>
      </nav>

      {isDemoMode ? <DemoBadge compact /> : null}
      <ThemeToggle />
      <UserMenu />
    </header>
  )
}
