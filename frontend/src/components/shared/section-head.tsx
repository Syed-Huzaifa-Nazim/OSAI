import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

/** A form section's heading: an icon tile, a bold title and a short line under it. */
export function SectionHead({
  icon: Icon,
  title,
  subtitle,
  tone = 'primary',
}: {
  icon: LucideIcon
  title: string
  subtitle?: React.ReactNode
  tone?: 'primary' | 'warning'
}) {
  return (
    <div className="flex items-start gap-4">
      <span
        className={cn(
          'flex size-12 shrink-0 items-center justify-center rounded-2xl',
          tone === 'primary' ? 'bg-primary/10 text-primary' : 'bg-warning/20 text-warning-ink',
        )}
      >
        <Icon className="size-6" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <h2 className="font-display text-lg font-bold">{title}</h2>
        {subtitle ? <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p> : null}
      </div>
    </div>
  )
}
