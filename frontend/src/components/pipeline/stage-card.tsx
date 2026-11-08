import { Check, Loader2, TriangleAlert, UserRoundCheck } from 'lucide-react'
import { motion } from 'framer-motion'
import type { StageDefinition, StageState } from '@/types/pipeline'
import { ACTOR_LABEL, STAGE_STATUS_LABEL } from '@/lib/pipeline-stages'
import { cn, formatDuration } from '@/lib/utils'
import { spring } from '@/lib/motion'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { resolveStageIcon } from './stage-icon'
import { STAGE_COLOR_CLASSES } from './stage-colors'

interface StageCardProps {
  definition: StageDefinition
  state: StageState
  orientation: 'horizontal' | 'vertical'
  selected?: boolean
  onSelect?: () => void
  className?: string
}

/**
 * One stage in the stepper. Five visually distinct states:
 *   idle           muted, no fill
 *   running        stage-coloured, pulsing ring, live progress bar
 *   awaiting_human butter-cream glow that breathes, unmistakably blocked on you
 *   complete       success tick, metrics revealed
 *   error          destructive border and message
 */
export function StageCard({
  definition,
  state,
  orientation,
  selected = false,
  onSelect,
  className,
}: StageCardProps) {
  const reduced = usePrefersReducedMotion()
  const colors = STAGE_COLOR_CLASSES[definition.id]
  const Icon = resolveStageIcon(definition.icon)
  const isHorizontal = orientation === 'horizontal'

  const running = state.status === 'running'
  const awaiting = state.status === 'awaiting_human'
  const complete = state.status === 'complete'
  const errored = state.status === 'error'

  return (
    <motion.button
      type="button"
      onClick={onSelect}
      layout={!reduced}
      transition={spring}
      whileHover={reduced ? undefined : { y: -3 }}
      whileTap={reduced ? undefined : { scale: 0.985 }}
      aria-current={selected ? 'step' : undefined}
      aria-label={`Stage ${definition.id}: ${definition.title}. ${STAGE_STATUS_LABEL[state.status]}.`}
      className={cn(
        'glass group relative overflow-hidden rounded-lg p-4 text-left transition-colors',
        isHorizontal ? 'w-[210px] shrink-0' : 'w-full',
        selected && 'ring-2 ring-primary/50',
        awaiting && 'border-brand-butter-cream/40',
        errored && 'border-destructive/40',
        className,
      )}
    >
      {/* Breathing wash behind a stage that is blocked on a human. */}
      {awaiting && !reduced ? (
        <motion.span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-brand-butter-cream/10"
          animate={{ opacity: [0.35, 1, 0.35] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
        />
      ) : null}

      <div className="relative flex items-start gap-3">
        <span className="relative flex size-9 shrink-0 items-center justify-center rounded-full">
          {/* Expanding ring while the agent works. */}
          {running && !reduced ? (
            <span
              className={cn('absolute inset-0 animate-pulse-ring rounded-full', colors.bgSoft)}
              aria-hidden="true"
            />
          ) : null}
          <span
            className={cn(
              'relative flex size-9 items-center justify-center rounded-full transition-colors',
              complete
                ? 'bg-success/15 text-success'
                : errored
                  ? 'bg-destructive/15 text-destructive'
                  : awaiting
                    ? 'bg-brand-butter-cream/20 text-brand-butter-cream'
                    : running
                      ? cn(colors.bgSoft, colors.text)
                      : 'bg-muted/60 text-muted-foreground',
            )}
          >
            {complete ? (
              <motion.span
                initial={reduced ? false : { scale: 0, rotate: -30 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: 'spring', stiffness: 500, damping: 18 }}
              >
                <Check className="size-4" strokeWidth={3} />
              </motion.span>
            ) : errored ? (
              <TriangleAlert className="size-4" />
            ) : awaiting ? (
              <UserRoundCheck className="size-4" />
            ) : running ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Icon className="size-4" />
            )}
          </span>
        </span>

        <span className="min-w-0 flex-1">
          <span className="flex items-baseline gap-1.5">
            <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
              {String(definition.id).padStart(2, '0')}
            </span>
            <span
              className={cn(
                'truncate text-[10px] uppercase tracking-wider',
                definition.actor === 'human' ? 'text-brand-butter-cream' : 'text-muted-foreground',
              )}
            >
              {ACTOR_LABEL[definition.actor]}
            </span>
          </span>
          <span className="mt-0.5 block text-sm font-medium leading-snug">
            {definition.title}
          </span>
        </span>
      </div>

      <div className="relative mt-3 min-h-[18px]">
        {running ? (
          <>
            <p className="truncate text-xs text-muted-foreground">{state.message ?? 'Working…'}</p>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={cn('h-full rounded-full', colors.bg)}
                initial={false}
                animate={{ width: `${state.progress}%` }}
                transition={{ ease: 'linear', duration: 0.25 }}
              />
            </div>
          </>
        ) : awaiting ? (
          <p className="text-xs font-medium text-brand-butter-cream">
            {state.message ?? 'Awaiting your input'}
          </p>
        ) : errored ? (
          <p className="line-clamp-2 text-xs text-destructive">{state.error ?? 'Stage failed'}</p>
        ) : complete ? (
          <p className="truncate text-xs text-muted-foreground">
            {state.message ??
              (state.metrics ? formatDuration(state.metrics.durationMs) : 'Complete')}
          </p>
        ) : (
          <p className="text-xs text-muted-foreground/60">Not started</p>
        )}
      </div>
    </motion.button>
  )
}
