import type { LucideIcon } from 'lucide-react'
import { motion } from 'framer-motion'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { spring } from '@/lib/motion'

interface StatCardProps {
  label: string
  value: string | number
  hint?: string
  icon: LucideIcon
  /** Tailwind text colour class for the icon, e.g. 'text-stage-4'. */
  accentClassName?: string
  className?: string
}

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  accentClassName = 'text-primary',
  className,
}: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={spring}
      whileHover={{ y: -2 }}
    >
      <Card glass className={cn('h-full p-5', className)}>
        <div className="flex items-start justify-between gap-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <Icon className={cn('size-4 shrink-0', accentClassName)} aria-hidden="true" />
        </div>
        <p className="mt-3 font-display text-2xl font-semibold tabular-nums">{value}</p>
        {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
      </Card>
    </motion.div>
  )
}
