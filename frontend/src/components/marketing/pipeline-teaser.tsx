import { useEffect, useState } from 'react'
import { PipelineStepper } from '@/components/pipeline/pipeline-stepper'
import type { PipelineState, StageId, StageState } from '@/types/pipeline'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'

const STAGE_MESSAGES: Partial<Record<StageId, string>> = {
  2: 'Collecting competitor pages and social posts…',
  3: 'Embedding 196 chunks into the vector store…',
  4: 'Comparing your brand against three competitors…',
  6: 'Critic challenging the Strategist’s first draft…',
  8: 'Assembling the strategy document…',
  9: 'Drafting follow-on content…',
}

function buildState(current: StageId, progress: number): PipelineState {
  const stages = {} as Record<StageId, StageState>
  for (let id = 1 as number; id <= 9; id += 1) {
    const stageId = id as StageId
    const isCheckpoint = stageId === 5 || stageId === 7
    let status: StageState['status'] = 'idle'
    if (stageId < current) status = 'complete'
    else if (stageId === current) status = isCheckpoint ? 'awaiting_human' : 'running'

    stages[stageId] = {
      id: stageId,
      status,
      progress: stageId === current ? progress : stageId < current ? 100 : 0,
      startedAt: null,
      completedAt: null,
      message:
        stageId === current
          ? isCheckpoint
            ? 'Waiting for your decision'
            : (STAGE_MESSAGES[stageId] ?? 'Working…')
          : null,
      error: null,
      metrics: null,
    }
  }
  return {
    projectId: 'teaser',
    currentStage: current,
    blockedOn: current === 5 || current === 7 ? current : null,
    stages,
    updatedAt: new Date().toISOString(),
  }
}

/**
 * A looping, self-driving run of the pipeline for the landing page. It is
 * decorative (no data, no network), and it pauses entirely for anyone who
 * prefers reduced motion, showing a completed run instead.
 */
export function PipelineTeaser() {
  const reduced = usePrefersReducedMotion()
  const [current, setCurrent] = useState<StageId>(2)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (reduced) return undefined

    const timer = setInterval(() => {
      setProgress((value) => {
        // Human checkpoints linger, so the "waiting on you" state is noticed.
        const step = current === 5 || current === 7 ? 2.2 : 4.5
        const next = value + step
        if (next < 100) return next

        setCurrent((stage) => (stage >= 9 ? 2 : ((stage + 1) as StageId)))
        return 0
      })
    }, 90)

    return () => {
      clearInterval(timer)
    }
  }, [current, reduced])

  const state = reduced ? buildState(9, 100) : buildState(current, progress)

  return (
    <div aria-hidden="true">
      <PipelineStepper pipeline={state} orientation="horizontal" />
    </div>
  )
}
