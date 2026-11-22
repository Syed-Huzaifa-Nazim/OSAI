import { useState } from 'react'
import { motion } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import {
  Check,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Hash,
  ImageIcon,
  Info,
  Play,
  Sparkles,
  X,
} from 'lucide-react'
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
import { GapExplanationLoading, GapExplanationPanel, fromSaved } from './gap-explanation'
import { SafeImage } from './safe-image'
import { mediaSrc } from '@/lib/media'
import type { Gap, GapDetails, GapPriority, HowSure } from '@/types/domain'
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

const KIND_LABEL: Record<NonNullable<GapDetails['kind']>, string> = {
  format: 'Type of post',
  timing: 'When they post',
  reach: 'Reel reach',
  topic: 'What you post about',
  hashtag: 'Hashtags',
  media: 'Pictures and videos',
  weakness: 'Your weak spot',
  habit: 'Habit',
  profile: 'Profile',
  caption: 'What the captions say',
  picture: 'What the pictures show',
  reel: 'How the reels open',
  daraz_price: 'Price',
  daraz_offer: 'Offers and badges',
  daraz_title: 'Title and search words',
  daraz_photos: 'Photos',
  daraz_content: 'Listing details',
  daraz_reviews: 'What customers say',
}

const SURE_VARIANT: Record<HowSure, 'success' | 'secondary' | 'muted'> = {
  High: 'success',
  Medium: 'secondary',
  Low: 'muted',
}

const SURE_HINT =
  'How sure we are. It depends on how unlikely it is that the difference is just chance, and on how many posts we could read.'

interface GapCardProps {
  gap: Gap
  /** Review mode adds the accept/reject controls used at HITL #1. */
  reviewable?: boolean
  onDecision?: (decision: 'accepted' | 'rejected') => void
  onPriorityChange?: (priority: GapPriority) => void
  onNoteChange?: (note: string) => void
  /** When set, shows the Explain button. */
  explainProjectId?: string
  /** Buttons always go under the title (for narrow places such as a dialog). */
  stacked?: boolean
}

