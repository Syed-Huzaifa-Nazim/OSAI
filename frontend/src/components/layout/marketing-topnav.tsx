import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { motion, useScroll, useSpring } from 'framer-motion'
import { ArrowUpRight, Menu, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/shared/logo'
import { ThemeToggle } from '@/components/shared/theme-toggle'
import { useAuthStore } from '@/stores/auth-store'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { cn } from '@/lib/utils'
import { spring, springSnappy } from '@/lib/motion'
import { MARKETING_NAV } from './nav-config'

/**
 * Variant A of the public navigation: a top bar.
 *
 * Two things carry it. At the top of a page the bar is full width and
 * transparent, and once you scroll it contracts into a floating glass pill, so
 * the chrome gets out of the way of the hero and then earns its keep. The
 * active link sits under a honey pill that slides between entries, which is the
 * horizontal counterpart of the marker on the vertical rail.
 *
 * The mobile menu is a full-screen numbered index rather than a dropdown,
 * matching the rail's typography so the two variants read as one brand.
 */
export function MarketingTopNav() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [menuMounted, setMenuMounted] = useState(false)
  const user = useAuthStore((state) => state.user)
  const reduced = usePrefersReducedMotion()
  const { pathname } = useLocation()

  const { scrollYProgress } = useScroll()
  const progress = useSpring(scrollYProgress, { stiffness: 220, damping: 40, mass: 0.4 })

  useEffect(() => {
    const onScroll = (): void => {
      setScrolled(window.scrollY > 24)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  // Close on route change rather than in each link's onClick. Closing during
  // the click is lost inside the router navigation the same tap starts, which
  // leaves the overlay mounted with its links still focusable.
  useEffect(() => {
    setMenuOpen(false)
  }, [pathname])

  // Mount on open; the exit animation completing is what unmounts it.
  useEffect(() => {
    if (menuOpen) setMenuMounted(true)
  }, [menuOpen])

  // A full-screen menu over a scrollable page is disorienting, so hold the
  // page still while it is open.
  useEffect(() => {
    if (!menuOpen) return undefined
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [menuOpen])

  return (
    <>
      <header className="sticky top-0 z-40 px-4 pt-0">
        {/* Reading position, as a hairline across the very top. */}
        <motion.div
          aria-hidden="true"
          style={{ scaleX: progress }}
          className="fixed inset-x-0 top-0 z-50 h-[2px] origin-left bg-gradient-to-r from-primary via-primary/60 to-primary"
        />

        <div
          className={cn(
            'mx-auto flex items-center gap-6 transition-all duration-300 ease-out',
            scrolled
              ? 'glass mt-3 h-14 max-w-6xl rounded-full px-5 shadow-glass-lg'
              : 'mt-0 h-16 max-w-none rounded-none border-transparent bg-transparent px-2 shadow-none',
          )}
        >
          <Link
            to="/"
            className="shrink-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Logo />
          </Link>

          <nav className="hidden flex-1 items-center justify-center lg:flex" aria-label="Main">
            <ul className="flex items-center gap-1">
              {MARKETING_NAV.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className="relative block rounded-full px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {({ isActive }) => (
                      <>
                        {isActive ? (
                          <motion.span
                            layoutId="topnav-active"
                            transition={reduced ? { duration: 0 } : springSnappy}
                            aria-hidden="true"
                            className="absolute inset-0 rounded-full bg-primary/15 ring-1 ring-inset ring-primary/25"
                          />
                        ) : null}
                        <span
                          className={cn(
                            'relative',
                            isActive
                              ? 'text-primary'
                              : 'text-muted-foreground hover:text-foreground',
                          )}
                        >
                          {item.label}
                        </span>
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-2 lg:ml-0">
            <ThemeToggle />
            {user ? (
              <Button asChild size="sm" className="group">
                <Link to="/app/dashboard">
                  Open app
                  <ArrowUpRight className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
                  <Link to="/login">Log in</Link>
                </Button>
                <Button asChild size="sm" className="group">
                  <Link to="/signup">
                    Get started
                    <ArrowUpRight className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
                  </Link>
                </Button>
              </>
            )}
            <Button
              variant="ghost"
              size="icon-sm"
              className="lg:hidden"
              onClick={() => {
                setMenuOpen(true)
              }}
              aria-label="Open menu"
              aria-expanded={menuOpen}
            >
              <Menu />
            </Button>
          </div>
        </div>
      </header>

      {/* Full-screen numbered index, the mobile counterpart of the rail. */}
      {menuMounted ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: menuOpen ? 1 : 0 }}
          transition={reduced ? { duration: 0 } : { duration: 0.22 }}
          onAnimationComplete={() => {
            if (!menuOpen) setMenuMounted(false)
          }}
          className="glass-strong fixed inset-0 z-50 flex flex-col rounded-none lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation"
        >
          <div className="flex h-16 shrink-0 items-center justify-between px-5">
            <Logo />
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => {
                setMenuOpen(false)
              }}
              aria-label="Close menu"
            >
              <X />
            </Button>
          </div>

          <nav className="flex-1 overflow-y-auto px-5 py-6" aria-label="Mobile">
            <p className="mb-5 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground/60">
              Index
            </p>
            <ul className="space-y-1">
              {[{ label: 'Home', to: '/' }, ...MARKETING_NAV].map((item, index) => (
                <motion.li
                  key={item.to}
                  initial={reduced ? false : { opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ ...spring, delay: reduced ? 0 : 0.04 * index }}
                >
                  <NavLink
                    to={item.to}
                    end={item.to === '/'}
                    className="flex items-baseline gap-4 rounded-lg py-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {({ isActive }) => (
                      <>
                        <span
                          aria-hidden="true"
                          className={cn(
                            'w-6 shrink-0 font-mono text-[11px] tabular-nums',
                            isActive ? 'text-primary' : 'text-muted-foreground/45',
                          )}
                        >
                          {String(index + 1).padStart(2, '0')}
                        </span>
                        <span
                          className={cn(
                            'font-display text-2xl font-semibold tracking-tight',
                            isActive ? 'text-primary' : 'text-foreground',
                          )}
                        >
                          {item.label}
                        </span>
                        {isActive ? (
                          <ArrowUpRight
                            aria-hidden="true"
                            className="ml-auto size-4 self-center text-primary"
                          />
                        ) : null}
                      </>
                    )}
                  </NavLink>
                </motion.li>
              ))}
            </ul>
          </nav>

          <div className="shrink-0 space-y-2 border-t border-border/15 px-5 pb-8 pt-5">
            <p className="mb-4 border-l-2 border-primary/40 pl-3.5 font-display text-[13px] font-medium leading-snug text-foreground/85">
              Nine stages.
              <br />
              Two of them are yours.
            </p>
            {user ? (
              <Button asChild size="lg" className="w-full justify-between">
                <Link to="/app/dashboard">
                  Open app
                  <ArrowUpRight />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild size="lg" className="w-full justify-between">
                  <Link to="/signup">
                    Get started
                    <ArrowUpRight />
                  </Link>
                </Button>
                <Button asChild variant="ghost" size="sm" className="w-full">
                  <Link to="/login">Log in</Link>
                </Button>
              </>
            )}
          </div>
        </motion.div>
      ) : null}
    </>
  )
}
