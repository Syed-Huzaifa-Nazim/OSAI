import { Check, Lock, Store } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface HeroStep {
  label: string
  state: 'done' | 'current' | 'locked' | 'todo'
}

/** The project's name, who is compared with whom, and where the project is in its steps. */
export function ProjectHero({
  name,
  compare,
  steps,
}: {
  name: string
  compare?: string
  steps: HeroStep[]
}) {
  return (
    <div className="card-soft flex flex-col gap-5 border border-border/15 p-5 sm:p-6">
      <div className="flex items-center gap-4">
        <span className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Store className="size-6" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h1 className="truncate font-display text-2xl font-bold sm:text-[1.7rem]">{name}</h1>
          {compare ? <p className="truncate text-sm text-muted-foreground">{compare}</p> : null}
        </div>
      </div>

      <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-3 sm:gap-x-2" aria-label="Project steps">
        {steps.map((step, index) => (
          <li key={step.label} className="flex items-center gap-2">
            {index > 0 ? (
              <span
                className={cn(
                  'h-px w-3 sm:w-4 xl:w-8',
                  step.state === 'done' || step.state === 'current' ? 'bg-primary/50' : 'bg-border/40',
                )}
                aria-hidden="true"
              />
            ) : null}
            <span
              className={cn(
                'flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                step.state === 'done' && 'bg-success text-success-foreground',
                step.state === 'current' && 'bg-primary text-primary-foreground shadow-glow',
                step.state === 'locked' && 'bg-muted text-muted-foreground',
                step.state === 'todo' && 'border border-border/40 text-muted-foreground',
              )}
              aria-hidden="true"
            >
              {step.state === 'done' ? (
                <Check className="size-4" strokeWidth={3} />
              ) : step.state === 'locked' ? (
                <Lock className="size-3.5" />
              ) : (
                index + 1
              )}
            </span>
            <span
              className={cn(
                'text-sm',
                step.state === 'current' ? 'font-semibold text-foreground' : 'hidden text-muted-foreground sm:inline',
                step.state === 'done' && 'text-success',
              )}
              aria-current={step.state === 'current' ? 'step' : undefined}
            >
              {step.label}
              {step.state === 'locked' ? <span className="sr-only"> (not available yet)</span> : null}
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}

/** One number with an icon, as in the Violet design's summary tiles. */
export function StatTile({
  label,
  value,
  icon,
  tone = 'primary',
}: {
  label: string
  value: number | string
  icon: React.ReactNode
  tone?: 'primary' | 'success' | 'warning'
}) {
  return (
    <div className="card-soft flex flex-col items-start gap-2 border border-border/15 p-3 sm:flex-row sm:items-center sm:gap-4 sm:p-5">
      <span
        className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-xl sm:size-12 sm:rounded-2xl',
          tone === 'primary' && 'bg-primary/10 text-primary',
          tone === 'success' && 'bg-success/12 text-success',
          tone === 'warning' && 'bg-warning/12 text-warning-ink',
        )}
        aria-hidden="true"
      >
        {icon}
      </span>
      <div>
        <p className="text-xs font-medium text-muted-foreground sm:text-sm">{label}</p>
        <p className="font-display text-xl font-bold tabular-nums sm:text-2xl">{value}</p>
      </div>
    </div>
  )
}
