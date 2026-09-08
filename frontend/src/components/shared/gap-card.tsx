import { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, ChevronDown, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ConfidenceMeter } from './confidence-meter'
import { EvidenceList } from './evidence-list'
import type { Gap, GapPriority } from '@/types/domain'
import { cn, titleCase } from '@/lib/utils'
import { spring, staggerItem } from '@/lib/motion'

const PRIORITIES: GapPriority[] = ['critical', 'high', 'medium', 'low']

const PRIORITY_VARIANT: Record<GapPriority, 'destructive' | 'default' | 'secondary' | 'muted'> = {
  critical: 'destructive',
  high: 'default',
  medium: 'secondary',
  low: 'muted',
}

interface GapCardProps {
  gap: Gap
  /** Review mode adds the accept/reject controls used at HITL #1. */
  reviewable?: boolean
  onDecision?: (decision: 'accepted' | 'rejected') => void
  onPriorityChange?: (priority: GapPriority) => void
  onNoteChange?: (note: string) => void
}

export function GapCard({
  gap,
  reviewable = false,
  onDecision,
  onPriorityChange,
  onNoteChange,
}: GapCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [note, setNote] = useState(gap.reviewerNote ?? '')
  const priority = gap.userPriority ?? gap.priority
  const overridden = gap.userPriority !== null && gap.userPriority !== gap.priority

  return (
    <motion.div variants={staggerItem} layout transition={spring}>
      <Card
        className={cn(
          'overflow-hidden transition-colors',
          gap.decision === 'accepted' && 'border-success/35',
          gap.decision === 'rejected' && 'border-border/20 opacity-55',
        )}
      >
        <div className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={PRIORITY_VARIANT[priority]}>{titleCase(priority)}</Badge>
                <Badge variant="outline">{titleCase(gap.category)}</Badge>
                {overridden ? <Badge variant="secondary">Priority overridden</Badge> : null}
                {gap.decision === 'accepted' ? <Badge variant="success">Accepted</Badge> : null}
                {gap.decision === 'rejected' ? <Badge variant="muted">Rejected</Badge> : null}
              </div>
              <h3 className="font-display text-base font-semibold leading-snug">{gap.title}</h3>
            </div>
            <ConfidenceMeter value={gap.confidence} />
          </div>

          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{gap.description}</p>

          <div className="mt-4 rounded-md border border-primary/20 bg-primary/5 p-3">
            <p className="text-xs font-medium uppercase tracking-wide text-primary">Opportunity</p>
            <p className="mt-1 text-sm text-muted-foreground">{gap.opportunity}</p>
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="mt-3 -ml-2"
            onClick={() => {
              setExpanded(!expanded)
            }}
            aria-expanded={expanded}
          >
            <ChevronDown className={cn('transition-transform', expanded && 'rotate-180')} />
            {expanded ? 'Hide' : 'Show'} evidence ({gap.evidence.length})
          </Button>

          {expanded ? (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-3 overflow-hidden"
            >
              <EvidenceList evidence={gap.evidence} />
            </motion.div>
          ) : null}
        </div>

        {reviewable ? (
          <div className="space-y-4 border-t border-border/15 bg-muted/25 p-5">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant={gap.decision === 'accepted' ? 'success' : 'outline'}
                  onClick={() => onDecision?.('accepted')}
                  aria-pressed={gap.decision === 'accepted'}
                >
                  <Check />
                  Keep
                </Button>
                <Button
                  size="sm"
                  variant={gap.decision === 'rejected' ? 'destructive' : 'outline'}
                  onClick={() => onDecision?.('rejected')}
                  aria-pressed={gap.decision === 'rejected'}
                >
                  <X />
                  Drop
                </Button>
              </div>

              <div className="flex items-center gap-2">
                <label
                  htmlFor={`priority-${gap.id}`}
                  className="text-xs text-muted-foreground"
                >
                  Priority
                </label>
                <Select
                  value={priority}
                  onValueChange={(value) => onPriorityChange?.(value as GapPriority)}
                >
                  <SelectTrigger id={`priority-${gap.id}`} className="h-8 w-[130px] text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITIES.map((value) => (
                      <SelectItem key={value} value={value}>
                        {titleCase(value)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor={`note-${gap.id}`} className="text-xs text-muted-foreground">
                Note for the Strategist
              </label>
              <Textarea
                id={`note-${gap.id}`}
                rows={2}
                value={note}
                placeholder="Anything the agents should know about this gap?"
                onChange={(event) => {
                  setNote(event.target.value)
                }}
                onBlur={() => {
                  if (note !== (gap.reviewerNote ?? '')) onNoteChange?.(note)
                }}
              />
            </div>
          </div>
        ) : null}
      </Card>
    </motion.div>
  )
}
