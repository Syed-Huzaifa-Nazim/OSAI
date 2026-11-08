import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCheck, Info, ListChecks, ShieldCheck, UserRoundCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { PageHeader } from '@/components/shared/page-header'
import { GapCard } from '@/components/shared/gap-card'
import { AnalysisSummary } from '@/components/shared/analysis-summary'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { useGaps, useSubmitGapReview, useUpdateGap } from '@/hooks/use-insights'
import { usePipeline } from '@/hooks/use-pipeline'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { staggerContainer, spring } from '@/lib/motion'
import type { GapPriority } from '@/types/domain'

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

  useDocumentTitle(project.data ? `${project.data.brandName} · Review gaps` : 'Review gaps')

  const { accepted, rejected, pending } = useMemo(() => {
    const list = gaps ?? []
    return {
      accepted: list.filter((gap) => gap.decision === 'accepted'),
      rejected: list.filter((gap) => gap.decision === 'rejected'),
      pending: list.filter((gap) => gap.decision === 'pending'),
    }
  }, [gaps])

  const alreadyReviewed = pipeline.data
    ? pipeline.data.stages[5].status === 'complete'
    : false
  const canSubmit = pending.length === 0 && accepted.length > 0 && !alreadyReviewed
  // Real projects stop at this checkpoint: stages 6-9 are not built yet.
  const isRealProject = project.data ? !project.data.isDemo : false
  const explainProjectId =
    isRealProject && project.data?.socialPlatform === 'instagram' ? projectId : undefined
  const analysisNotes = pipeline.data?.stages[4]?.metrics?.notes ?? []
  const analysisParts = pipeline.data?.stages[4]?.metrics?.analysis ?? []

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
    <div className="space-y-7">
      <PageHeader
        eyebrow="Stage 5 · Human checkpoint"
        title="Refine the gaps"
        description={
          isRealProject
            ? 'Keep what is real for this business and drop what is not. Use Explain to see the posts behind a gap.'
            : 'Keep what is real for this business and drop what is not. Only the gaps you keep reach the Strategist.'
        }
      />

      {analysisParts.length > 0 ? <AnalysisSummary parts={analysisParts} /> : null}

      {analysisNotes.length > 0 ? (
        <Card className="flex gap-3 border-border/30 p-4">
          <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-medium">Notes from the analysis</p>
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
      ) : (gaps ?? []).length === 0 ? (
        <EmptyState
          title="There is nothing to review yet"
          description="The Insight Agent has not produced any gaps for this project. Run the pipeline first."
          icon={<ListChecks className="size-5" />}
          action={
            <Button asChild variant="outline">
              <Link to={`/app/projects/${projectId}/pipeline`}>Go to the pipeline</Link>
            </Button>
          }
        />
      ) : (
        <>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
          >
            <Card glass className="flex flex-wrap items-center gap-5 p-5">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-butter-cream/20 text-brand-butter-cream">
                <UserRoundCheck className="size-5" />
              </span>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <Stat label="To triage" value={pending.length} accent={pending.length > 0} />
                <Stat label="Keeping" value={accepted.length} />
                <Stat label="Dropping" value={rejected.length} />
              </div>
              <div className="ml-auto">
                <Button
                  disabled={!canSubmit}
                  onClick={() => {
                    setConfirmOpen(true)
                  }}
                >
                  <CheckCheck />
                  Submit review
                </Button>
              </div>
            </Card>
          </motion.div>

          {pending.length > 0 && !alreadyReviewed ? (
            <p className="text-sm text-muted-foreground">
              {pending.length} gap{pending.length === 1 ? '' : 's'} still need a decision. Every gap
              has to be kept or dropped before this checkpoint can close.
            </p>
          ) : null}

          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="space-y-4"
          >
            {(gaps ?? []).map((gap) => (
              <GapCard
                key={gap.id}
                gap={gap}
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
            ))}
          </motion.div>
        </>
      )}

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
                  { notes: notes.trim() || null, acceptedGapIds: accepted.map((gap) => gap.id) },
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

function Stat({ label, value, accent = false }: { label: string; value: number; accent?: boolean }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-0.5 flex items-center gap-2 font-display text-xl font-semibold tabular-nums">
        {value}
        {accent && value > 0 ? <Badge variant="secondary">Action needed</Badge> : null}
      </p>
    </div>
  )
}
