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
      <Card className={cn('flex h-full flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-4 sm:p-5', className)}>
        <span
          className={cn(
            'flex size-10 shrink-0 items-center justify-center rounded-xl bg-muted sm:size-12 sm:rounded-2xl',
            accentClassName,
          )}
        >
          <Icon className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground sm:text-sm">{label}</p>
          <p className="font-display text-2xl font-bold tabular-nums">{value}</p>
          {hint ? <p className="hidden text-xs text-muted-foreground sm:block">{hint}</p> : null}
        </div>
      </Card>
    </motion.div>
  )
}
