import { useEffect, useState } from 'react'
import { Link, useLocation, useMatch } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { PanelLeftClose, PanelLeftOpen, Plus, ShieldCheck, UsersRound, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Logo } from '@/components/shared/logo'
import { useUiStore } from '@/stores/ui-store'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { cn } from '@/lib/utils'
import { spring } from '@/lib/motion'
import { featureNavEntries } from '@/features/registry'
import { useProject } from '@/hooks/use-projects'
import { MAIN_NAV, SETTINGS_NAV, projectNav } from './nav-config'
import { SidebarLink } from './sidebar-link'
import { api } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'

const EXPANDED_WIDTH = 244
const COLLAPSED_WIDTH = 68

/**
 * The primary navigation: a fixed vertical rail on the left edge.
 * Collapsible to icons on desktop; below md it becomes an off-canvas drawer
 * driven by `mobileNavOpen`.
 */
export function AppSidebar() {
  const expanded = useUiStore((state) => state.sidebarExpanded)
  const toggle = useUiStore((state) => state.toggleSidebar)
  const mobileOpen = useUiStore((state) => state.mobileNavOpen)
  const setMobileOpen = useUiStore((state) => state.setMobileNavOpen)
  const { pathname } = useLocation()
  const reduced = usePrefersReducedMotion()
  const [drawerMounted, setDrawerMounted] = useState(false)
  const user = useAuthStore((state) => state.user)
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    let active = true
    setIsAdmin(false)
    if (user?.id) {
      void api.get<{ isAdmin: boolean }>('/admin/me')
        .then((result) => { if (active) setIsAdmin(result.isAdmin) })
        .catch(() => { if (active) setIsAdmin(false) })
    }
    return () => { active = false }
  }, [user?.id])

  // Close on route change, not in each link's onClick. See the note in
  // marketing-sidenav.tsx for why the click-time close does not stick.
  useEffect(() => {
    setMobileOpen(false)
  }, [pathname, setMobileOpen])

  // Mount on open; unmounting happens when the exit animation completes.
  useEffect(() => {
    if (mobileOpen) setDrawerMounted(true)
  }, [mobileOpen])

  // Project workspace nav only appears while a project is open.
  const projectMatch = useMatch('/app/projects/:projectId/*')
  const projectId = projectMatch?.params.projectId
  const showProjectNav = Boolean(projectId && projectId !== 'new')
  const project = useProject(showProjectNav ? projectId : undefined)

  const closeMobile = (): void => {
    setMobileOpen(false)
  }

  const content = (mobile: boolean) => {
    const isExpanded = mobile || expanded
    return (
      <div className="flex h-full flex-col">
        <div
          className={cn(
            'flex h-16 shrink-0 items-center px-4',
            isExpanded ? 'justify-between' : 'justify-center',
          )}
        >
          <Link to="/app/dashboard">
            <Logo markOnly={!isExpanded} />
          </Link>
          {mobile ? (
            <Button variant="ghost" size="icon-sm" onClick={closeMobile} aria-label="Close menu">
              <X />
            </Button>
          ) : null}
        </div>

        <div className={cn('px-3 pb-3', !isExpanded && 'px-2')}>
          <Button asChild className="w-full" size={isExpanded ? 'default' : 'icon'}>
            <Link to="/app/projects/new">
              <Plus />
              {isExpanded ? 'New analysis' : <span className="sr-only">New analysis</span>}
            </Link>
          </Button>
        </div>

        <nav
          className={cn('flex-1 space-y-1 overflow-y-auto px-3 pb-4', !isExpanded && 'px-2')}
          aria-label="Main"
        >
          {MAIN_NAV.map((item) => (
            <SidebarLink
              key={item.to}
              to={item.to}
              label={item.label}
              icon={item.icon}
              expanded={isExpanded}
              end={!item.matchPrefix}
            />
          ))}

          {isAdmin ? (
            <SidebarLink
              to="/app/users"
              label="Users"
              icon={UsersRound}
              expanded={isExpanded}
            />
          ) : null}

          {featureNavEntries('main').map((entry) => (
            <SidebarLink
              key={entry.to}
              to={`/app/${entry.to}`}
              label={entry.label}
              icon={entry.icon}
              expanded={isExpanded}
            />
          ))}

          <AnimatePresence initial={false}>
            {showProjectNav && projectId ? (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={spring}
                className="overflow-hidden"
              >
                <Separator className="my-3" />
                {isExpanded ? (
                  <p className="px-3 pb-1.5 text-[10px] uppercase tracking-wider text-muted-foreground/70">
                    This project
                  </p>
                ) : null}
                <div className="space-y-1">
                  {projectNav(projectId, project.data?.comparisonType, project.data?.isDemo).map((item) => (
                    <SidebarLink
                      key={item.to}
                      to={item.to}
                      label={item.label}
                      icon={item.icon}
                      expanded={isExpanded}
                            />
                  ))}
                  {featureNavEntries('project').map((entry) => (
                    <SidebarLink
                      key={entry.to}
                      to={`/app/projects/${projectId}/${entry.to}`}
                      label={entry.label}
                      icon={entry.icon}
                      expanded={isExpanded}
                            />
                  ))}
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>

          <Separator className="my-3" />
          {isExpanded ? (
            <p className="px-3 pb-1.5 text-[10px] uppercase tracking-wider text-muted-foreground/70">
              Settings
            </p>
          ) : null}
          {SETTINGS_NAV.map((item) => (
            <SidebarLink
              key={item.to}
              to={item.to}
              label={item.label}
              icon={item.icon}
              expanded={isExpanded}
            />
          ))}
          {isAdmin ? (
            <SidebarLink
              to="/admin"
              label="Admin portal"
              icon={ShieldCheck}
              expanded={isExpanded}
            />
          ) : null}
          {featureNavEntries('settings').map((entry) => (
            <SidebarLink
              key={entry.to}
              to={`/app/settings/${entry.to}`}
              label={entry.label}
              icon={entry.icon}
              expanded={isExpanded}
            />
          ))}
        </nav>

        {!mobile ? (
          <div className={cn('shrink-0 border-t border-border/15 p-3', !expanded && 'px-2')}>
            <Button
              variant="ghost"
              size={expanded ? 'sm' : 'icon-sm'}
              onClick={toggle}
              className={cn('w-full', !expanded && 'mx-auto')}
              aria-label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              {expanded ? (
                <>
                  <PanelLeftClose />
                  Collapse
                </>
              ) : (
                <PanelLeftOpen />
              )}
            </Button>
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <>
      {/* Desktop rail */}
      <motion.aside
        initial={false}
        animate={{ width: expanded ? EXPANDED_WIDTH : COLLAPSED_WIDTH }}
        transition={spring}
        className="fixed inset-y-0 left-0 z-40 hidden shrink-0 border-r border-border/15 bg-card md:block"
      >
        {content(false)}
      </motion.aside>

      {/* Mobile drawer */}
      {/*
       * The drawer manages its own mount. See the note in
       * marketing-sidenav.tsx. AnimatePresence's removal is lost when the same
       * interaction also starts a navigation, which left the dialog off-screen
       * but still in the tab order.
       */}
      {drawerMounted ? (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: mobileOpen ? 1 : 0 }}
            transition={{ duration: 0.2 }}
            onClick={closeMobile}
            className="fixed inset-0 z-40 bg-brand-ink-black/70 backdrop-blur-sm md:hidden"
            aria-hidden="true"
          />
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: mobileOpen ? 0 : '-100%' }}
            transition={reduced ? { duration: 0 } : spring}
            onAnimationComplete={() => {
              if (!mobileOpen) setDrawerMounted(false)
            }}
            className="fixed inset-y-0 left-0 z-50 w-[272px] border-r border-border/15 bg-card shadow-2xl md:hidden"
            role="dialog"
            aria-label="Navigation"
          >
            {content(true)}
          </motion.aside>
        </>
      ) : null}
    </>
  )
}

export const SIDEBAR_WIDTHS = { expanded: EXPANDED_WIDTH, collapsed: COLLAPSED_WIDTH }