/** Daraz gaps have no Explain button: what was found, the numbers, the step to take and the top listings show here. */
function DarazDetails({ gap }: { gap: Gap }) {
  const rows = gap.details?.numbers ?? []
  const examples = (gap.evidence ?? []).filter((e) => e.sourceUrl)
  return (
    <div className="space-y-3 pt-1 text-sm">
      <p className="text-muted-foreground">{gap.description}</p>
      {rows.length ? (
        <dl className="grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1 text-xs">
          {rows
            .flatMap((r) => [
              ['You', r.you],
              ['Competitor', r.competitor],
              ['Top 20 listings', r.typical],
            ])
            .filter(([, v]) => v)
            .map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="font-semibold">{k}</dt>
                <dd className="text-muted-foreground">{v}</dd>
              </div>
            ))}
        </dl>
      ) : null}
      {gap.opportunity ? (
        <p className="rounded-xl bg-primary/5 px-3 py-2">
          <span className="font-semibold text-primary">Try this: </span>
          {gap.opportunity.replace(/^Try this:\s*/, '')}
        </p>
      ) : null}
      {examples.length ? (
        <div className="text-xs">
          <p className="font-semibold">
            {gap.details?.kind === 'daraz_reviews'
              ? 'From the reviews'
              : 'Top listings for this search'}
          </p>
          <ul className="mt-1 space-y-1">
            {examples.slice(0, 3).map((e) => (
              <li
                key={`${e.sourceId}-${e.quote}`}
                className="text-muted-foreground [overflow-wrap:anywhere]"
              >
                <a
                  href={e.sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-primary hover:underline"
                >
                  {e.sourceTitle}
                </a>
                {': '}
                {e.quote}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {gap.details?.technical?.length ? (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer font-semibold text-foreground">
            How we found this
          </summary>
          <ul className="mt-1 list-disc space-y-1 pl-4">
            {gap.details.technical.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  )
}

export function GapCard({
  gap,
  reviewable = false,
  onDecision,
  onPriorityChange,
  onNoteChange,
  explainProjectId,
  stacked = false,
}: GapCardProps) {
  const [expanded, setExpanded] = useState(false)
  const explain = useMutation<GapExplanation, Error>({
    mutationFn: () => gapsApi.explain(explainProjectId as string, gap.id),
  })
  const [note, setNote] = useState(gap.reviewerNote ?? '')
  // The explanation opens on demand and can be closed again after reading.
  const [open, setOpen] = useState(false)
  const priority = gap.userPriority ?? gap.priority
  const overridden = gap.userPriority !== null && gap.userPriority !== gap.priority

  const details = gap.details
  const plain = Boolean(details?.howSure)
  const kind = details?.kind
  // A fresh explanation, or the one saved the last time Explain was pressed (so a reload keeps it).
  const explanation =
    explain.data ??
    (plain && details?.explanation ? fromSaved(gap.id, details.explanation) : undefined)

  const explainButton = explainProjectId ? (
    <Button
      variant="outline"
      size="sm"
      loading={explain.isPending && !explanation}
      aria-expanded={open}
      onClick={() => {
        if (open && explanation) {
          setOpen(false)
          return
        }
        setOpen(true)
        if (!explanation) explain.mutate()
      }}
    >
      {open && explanation ? (
        <ChevronUp />
      ) : explain.isPending && !explanation ? null : (
        <Sparkles />
      )}
      {open && explanation
        ? 'Hide explanation'
        : explanation
          ? 'Show explanation'
          : explain.isPending
            ? 'Explaining…'
            : 'Explain'}
    </Button>
  ) : null

  const explainResult = explainProjectId ? (
    <>
      {explain.isError ? (
        <p className="mt-2 text-sm text-destructive">{errorMessage(explain.error)}</p>
      ) : null}

      {open && !explanation && explain.isPending ? <GapExplanationLoading /> : null}

      {explanation && open ? (
        plain ? (
          <GapExplanationPanel
            data={explanation}
            values={details?.numbers ?? explanation.values ?? []}
            unproven={details?.unproven}
            technical={details?.technical}
            againLoading={explain.isPending}
            onAgain={() => {
              explain.mutate()
            }}
          />
        ) : (
          <div className="mt-3 space-y-3 rounded-md border border-border/30 bg-muted/20 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs font-medium uppercase tracking-wide text-primary">
                Why this was flagged
              </p>
              {explanation.grounded ? (
                <Badge variant="success">Grounded in scraped posts</Badge>
              ) : (
                <Badge variant="destructive">Treat with care</Badge>
              )}
            </div>
            <p className="text-sm leading-relaxed">{explanation.explanation}</p>
            <ul className="space-y-2">
              {explanation.evidence.map((item) => (
                <li
                  key={item.id}
                  className={cn(
                    'rounded border border-border/20 p-2 text-xs',
                    explanation.evidenceUsed.includes(item.id) && 'border-primary/40',
                  )}
                >
                  <div className="mb-1 flex flex-wrap items-center gap-2 text-muted-foreground">
                    <span className="font-mono">[{item.id}]</span>
                    <span>{item.side === 'you' ? 'Your' : 'Competitor'} post</span>
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
        )
      ) : null}
    </>
  ) : null

  const explainBlock = explainProjectId ? (
    <div className="mt-3">
      {explainButton}
      {explainResult}
    </div>
  ) : null

  return (
    <motion.div variants={staggerItem} layout transition={spring}>
      <Card
        className={cn(
          'overflow-hidden transition-all hover:shadow-[0_14px_36px_-16px_hsl(var(--shadow-color)/0.3)]',
          plain && open && explanation && 'bg-gradient-to-br from-card via-card to-primary/5',
          gap.decision === 'accepted' && 'border-success/60 ring-1 ring-success/30',
          gap.decision === 'rejected' && 'border-border/20 opacity-55',
        )}
      >
        <div className={plain ? 'p-4 sm:p-5' : 'p-5'}>
          {plain ? (
            <>
              <div className={cn('flex flex-col gap-4', !stacked && 'lg:flex-row lg:items-center')}>
                <div className="flex min-w-0 flex-1 items-start gap-4">
                  <GapThumb gap={gap} />
                  <div className="min-w-0 space-y-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {kind ? <Badge variant="default">{KIND_LABEL[kind]}</Badge> : null}
                      {details?.market ? (
                        <Badge
                          variant="outline"
                          title={
                            kind?.startsWith('daraz_')
                              ? 'Compared with the top Daraz listings for your search word, not only your competitor.'
                              : 'Compared with jewellery shops on Instagram, not only your competitor.'
                          }
                        >
                          {kind?.startsWith('daraz_') ? 'Top listings' : 'Jewellery market'}
                        </Badge>
                      ) : null}
                      {details?.unproven ? (
                        <Badge
                          variant="warning"
                          title="A real difference, but with this many posts it could still be chance."
                        >
                          Not proven yet · worth trying
                        </Badge>
                      ) : (
                        <Badge variant={SURE_VARIANT[details?.howSure ?? 'Low']} title={SURE_HINT}>
                          How sure: {details?.howSure}
                        </Badge>
                      )}
                      {gap.decision === 'accepted' ? <Badge variant="success">Kept</Badge> : null}
                      {gap.decision === 'rejected' ? <Badge variant="muted">Dropped</Badge> : null}
                    </div>
                    <h3 className="font-display text-base font-semibold leading-snug [overflow-wrap:anywhere] sm:text-[1.05rem]">
                      {gap.title}
                    </h3>
                    {kind?.startsWith('daraz_') ? <DarazDetails gap={gap} /> : null}
                  </div>
                </div>

                <div
                  className={cn(
                    'flex flex-wrap items-center gap-2',
                    !stacked && 'lg:shrink-0 lg:justify-end',
                  )}
                >
                  {explainButton}
                  {reviewable ? (
                    <>
                      <Button
                        size="sm"
                        variant={gap.decision === 'accepted' ? 'success' : 'outline'}
                        className={cn(
                          gap.decision !== 'accepted' && 'text-success hover:text-success',
                        )}
                        onClick={() => onDecision?.('accepted')}
                        aria-pressed={gap.decision === 'accepted'}
                      >
                        <Check />
                        Keep
                      </Button>
                      <Button
                        size="sm"
                        variant={gap.decision === 'rejected' ? 'destructive' : 'outline'}
                        className={cn(
                          gap.decision !== 'rejected' && 'text-destructive hover:text-destructive',
                        )}
                        onClick={() => onDecision?.('rejected')}
                        aria-pressed={gap.decision === 'rejected'}
                      >
                        <X />
                        Drop
                      </Button>
                      <Select
                        value={priority}
                        onValueChange={(value) => onPriorityChange?.(value as GapPriority)}
                      >
                        <SelectTrigger
                          className="h-8 w-[118px] rounded-xl text-xs"
                          aria-label="Priority"
                        >
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
                    </>
                  ) : null}
                  {open && explanation ? (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="rounded-full bg-muted/60"
                      onClick={() => {
                        setOpen(false)
                      }}
                      aria-label="Close explanation"
                    >
                      <X />
                    </Button>
                  ) : null}
                </div>
              </div>

              {explainResult}

              {reviewable ? (
                <label className="mt-4 flex items-center gap-3 rounded-full border border-border/30 bg-card px-4 py-2 focus-within:ring-2 focus-within:ring-ring">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                    <Info className="size-3.5" aria-hidden="true" />
                  </span>
                  <span className="sr-only">Your note on this gap</span>
                  <input
                    className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                    value={note}
                    placeholder="Add a note…"
                    onChange={(event) => {
                      setNote(event.target.value)
                    }}
                    onBlur={() => {
                      if (note !== (gap.reviewerNote ?? '')) onNoteChange?.(note)
                    }}
                  />
                </label>
              ) : null}
            </>
          ) : (
            <>
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
                <ConfidenceMeter value={gap.confidence} showLabel={false} />
              </div>

              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {gap.description}
              </p>

              <div className="mt-4 rounded-md border border-primary/20 bg-primary/5 p-3">
                <p className="text-xs font-medium uppercase tracking-wide text-primary">
                  Opportunity
                </p>
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

              {explainBlock}
            </>
          )}
        </div>

        {reviewable && !plain ? (
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
                <label htmlFor={`priority-${gap.id}`} className="text-xs text-muted-foreground">
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

/** The gap's first example post as a small picture (a reel shows its cover frame with a play sign);
 *  an icon when there is no still picture. */
function GapThumb({ gap }: { gap: Gap }) {
  const example = gap.details?.examples?.[0]
  const url = example?.imageUrl ?? ''
  const videoFile = /\.mp4(\?|$)/i.test(url)
  const isVideo = (example?.format ?? '').startsWith('video') || videoFile
  const picture = url && !videoFile ? url : ''
  const Icon = gap.details?.kind === 'hashtag' ? Hash : isVideo ? Play : ImageIcon
  return (
    <span className="relative flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-primary/10 text-primary sm:size-[72px]">
      {picture ? (
        <SafeImage
          src={mediaSrc(picture)}
          alt=""
          className="size-full border-0"
          fit="cover"
          compact
        />
      ) : (
        <Icon className="size-6" aria-hidden="true" />
      )}
      {picture && isVideo ? (
        <span className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
          <span className="flex size-7 items-center justify-center rounded-full bg-black/45 text-white">
            <Play className="ml-0.5 size-3.5 fill-current" />
          </span>
        </span>
      ) : null}
    </span>
  )
}
