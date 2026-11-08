import { Link } from 'react-router-dom'
import { ArrowUpRight, Clock, Coins, Layers } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import type { StageDefinition, StageState } from '@/types/pipeline'
import { ACTOR_LABEL, STAGE_STATUS_LABEL, STAGE_STATUS_STYLES } from '@/lib/pipeline-stages'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn, formatCompactNumber, formatDuration, formatUsd } from '@/lib/utils'
import { spring } from '@/lib/motion'
import { resolveStageIcon } from './stage-icon'
import { STAGE_COLOR_CLASSES } from './stage-colors'

interface StageDetailProps {
  projectId: string
  definition: StageDefinition
  state: StageState
  className?: string
}

/** Expanded view of one selected stage: what it does, where it got to, and
 *  a link through to whatever it produced. */
export function StageDetail({ projectId, definition, state, className }: StageDetailProps) {
  const colors = STAGE_COLOR_CLASSES[definition.id]
  const Icon = resolveStageIcon(definition.icon)
  const statusStyle = STAGE_STATUS_STYLES[state.status]

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={definition.id}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={spring}
        className={className}
      >
        <Card glass className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <span
                className={cn(
                  'flex size-10 shrink-0 items-center justify-center rounded-full',
                  colors.bgSoft,
                  colors.text,
                )}
              >
                <Icon className="size-5" />
              </span>
              <div className="min-w-0 space-y-1">
                <p className="eyebrow">
                  Stage {definition.id} · {ACTOR_LABEL[definition.actor]}
                </p>
                <h2 className="font-display text-lg font-semibold">{definition.title}</h2>
                <p className="max-w-xl text-sm text-muted-foreground">{definition.summary}</p>
              </div>
            </div>
            <Badge className={statusStyle.badge}>{STAGE_STATUS_LABEL[state.status]}</Badge>
          </div>

          {state.metrics ? (
            <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <MetricTile
                icon={Layers}
                label="Items"
                value={formatCompactNumber(state.metrics.itemsProcessed)}
              />
              <MetricTile
                icon={Clock}
                label="Duration"
                value={formatDuration(state.metrics.durationMs)}
              />
              <MetricTile
                icon={Layers}
                label="Tokens"
                value={
                  state.metrics.tokensUsed === null
                    ? '-'
                    : formatCompactNumber(state.metrics.tokensUsed)
                }
              />
              <MetricTile
                icon={Coins}
                label="Cost"
                value={state.metrics.costUsd === null ? '-' : formatUsd(state.metrics.costUsd)}
              />
            </dl>
          ) : null}

          {state.error ? (
            <p className="mt-4 rounded-md border border-destructive/25 bg-destructive/5 p-3 text-sm text-destructive">
              {state.error}
            </p>
          ) : null}

          {definition.route ? (
            <div className="mt-5">
              <Button asChild variant="outline" size="sm">
                <Link to={`/app/projects/${projectId}/${definition.route}`}>
                  Open stage output
                  <ArrowUpRight />
                </Link>
              </Button>
            </div>
          ) : null}
        </Card>
      </motion.div>
    </AnimatePresence>
  )
}

function MetricTile({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Clock
  label: string
  value: string
}) {
  return (
    <div className="rounded-md border border-border/20 bg-muted/30 p-3">
      <dt className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
        <Icon className="size-3" aria-hidden="true" />
        {label}
      </dt>
      <dd className="mt-1 font-display text-sm font-semibold tabular-nums">{value}</dd>
    </div>
  )
}
