import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowUpRight, LogIn, Menu, Sparkles, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/shared/logo'
import { ThemeToggle } from '@/components/shared/theme-toggle'
import { useAuthStore } from '@/stores/auth-store'
import { useUiStore } from '@/stores/ui-store'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { cn } from '@/lib/utils'
import { spring, springSnappy } from '@/lib/motion'
import { MARKETING_NAV } from './nav-config'

/** Rail width. Exported so the shell reserves exactly this much. */
export const MARKETING_RAIL_WIDTH = 288

const ITEMS: { label: string; to: string; end: boolean }[] = [
  { label: 'Home', to: '/', end: true },
  ...MARKETING_NAV.map((item) => ({ ...item, end: false })),
]

/**
 * Variant B of the public navigation: a left vertical rail.
 *
 * Deliberately editorial rather than app-like, a numbered index in display
 * type, one honey marker that slides between entries, and a rotated wordmark
 * down the edge. The rail is a piece of the brand, not a utility strip; if it
 * looked like the app's sidebar there would be no reason to offer it as an
 * alternative to the top bar.
 */
export function MarketingSideNav() {
  const user = useAuthStore((state) => state.user)
  const mobileOpen = useUiStore((state) => state.mobileNavOpen)
  const setMobileOpen = useUiStore((state) => state.setMobileNavOpen)
  const reduced = usePrefersReducedMotion()
  const { pathname } = useLocation()
  const [drawerMounted, setDrawerMounted] = useState(false)

  const close = (): void => {
    setMobileOpen(false)
  }

  /*
   * Close the drawer when the route changes, rather than in each link's
   * onClick.
   *
   * Closing during the click does update the state, the exit animation runs, * but the removal never completes, because the same click also starts a
   * router navigation and AnimatePresence loses the element inside that
   * transition. The drawer then sits off-screen at translateX(-100%) with its
   * links still focusable, permanently.
   *
   * Running it from an effect means the close is an ordinary post-commit
   * update, which behaves exactly like the X button (which always worked).
   */
  useEffect(() => {
    setMobileOpen(false)
  }, [pathname, setMobileOpen])

  // Mount on open; unmounting is handled by the exit animation completing.
  useEffect(() => {
    if (mobileOpen) setDrawerMounted(true)
  }, [mobileOpen])

  /**
   * `instance` scopes the shared-layout id. The desktop rail and the mobile
   * drawer can both be mounted at once, and a single layoutId across the two
   * would make the marker fly between them.
   */
  const body = (instance: 'desktop' | 'mobile') => {
    const mobile = instance === 'mobile'

    return (
      <div className="relative flex h-full flex-col overflow-hidden">
        {/* Warm bloom behind the top of the rail. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-gradient-to-b from-primary/[0.13] via-primary/[0.04] to-transparent"
        />

        {/* ------------------------------------------------------- header */}
        <div className="relative flex h-20 shrink-0 items-center justify-between px-6">
          <Link
            to="/"
            className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Logo className="[&_svg]:size-8 [&_span]:text-[17px]" />
          </Link>
          {mobile ? (
            <Button variant="ghost" size="icon-sm" onClick={close} aria-label="Close menu">
              <X />
            </Button>
          ) : null}
        </div>

        <div className="relative mx-6 h-px shrink-0 bg-gradient-to-r from-primary/50 via-border/20 to-transparent" />

        {/* --------------------------------------------------------- nav */}
        <nav
          className="no-scrollbar relative flex flex-1 flex-col overflow-y-auto px-3 py-6"
          aria-label="Main"
        >
          <p className="mb-4 px-3 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground/60">
            Index
          </p>

          <ul className="space-y-0.5">
            {ITEMS.map((item, index) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                        className="group relative flex items-baseline gap-4 rounded-lg px-3 py-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {({ isActive }) => (
                    <>
                      {isActive ? (
                        <>
                          <motion.span
                            layoutId={`${instance}-rail-fill`}
                            transition={reduced ? { duration: 0 } : springSnappy}
                            aria-hidden="true"
                            className="absolute inset-0 rounded-lg bg-gradient-to-r from-primary/[0.16] to-transparent"
                          />
                          <motion.span
                            layoutId={`${instance}-rail-bar`}
                            transition={reduced ? { duration: 0 } : springSnappy}
                            aria-hidden="true"
                            className="absolute left-0 top-1/2 h-7 w-[3px] -translate-y-1/2 rounded-full bg-primary shadow-[0_0_12px_hsl(var(--primary)/0.7)]"
                          />
                        </>
                      ) : null}

                      <span
                        aria-hidden="true"
                        className={cn(
                          'relative w-6 shrink-0 font-mono text-[11px] tabular-nums transition-colors',
                          isActive
                            ? 'text-primary'
                            : 'text-muted-foreground/45 group-hover:text-primary/70',
                        )}
                      >
                        {String(index + 1).padStart(2, '0')}
                      </span>

                      <span
                        className={cn(
                          'relative font-display text-xl font-semibold leading-tight tracking-tight transition-all duration-200',
                          isActive
                            ? 'text-foreground'
                            : 'text-muted-foreground group-hover:translate-x-1 group-hover:text-foreground',
                        )}
                      >
                        {item.label}
                      </span>

                      <ArrowUpRight
                        aria-hidden="true"
                        className={cn(
                          'relative ml-auto size-4 self-center transition-all duration-200',
                          isActive
                            ? 'text-primary opacity-100'
                            : '-translate-x-1 text-primary opacity-0 group-hover:translate-x-0 group-hover:opacity-100',
                        )}
                      />
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>

          {/*
           * Rotated wordmark, parked in whatever space the index leaves over.
           * Sitting in the flex remainder rather than pinned to the edge means
           * it fills the gap instead of crowding the footer, and it collapses
           * on its own when the viewport is short.
           */}
          <div
            aria-hidden="true"
            className="pointer-events-none hidden min-h-0 flex-1 items-center justify-end pr-2 pt-8 lg:flex"
          >
            <span
              className="select-none font-mono text-[10px] uppercase tracking-[0.42em] text-muted-foreground/30"
              style={{ writingMode: 'vertical-rl' }}
            >
              Human-in-the-loop
            </span>
          </div>
        </nav>

        {/* ------------------------------------------------------- footer */}
        <div className="relative shrink-0 px-6 pb-6">
          <div className="mb-5 border-l-2 border-primary/40 pl-3.5">
            <p className="font-display text-[13px] font-medium leading-snug text-foreground/85">
              Nine stages.
              <br />
              Two of them are yours.
            </p>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/60">
              Human-validated
            </p>
          </div>

          <div className="space-y-2">
            {user ? (
              <Button asChild size="lg" className="w-full justify-between">
                <Link to="/app/dashboard">
                  <span className="flex items-center gap-2">
                    <Sparkles />
                    Open app
                  </span>
                  <ArrowUpRight />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild size="lg" className="w-full justify-between">
                  <Link to="/signup">
                    <span className="flex items-center gap-2">
                      <Sparkles />
                      Get started
                    </span>
                    <ArrowUpRight />
                  </Link>
                </Button>
                <Button asChild variant="ghost" size="sm" className="w-full">
                  <Link to="/login">
                    <LogIn />
                    Log in
                  </Link>
                </Button>
              </>
            )}
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-border/15 pt-4">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/50">
              Theme
            </span>
            <ThemeToggle />
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <aside
        className="glass fixed inset-y-0 left-0 z-40 hidden rounded-none border-y-0 border-l-0 lg:block"
        style={{ width: MARKETING_RAIL_WIDTH }}
      >
        {body('desktop')}
      </aside>

      {/* Mobile: a compact bar that opens the same rail as a drawer. */}
      <header className="glass sticky top-0 z-40 flex h-16 items-center gap-3 rounded-none border-x-0 border-t-0 px-4 lg:hidden">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => {
            setMobileOpen(true)
          }}
          aria-label="Open navigation"
        >
          <Menu />
        </Button>
        <Link to="/" className="flex-1">
          <Logo />
        </Link>
        <ThemeToggle />
      </header>

      {/*
       * The drawer manages its own mount rather than using AnimatePresence.
       *
       * AnimatePresence removes an exiting child via an internal state update.
       * When the same interaction also starts a router navigation, that update
       * is lost inside the navigation transition: the exit animation runs to
       * completion but the node is never removed. The result was a
       * role="dialog" holding eleven focusable links parked at
       * translateX(-100%): invisible, still tabbable, and permanent. Closing
       * with the X button worked, because no navigation was involved.
       *
       * Driving `animate` off `mobileOpen` and unmounting in
       * onAnimationComplete keeps the slide-out and puts removal somewhere it
       * cannot be swallowed.
       */}
      {drawerMounted ? (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: mobileOpen ? 1 : 0 }}
            transition={{ duration: 0.2 }}
            onClick={close}
            className="fixed inset-0 z-40 bg-brand-ink-black/70 backdrop-blur-sm lg:hidden"
            aria-hidden="true"
          />
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: mobileOpen ? 0 : '-100%' }}
            transition={reduced ? { duration: 0 } : spring}
            onAnimationComplete={() => {
              if (!mobileOpen) setDrawerMounted(false)
            }}
            className="glass-strong fixed inset-y-0 left-0 z-50 w-[292px] rounded-none border-y-0 border-l-0 lg:hidden"
            role="dialog"
            aria-label="Navigation"
          >
            {body('mobile')}
          </motion.aside>
        </>
      ) : null}
    </>
  )
}
