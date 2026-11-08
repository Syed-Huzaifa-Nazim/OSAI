import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { springSnappy } from '@/lib/motion'

interface SidebarLinkProps {
  to: string
  label: string
  icon: LucideIcon
  expanded: boolean
  end?: boolean
  onNavigate?: () => void
}

/**
 * One sidebar row. When collapsed the label is replaced by a tooltip so the
 * rail stays usable at icon width.
 */
export function SidebarLink({
  to,
  label,
  icon: Icon,
  expanded,
  end = false,
  onNavigate,
}: SidebarLinkProps) {
  const link = (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'group relative flex h-10 items-center gap-3 rounded-md px-3 text-sm transition-colors',
          expanded ? 'justify-start' : 'justify-center',
          isActive
            ? 'text-primary'
            : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive ? (
            <motion.span
              layoutId="sidebar-active"
              transition={springSnappy}
              className="absolute inset-0 rounded-md bg-primary/12"
              aria-hidden="true"
            />
          ) : null}
          {isActive ? (
            <motion.span
              layoutId="sidebar-active-bar"
              transition={springSnappy}
              className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary"
              aria-hidden="true"
            />
          ) : null}
          <Icon className="relative size-4 shrink-0" aria-hidden="true" />
          {expanded ? (
            <motion.span
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="relative truncate"
            >
              {label}
            </motion.span>
          ) : null}
        </>
      )}
    </NavLink>
  )

  if (expanded) return link

  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent side="right">{label}</TooltipContent>
    </Tooltip>
  )
}
