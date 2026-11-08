import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Check, RotateCcw, ShieldCheck, ShieldAlert, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { PageHeader } from '@/components/shared/page-header'
import { InitiativeCard } from '@/components/shared/initiative-card'
import { CriticPanel } from '@/components/shared/critic-panel'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { useStrategy, useSubmitStrategyReview, useReviews } from '@/hooks/use-insights'
import { usePipeline } from '@/hooks/use-pipeline'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { formatDate, titleCase } from '@/lib/utils'
import { spring, staggerContainer } from '@/lib/motion'
import type { ReviewDecision } from '@/types/domain'

/**
 * HITL checkpoint #2 (stage 7).
 *
 * Approving releases stage 8. Requesting a revision sends the strategy back to
 * the Strategist and Critic, which produces a new version, so a rejection is
 * never a dead end.
 */
export default function ReviewStrategyPage() {
  const projectId = useProjectId()
  const navigate = useNavigate()
  const project = useProject(projectId)
  const pipeline = usePipeline(projectId)
  const reviews = useReviews(projectId)
  const { data: strategy, isLoading, isError, error, refetch } = useStrategy(projectId)
  const submitReview = useSubmitStrategyReview(projectId)
  const [decision, setDecision] = useState<ReviewDecision | null>(null)
  const [notes, setNotes] = useState('')

  useDocumentTitle(project.data ? `${project.data.brandName} · Final approval` : 'Final approval')

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

  if (isLoading) return <LoadingState rows={4} />

  if (!strategy) {
    return (
      <div className="space-y-7">
        <PageHeader
          eyebrow="Stage 7 · Human checkpoint"
          title="Final approval"
          description="The last gate before a strategy becomes a document."
        />
        <EmptyState
          title="There is no strategy to approve yet"
          description="Stage 6 has to produce a strategy before this checkpoint opens."
          icon={<ShieldCheck className="size-5" />}
          action={
            <Button asChild variant="outline">
              <Link to={`/app/projects/${projectId}/pipeline`}>Go to the pipeline</Link>
            </Button>
          }
        />
      </div>
    )
  }

  const closed = pipeline.data ? pipeline.data.stages[7].status === 'complete' : false
  const priorReview = (reviews.data ?? []).find((review) => review.stage === 7)
  const majorInterventions = strategy.criticFeedback.filter((item) => item.severity === 'major')

  const copy: Record<ReviewDecision, { title: string; body: string; cta: string }> = {
    approved: {
      title: 'Approve this strategy for execution?',
      body: 'Stage 8 will assemble the full strategy document, and stage 9 will map content assets to these initiatives.',
      cta: 'Approve strategy',
    },
    revision_requested: {
      title: 'Send this back for revision?',
      body: 'The Strategist and Critic will produce a new version against the same gaps. Your notes below become part of their brief.',
      cta: 'Request revision',
    },
    rejected: {
      title: 'Reject this strategy?',
      body: 'The strategy is discarded and stage 6 runs again from the gaps you prioritised. Your notes below become part of the brief.',
      cta: 'Reject and regenerate',
    },
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Stage 7 · Human checkpoint"
        title="Final approval"
        description="Read it with the Critic's objections in view, then decide whether it ships."
      />

      {closed && priorReview ? (
        <Card className="flex flex-wrap items-center gap-4 border-success/30 bg-success/5 p-5">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-success/15 text-success">
            <ShieldCheck className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-display text-sm font-semibold">
              {titleCase(priorReview.decision)} on {formatDate(priorReview.createdAt)}
            </p>
            {priorReview.notes ? (
              <p className="mt-0.5 text-sm text-muted-foreground">{priorReview.notes}</p>
            ) : null}
          </div>
          <Button asChild variant="outline">
            <Link to={`/app/projects/${projectId}/document`}>View the document</Link>
          </Button>
        </Card>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={spring}
        >
          <Card glass className="border-brand-butter-cream/35 p-5">
            <div className="flex flex-wrap items-center gap-4">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-butter-cream/20 text-brand-butter-cream">
                <ShieldCheck className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-display text-sm font-semibold">Your decision</p>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {strategy.initiatives.length} initiatives, {strategy.criticFeedback.length} critic
                  interventions
                  {majorInterventions.length > 0
                    ? `, ${majorInterventions.length} of them major`
                    : ''}
                  .
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setDecision('rejected')
                  }}
                >
                  <X />
                  Reject
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setDecision('revision_requested')
                  }}
                >
                  <RotateCcw />
                  Request revision
                </Button>
                <Button
                  onClick={() => {
                    setDecision('approved')
                  }}
                >
                  <Check />
                  Approve
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      <Card glass className="p-6">
        <div className="flex flex-wrap items-center gap-2">
          <p className="eyebrow">Executive summary</p>
          <Badge variant="outline">Version {strategy.version}</Badge>
        </div>
        <p className="mt-3 text-base leading-relaxed">{strategy.executiveSummary}</p>
      </Card>

      <section className="space-y-4">
        <h2 className="font-display text-lg font-semibold">Initiatives</h2>
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="space-y-4"
        >
          {strategy.initiatives.map((initiative, index) => (
            <InitiativeCard
              key={initiative.id}
              initiative={initiative}
              index={index}
              feedback={strategy.criticFeedback}
            />
          ))}
        </motion.div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="size-4 text-primary" />
          <h2 className="font-display text-lg font-semibold">What the Critic objected to</h2>
        </div>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Read this before deciding. These are the points where the two agents disagreed, the
          places where a strategy is most likely to be wrong.
        </p>
        <CriticPanel feedback={strategy.criticFeedback} />
      </section>

      <Dialog
        open={decision !== null}
        onOpenChange={(open) => {
          if (!open) setDecision(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{decision ? copy[decision].title : ''}</DialogTitle>
            <DialogDescription>{decision ? copy[decision].body : ''}</DialogDescription>
          </DialogHeader>

          <div className="space-y-1.5">
            <label htmlFor="strategy-notes" className="text-sm font-medium">
              Notes
              {decision === 'approved' ? (
                <span className="ml-1 text-muted-foreground">(optional)</span>
              ) : null}
            </label>
            <Textarea
              id="strategy-notes"
              rows={3}
              value={notes}
              placeholder={
                decision === 'approved'
                  ? 'Anything worth recording alongside the approval.'
                  : 'What needs to change? The agents read this.'
              }
              onChange={(event) => {
                setNotes(event.target.value)
              }}
            />
          </div>

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => {
                setDecision(null)
              }}
            >
              Cancel
            </Button>
            <Button
              variant={decision === 'approved' ? 'default' : 'destructive'}
              loading={submitReview.isPending}
              onClick={() => {
                if (!decision) return
                submitReview.mutate(
                  { decision, notes: notes.trim() || null, flaggedIds: [] },
                  {
                    onSuccess: () => {
                      setDecision(null)
                      setNotes('')
                      navigate(`/app/projects/${projectId}/pipeline`)
                    },
                  },
                )
              }}
            >
              {decision ? copy[decision].cta : ''}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
