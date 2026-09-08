import { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown, Clock, Gauge, Megaphone, Wrench } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { CriticPanel } from './critic-panel'
import type { CriticFeedback, Initiative } from '@/types/domain'
import { cn, titleCase } from '@/lib/utils'
import { spring, staggerItem } from '@/lib/motion'

const EFFORT_VARIANT = {
  low: 'success',
  medium: 'secondary',
  high: 'destructive',
} as const

export function InitiativeCard({
  initiative,
  index,
  feedback,
}: {
  initiative: Initiative
  index: number
  feedback: CriticFeedback[]
}) {
  const [showCritic, setShowCritic] = useState(false)
  const related = feedback.filter((item) => item.targetInitiativeId === initiative.id)

  return (
    <motion.div variants={staggerItem} layout transition={spring}>
      <Card className={cn('overflow-hidden', initiative.revisedFromDraft && 'border-primary/30')}>
        <div className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 gap-3">
              <span className="font-mono text-lg tabular-nums text-muted-foreground/50">
                {String(index + 1).padStart(2, '0')}
              </span>
              <div className="min-w-0">
                <h3 className="font-display text-base font-semibold leading-snug">
                  {initiative.title}
                </h3>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Badge variant="outline">
                    <Megaphone />
                    {initiative.channel}
                  </Badge>
                  <Badge variant={EFFORT_VARIANT[initiative.effort]}>
                    <Gauge />
                    {titleCase(initiative.effort)} effort
                  </Badge>
                  <Badge variant="muted">
                    <Clock />
                    {initiative.timelineWeeks} weeks
                  </Badge>
                  {initiative.revisedFromDraft ? (
                    <Badge>
                      <Wrench />
                      Revised by the Critic
                    </Badge>
                  ) : null}
                </div>
              </div>
            </div>
          </div>

          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            {initiative.rationale}
          </p>

          <div className="mt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Action steps
            </p>
            <ol className="mt-2 space-y-2">
              {initiative.actions.map((action, actionIndex) => (
                <li key={action} className="flex gap-3 text-sm">
                  <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/12 font-mono text-[10px] text-primary">
                    {actionIndex + 1}
                  </span>
                  <span className="text-muted-foreground">{action}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="mt-4 rounded-md border border-border/20 bg-muted/25 p-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Expected impact
            </p>
            <p className="mt-1 text-sm text-muted-foreground">{initiative.expectedImpact}</p>
          </div>

          {related.length > 0 ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="mt-3 -ml-2"
                onClick={() => {
                  setShowCritic(!showCritic)
                }}
                aria-expanded={showCritic}
              >
                <ChevronDown className={cn('transition-transform', showCritic && 'rotate-180')} />
                {showCritic ? 'Hide' : 'Show'} what the Critic changed ({related.length})
              </Button>
              {showCritic ? (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mt-3 overflow-hidden"
                >
                  <CriticPanel feedback={feedback} initiativeId={initiative.id} />
                </motion.div>
              ) : null}
            </>
          ) : null}
        </div>
      </Card>
    </motion.div>
  )
}
