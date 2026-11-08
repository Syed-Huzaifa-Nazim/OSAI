import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import type { PipelineState, StageId } from '@/types/pipeline'
import { PIPELINE_STAGES } from '@/lib/pipeline-stages'
import { cn } from '@/lib/utils'
import { useIsDesktop } from '@/hooks/use-media-query'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { staggerContainer, staggerItem } from '@/lib/motion'
import { StageCard } from './stage-card'
import { StageConnector } from './stage-connector'

interface PipelineStepperProps {
  pipeline: PipelineState
  selectedStage?: StageId | null
  onSelectStage?: (stage: StageId) => void
  /** Force an orientation instead of deriving it from the viewport. */
  orientation?: 'horizontal' | 'vertical'
  className?: string
}

/**
 * The signature interaction: all nine stages, their live status, and the
 * connectors between them. Horizontal on desktop (scrolls, and auto-scrolls to
 * follow the active stage), vertical below lg.
 */
export function PipelineStepper({
  pipeline,
  selectedStage,
  onSelectStage,
  orientation,
  className,
}: PipelineStepperProps) {
  const isDesktop = useIsDesktop()
  const reduced = usePrefersReducedMotion()
  const resolved = orientation ?? (isDesktop ? 'horizontal' : 'vertical')
  const isHorizontal = resolved === 'horizontal'
  const scrollRef = useRef<HTMLDivElement>(null)
  const activeRef = useRef<HTMLDivElement>(null)

  // Keep the active stage in view as the run progresses.
  //
  // This scrolls the strip itself rather than calling scrollIntoView, which
  // walks up to the nearest scrollable ancestor, the document, and yanks the
  // whole window. On the landing page the teaser advances a stage every couple
  // of seconds, so that made the page unscrollable: every attempt to read down
  // the page was undone by the next tick.
  useEffect(() => {
    if (!isHorizontal) return

    const container = scrollRef.current
    const active = activeRef.current
    if (!container || !active) return

    const containerRect = container.getBoundingClientRect()
    const activeRect = active.getBoundingClientRect()
    const offsetFromLeft = activeRect.left - containerRect.left
    const centred = offsetFromLeft - (containerRect.width - activeRect.width) / 2
    const left = Math.max(0, container.scrollLeft + centred)

    // Element.scrollTo is not universally available, and an exception thrown
    // from this effect would take the whole page down with it. The stepper is
    // decorative on the landing page, so it must never be able to do that.
    if (typeof container.scrollTo === 'function') {
      container.scrollTo({ left, behavior: reduced ? 'auto' : 'smooth' })
    } else {
      container.scrollLeft = left
    }
  }, [pipeline.currentStage, isHorizontal, reduced])

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      ref={scrollRef}
      role="list"
      aria-label="Analysis pipeline"
      className={cn(
        isHorizontal
          ? 'no-scrollbar flex items-stretch overflow-x-auto pb-2'
          : 'flex flex-col',
        className,
      )}
    >
      {PIPELINE_STAGES.map((definition, index) => {
        const state = pipeline.stages[definition.id]
        const previous = index > 0 ? pipeline.stages[PIPELINE_STAGES[index - 1]!.id] : null
        const isActive = pipeline.currentStage === definition.id

        return (
          <div
            key={definition.id}
            role="listitem"
            ref={isActive ? activeRef : undefined}
            className={cn('flex', isHorizontal ? 'items-center' : 'flex-col')}
          >
            {index > 0 ? (
              <StageConnector
                orientation={resolved}
                active={previous?.status === 'complete'}
                flowing={state.status === 'running'}
              />
            ) : null}
            <motion.div variants={staggerItem} className={isHorizontal ? undefined : 'w-full'}>
              <StageCard
                definition={definition}
                state={state}
                orientation={resolved}
                selected={selectedStage === definition.id}
                {...(onSelectStage
                  ? {
                      onSelect: () => {
                        onSelectStage(definition.id)
                      },
                    }
                  : {})}
              />
            </motion.div>
          </div>
        )
      })}
    </motion.div>
  )
}
