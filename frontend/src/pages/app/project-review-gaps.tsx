import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCheck, Download, Info, ListChecks, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { GapCard } from '@/components/shared/gap-card'
import { GapCategories } from '@/components/shared/gap-categories'
import { DarazStanding } from '@/components/shared/daraz-standing'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { useGaps, useSubmitGapReview, useUpdateGap } from '@/hooks/use-insights'
import { usePipeline } from '@/hooks/use-pipeline'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { gapsApi } from '@/lib/api/services'
import { staggerContainer } from '@/lib/motion'
import { cn } from '@/lib/utils'
import type { Gap, GapPriority } from '@/types/domain'

/**
 * HITL checkpoint #1 (stage 5).
 *
 * The pipeline is parked here until a person triages the gap list. Nothing is
 * submitted until every gap has an explicit decision. Leaving one untouched
 * would let an unreviewed finding reach the Strategist, which is precisely what
 * this checkpoint exists to prevent.
 */
export default function ReviewGapsPage() {
  const projectId = useProjectId()
  const navigate = useNavigate()
  const project = useProject(projectId)
  const pipeline = usePipeline(projectId)
  const { data: gaps, isLoading, isError, error, refetch } = useGaps(projectId)
  const updateGap = useUpdateGap(projectId)
  const submitReview = useSubmitGapReview(projectId)
  const [notes, setNotes] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [downloading, setDownloading] = useState<'all' | 'kept' | null>(null)

  const download = async (which: 'all' | 'kept') => {
    setDownloading(which)
    try {
      await gapsApi.downloadReport(projectId, which)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setDownloading(null)
    }
  }

  useDocumentTitle(project.data ? `${project.data.brandName} · Review gaps` : 'Review gaps')

  const { accepted, rejected, pending } = useMemo(() => {
    const list = gaps ?? []
    return {
      accepted: list.filter((gap) => gap.decision === 'accepted'),
      rejected: list.filter((gap) => gap.decision === 'rejected'),
      pending: list.filter((gap) => gap.decision === 'pending'),
    }
  }, [gaps])

  const alreadyReviewed = pipeline.data ? pipeline.data.stages[5].status === 'complete' : false
  const canSubmit = pending.length === 0 && accepted.length > 0 && !alreadyReviewed
  // Real projects stop at this checkpoint: stages 6-9 are not built yet.
  const isRealProject = project.data ? !project.data.isDemo : false
  const explainProjectId =
    isRealProject &&
    (project.data?.socialPlatform === 'instagram' || project.data?.ecommercePlatform === 'daraz')
      ? projectId
      : undefined
  const analysisNotes = pipeline.data?.stages[4]?.metrics?.notes ?? []
  // What the analysis measured for the (single) competitor: strengths and the full trait comparison.
  const analysisPart = pipeline.data?.stages[4]?.metrics?.analysis?.[0]
  // Daraz projects: where both listings stand, and every proven lever side by side.
  const darazPart = pipeline.data?.stages[4]?.metrics?.daraz?.[0]

  const [filter, setFilter] = useState<Filter>('all')
  const [showAll, setShowAll] = useState(false)
  // Older and demo gaps carry no kind: they are shown as one list, without the category buttons.
  const hasKinds =
    (gaps ?? []).some((gap) => gap.details?.kind !== undefined) || darazPart !== undefined
  const listOpen = showAll || !hasKinds
  const list = gaps ?? []
  const counts: Record<Filter, number> = {
    all: list.length,
    proven: list.filter((gap) => !gap.details?.unproven).length,
    test: list.filter((gap) => gap.details?.unproven).length,
    kept: accepted.length,
  }
  const shown = list.filter((gap) => FILTERS[filter].keep(gap))
  const submitLabel = isRealProject ? 'Save my review' : 'Send to strategy'
  const renderGap = (gap: Gap, opts?: { stacked?: boolean }) => (
    <GapCard
      key={gap.id}
      gap={gap}
      stacked={opts?.stacked}
      reviewable={!alreadyReviewed}
      explainProjectId={explainProjectId}
      onDecision={(decision) => {
        updateGap.mutate({ gapId: gap.id, patch: { decision } })
      }}
      onPriorityChange={(userPriority: GapPriority) => {
        updateGap.mutate({ gapId: gap.id, patch: { userPriority } })
      }}
      onNoteChange={(reviewerNote) => {
        updateGap.mutate({ gapId: gap.id, patch: { reviewerNote } })
      }}
    />
  )
  const openConfirm = (): void => {
    setConfirmOpen(true)
  }

  if (isError) {
    return (
      <ErrorState
        message={errorMessage(error)}
        onRetry={() => {
          void refetch()
        }}
      />
    )
  }

  return (
    <div className="space-y-6 pb-28 lg:pb-0">
      {analysisNotes.length > 0 ? (
        <Card className="flex gap-3 p-4">
          <Info className="mt-0.5 size-4 shrink-0 text-primary" />
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-semibold">Notes from the analysis</p>
            <ul className="list-disc space-y-0.5 pl-4 text-sm text-muted-foreground">
              {analysisNotes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </div>
        </Card>
      ) : null}

      {alreadyReviewed ? (
        <Card className="flex flex-wrap items-center gap-4 border-success/30 bg-success/5 p-5">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-success/15 text-success">
            <ShieldCheck className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-display text-sm font-semibold">This checkpoint is closed</p>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {isRealProject
                ? 'You have reviewed these gaps. The strategy stages are not built yet, so the project stops here. The list below is kept as a record.'
                : 'You have already prioritised these gaps and the Strategist has taken over. The list below is kept as a record.'}
            </p>
          </div>
          {isRealProject ? null : (
            <Button asChild variant="outline">
              <Link to={`/app/projects/${projectId}/strategy`}>View the strategy</Link>
            </Button>
          )}
        </Card>
      ) : null}

      {isLoading ? (
        <LoadingState rows={4} />
      ) : list.length === 0 && !darazPart ? (
        <EmptyState
          title="There is nothing to review yet"
          description="No gaps have been found for this project yet. Collect posts and press Find gaps first."
          icon={<ListChecks className="size-5" />}
          action={
            <Button asChild variant="outline">
              <Link to={`/app/projects/${projectId}/${isRealProject ? 'sources' : 'pipeline'}`}>
                Go back
              </Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
          <div className="min-w-0 space-y-5">
            {darazPart ? <DarazStanding part={darazPart} /> : null}
            {hasKinds ? (
              <GapCategories
                gaps={list}
                renderGap={renderGap}
                showingAll={showAll}
                strengths={darazPart?.strengths ?? analysisPart?.strengths}
                comparison={darazPart?.comparison ?? analysisPart?.content?.comparison}
                onShowAll={() => {
                  setShowAll((value) => !value)
                }}
              />
            ) : null}

            {listOpen ? (
              <>
                <div role="tablist" aria-label="Show gaps" className="flex flex-wrap gap-2">
                  {(Object.keys(FILTERS) as Filter[]).map((key) => (
                    <button
                      key={key}
                      type="button"
                      role="tab"
                      aria-selected={filter === key}
                      onClick={() => {
                        setFilter(key)
                      }}
                      className={cn(
                        'inline-flex h-9 items-center gap-2 rounded-full border px-3.5 text-sm font-medium transition-colors',
                        filter === key
                          ? 'border-primary bg-primary text-primary-foreground shadow-glow'
                          : 'border-border/25 bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground',
                      )}
                    >
                      {FILTERS[key].label}
                      <span
                        className={cn(
                          'rounded-full px-1.5 text-xs tabular-nums',
                          filter === key ? 'bg-primary-foreground/20' : 'bg-muted',
                        )}
                      >
                        {counts[key]}
                      </span>
                    </button>
                  ))}
                </div>

                <motion.div
                  variants={staggerContainer}
                  initial="initial"
                  animate="animate"
                  className="space-y-4"
                >
                  {shown.map((gap) => renderGap(gap))}
                  {shown.length === 0 ? (
                    <p className="rounded-2xl border border-dashed border-border/30 p-6 text-center text-sm text-muted-foreground">
                      No gaps in this list.
                    </p>
                  ) : null}
                </motion.div>
              </>
            ) : null}
          </div>

          <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start" aria-label="Your decision">
            <Card className="space-y-4 p-5">
              <p className="font-display text-lg font-bold">Your decision</p>
              <dl className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Kept gaps</dt>
                  <dd className="font-display text-lg font-bold text-success tabular-nums">
                    {accepted.length}
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">To decide</dt>
                  <dd className="font-display text-lg font-bold text-warning-ink tabular-nums">
                    {pending.length}
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Dropped</dt>
                  <dd className="font-display text-lg font-bold tabular-nums">{rejected.length}</dd>
                </div>
              </dl>
              {!alreadyReviewed ? (
                <>
                  <div className="space-y-1.5">
                    <label htmlFor="decision-note" className="text-sm font-medium">
                      Add a note{' '}
                      <span className="font-normal text-muted-foreground">(optional)</span>
                    </label>
                    <Textarea
                      id="decision-note"
                      rows={3}
                      value={notes}
                      placeholder="e.g. Focus on carousels first."
                      onChange={(event) => {
                        setNotes(event.target.value)
                      }}
                    />
                  </div>
                  <Button className="w-full" disabled={!canSubmit} onClick={openConfirm}>
                    <CheckCheck />
                    {submitLabel}
                  </Button>
                  {pending.length > 0 ? (
                    <p className="text-xs text-muted-foreground">
                      Keep or drop every gap first ({pending.length} left).
                    </p>
                  ) : null}
                </>
              ) : null}
            </Card>

            {isRealProject ? (
              <Card className="space-y-2.5 p-5">
                <p className="text-sm font-semibold">Download PDF</p>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  loading={downloading === 'all'}
                  disabled={downloading !== null}
                  onClick={() => {
                    void download('all')
                  }}
                >
                  <Download /> All gaps
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  loading={downloading === 'kept'}
                  disabled={downloading !== null || accepted.length === 0}
                  title={accepted.length === 0 ? 'Keep at least one gap first' : undefined}
                  onClick={() => {
                    void download('kept')
                  }}
                >
                  <Download /> Kept gaps ({accepted.length})
                </Button>
              </Card>
            ) : null}
          </aside>
        </div>
      )}

      {!alreadyReviewed && list.length > 0 ? (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border/15 bg-card/95 px-4 py-3 backdrop-blur-xl lg:hidden">
          <div className="mx-auto flex max-w-xl items-center gap-3">
            <p className="min-w-0 flex-1 text-sm text-muted-foreground">
              <span className="font-semibold text-success">{accepted.length} kept</span> ·{' '}
              {pending.length} to decide
            </p>
            <Button disabled={!canSubmit} onClick={openConfirm}>
              {submitLabel}
            </Button>
          </div>
        </div>
      ) : null}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {isRealProject
                ? `Save your review of ${accepted.length} gaps?`
                : `Send ${accepted.length} gaps to the Strategist?`}
            </DialogTitle>
            <DialogDescription>
              {isRealProject
                ? 'This closes the checkpoint and stores your decisions. The project stops here: the strategy stages are not built yet.'
                : `The ${rejected.length} gap${rejected.length === 1 ? '' : 's'} you dropped will not influence the strategy. This closes the checkpoint and starts stage 6.`}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-1.5">
            <label htmlFor="review-notes" className="text-sm font-medium">
              Notes for the record
            </label>
            <Textarea
              id="review-notes"
              rows={3}
              value={notes}
              placeholder="Why you kept what you kept. This is stored with the review."
              onChange={(event) => {
                setNotes(event.target.value)
              }}
            />
          </div>

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => {
                setConfirmOpen(false)
              }}
            >
              Keep reviewing
            </Button>
            <Button
              loading={submitReview.isPending}
              onClick={() => {
                submitReview.mutate(
                  {
                    notes: notes.trim() || null,
                    acceptedGapIds: accepted.map((gap) => gap.id),
                  },
                  {
                    onSuccess: () => {
                      setConfirmOpen(false)
                      if (!isRealProject) navigate(`/app/projects/${projectId}/pipeline`)
                    },
                  },
                )
              }}
            >
              {isRealProject ? 'Save review' : 'Approve and continue'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

type Filter = 'all' | 'proven' | 'test' | 'kept'

const FILTERS: Record<Filter, { label: string; keep: (gap: Gap) => boolean }> = {
  all: { label: 'All', keep: () => true },
  proven: { label: 'Proven', keep: (gap) => !gap.details?.unproven },
  test: {
    label: 'Worth trying',
    keep: (gap) => Boolean(gap.details?.unproven),
  },
  kept: { label: 'Kept', keep: (gap) => gap.decision === 'accepted' },
}
