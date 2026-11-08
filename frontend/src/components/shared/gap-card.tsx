import { useState } from 'react'
import { motion } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import { Check, ChevronDown, ExternalLink, Sparkles, X } from 'lucide-react'
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
import { gapsApi, type GapExplanation } from '@/lib/api/services'
import { errorMessage } from '@/lib/api-client'
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
  /** When set, shows the Explain button (grounded LLM + pgvector explanation). */
  explainProjectId?: string
}

export function GapCard({
  gap,
  reviewable = false,
  onDecision,
  onPriorityChange,
  onNoteChange,
  explainProjectId,
}: GapCardProps) {
  const [expanded, setExpanded] = useState(false)
  const explain = useMutation<GapExplanation, Error>({
    mutationFn: () => gapsApi.explain(explainProjectId as string, gap.id),
  })
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

          {explainProjectId ? (
            <div className="mt-2">
              <Button
                variant="outline"
                size="sm"
                loading={explain.isPending}
                onClick={() => {
                  explain.mutate()
                }}
              >
                <Sparkles />
                {explain.data ? 'Explain again' : 'Explain'}
              </Button>

              {explain.isError ? (
                <p className="mt-2 text-sm text-destructive">{errorMessage(explain.error)}</p>
              ) : null}

              {explain.data ? (
                <div className="mt-3 space-y-3 rounded-md border border-border/30 bg-muted/20 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-xs font-medium uppercase tracking-wide text-primary">
                      Why this was flagged
                    </p>
                    {explain.data.grounded ? (
                      <Badge variant="success">Grounded in scraped posts</Badge>
                    ) : (
                      <Badge variant="destructive">Not grounded: treat with care</Badge>
                    )}
                  </div>
                  <p className="text-sm leading-relaxed">{explain.data.explanation}</p>
                  {explain.data.unknownCitations.length > 0 ? (
                    <p className="text-xs text-destructive">
                      Removed citations to evidence that was never retrieved:{' '}
                      {explain.data.unknownCitations.join(', ')}
                    </p>
                  ) : null}
                  <ul className="space-y-2">
                    {explain.data.evidence.map((item) => (
                      <li
                        key={item.id}
                        className={cn(
                          'rounded border border-border/20 p-2 text-xs',
                          explain.data.evidenceUsed.includes(item.id) && 'border-primary/40',
                        )}
                      >
                        <div className="mb-1 flex flex-wrap items-center gap-2 text-muted-foreground">
                          <span className="font-mono">[{item.id}]</span>
                          <span>
                            {item.side === 'you' ? 'Your' : 'Competitor'}
                            {item.format && item.format !== 'other' ? ` ${item.format}` : ''} post
                          </span>
                          <span>· {item.fieldType}</span>
                          <span>· match {Math.round(item.similarity * 100)}%</span>
                          {item.postUrl ? (
                            <a
                              href={item.postUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 underline"
                            >
                              Open post <ExternalLink className="size-3" />
                            </a>
                          ) : null}
                        </div>
                        <p>{item.text}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
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
                Note for the record
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
