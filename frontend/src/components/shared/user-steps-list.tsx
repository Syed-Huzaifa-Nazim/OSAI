import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/badge'
import { USER_STEPS, USER_STEP_TEXT } from '@/lib/user-steps'
import { cn } from '@/lib/utils'
import { spring } from '@/lib/motion'

/** The six steps, numbered, with what each does. `compact` drops the descriptions (sign-in panel). */
export function UserStepsList({ compact = false }: { compact?: boolean }) {
  return (
    <ol className={compact ? 'space-y-3' : 'space-y-4'}>
      {USER_STEPS.map((step, index) => (
        <motion.li
          key={step.label}
          initial={{ opacity: 0, x: 18 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ ...spring, delay: 0.05 * index }}
          className={cn('flex gap-4', compact ? 'items-center' : 'card-soft items-start border border-border/15 p-5')}
        >
          <span
            className={cn(
              'flex shrink-0 items-center justify-center rounded-2xl font-display font-bold',
              compact ? 'size-8 text-sm' : 'size-11 text-base',
              step.you ? 'bg-warning/12 text-warning-ink' : 'bg-primary/10 text-primary',
            )}
          >
            {index + 1}
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={cn('font-semibold', compact ? 'text-sm' : 'font-display text-lg')}>{step.label}</span>
              {step.you ? <Badge variant="warning">You</Badge> : null}
              {!step.built && !compact ? <Badge variant="muted">Coming soon</Badge> : null}
            </div>
            {compact ? null : <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{USER_STEP_TEXT[index]}</p>}
          </div>
        </motion.li>
      ))}
    </ol>
  )
}
