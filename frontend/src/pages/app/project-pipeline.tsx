import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Coins, Play, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { PageHeader } from '@/components/shared/page-header'
import { ProjectStatusBadge } from '@/components/shared/project-status-badge'
import { DemoBadge } from '@/components/shared/demo-badge'
import { ErrorState, LoadingState } from '@/components/shared/state-views'
import { PipelineStepper } from '@/components/pipeline/pipeline-stepper'
import { StageDetail } from '@/components/pipeline/stage-detail'
import { HitlCallout } from '@/components/pipeline/hitl-callout'
import { SourceMixChart } from '@/components/charts/source-mix-chart'
import { CostByStageChart } from '@/components/charts/cost-by-stage-chart'
import { usePipeline, useResetPipeline, useSources, useStartPipeline } from '@/hooks/use-pipeline'
import { useProject } from '@/hooks/use-projects'
import { useRunCost } from '@/hooks/use-automation'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { getStage } from '@/lib/pipeline-stages'
import { errorMessage } from '@/lib/api-client'
import { formatUsd } from '@/lib/utils'
import { spring } from '@/lib/motion'
import type { StageId } from '@/types/pipeline'

export default function PipelinePage() {
  const projectId = useProjectId()
  const project = useProject(projectId)
  const pipeline = usePipeline(projectId)
  const sources = useSources(projectId)
  const cost = useRunCost(projectId)
  const startPipeline = useStartPipeline(projectId)
  const resetPipeline = useResetPipeline(projectId)
  const [selected, setSelected] = useState<StageId | null>(null)
  const [confirmReset, setConfirmReset] = useState(false)

  useDocumentTitle(project.data ? `${project.data.brandName} · Pipeline` : 'Pipeline')

  // Follow the run: keep the detail panel on whatever stage is active, until
  // the user picks one themselves.
  const [userPicked, setUserPicked] = useState(false)
  useEffect(() => {
    if (!userPicked && pipeline.data) setSelected(pipeline.data.currentStage)
  }, [pipeline.data, userPicked])

  if (pipeline.isError || project.isError) {
    return (
      <ErrorState
        message={errorMessage(pipeline.error ?? project.error)}
        onRetry={() => {
          void pipeline.refetch()
          void project.refetch()
        }}
      />
    )
  }

  if (pipeline.isLoading || project.isLoading || !pipeline.data || !project.data) {
    return (
      <div className="space-y-6">
        <LoadingState rows={1} />
        <LoadingState rows={2} />
      </div>
    )
  }

  const state = pipeline.data
  const notStarted = state.stages[2].status === 'idle'
  const blockedOn = state.blockedOn
  const activeStage = selected ?? state.currentStage

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="The run"
        title={project.data.brandName}
        description="Nine stages, live. Select any stage to see what it produced."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {project.data.isDemo ? <DemoBadge /> : null}
            <ProjectStatusBadge status={project.data.status} />
            {notStarted ? (
              <Button
                loading={startPipeline.isPending}
                onClick={() => {
                  startPipeline.mutate()
                }}
              >
                <Play />
                Start pipeline
              </Button>
            ) : (
              <Button
                variant="outline"
                onClick={() => {
                  setConfirmReset(true)
                }}
              >
                <RotateCcw />
                Reset
              </Button>
            )}
          </div>
        }
      />

      {blockedOn === 5 || blockedOn === 7 ? (
        <HitlCallout projectId={projectId} stage={blockedOn} />
      ) : null}

      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring}
        aria-label="Pipeline stages"
      >
        <PipelineStepper
          pipeline={state}
          selectedStage={activeStage}
          onSelectStage={(stage) => {
            setSelected(stage)
            setUserPicked(true)
          }}
        />
      </motion.section>

      <StageDetail
        projectId={projectId}
        definition={getStage(activeStage)}
        state={state.stages[activeStage]}
      />

      <div className="grid gap-5 lg:grid-cols-2">
        {sources.data && sources.data.length > 0 ? (
          <SourceMixChart sources={sources.data} />
        ) : (
          <Card className="flex items-center p-6">
            <p className="text-sm text-muted-foreground">
              Source breakdown appears once the Scout Agent has finished collecting.
            </p>
          </Card>
        )}

        {cost.data && cost.data.byStage.length > 0 ? (
          <CostByStageChart cost={cost.data} />
        ) : (
          <Card className="flex items-start gap-3 p-6">
            <Coins className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Token and cost tracking appears once an agent stage has run. Total so far:{' '}
              {formatUsd(cost.data?.totalCostUsd ?? 0)}.
            </p>
          </Card>
        )}
      </div>

      <Dialog open={confirmReset} onOpenChange={setConfirmReset}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset this pipeline?</DialogTitle>
            <DialogDescription>
              Every stage returns to not-started, and the sources, gaps, strategy and document this
              run produced are cleared. The project itself and its competitor list are kept.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => {
                setConfirmReset(false)
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              loading={resetPipeline.isPending}
              onClick={() => {
                resetPipeline.mutate(undefined, {
                  onSuccess: () => {
                    setConfirmReset(false)
                    setUserPicked(false)
                  },
                })
              }}
            >
              Reset pipeline
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
