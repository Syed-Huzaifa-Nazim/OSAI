import { Link } from 'react-router-dom'
import { ArrowRight, UserRoundCheck } from 'lucide-react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { getStage } from '@/lib/pipeline-stages'
import { cn } from '@/lib/utils'
import { spring } from '@/lib/motion'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import type { StageId } from '@/types/pipeline'

interface HitlCalloutProps {
  projectId: string
  stage: Extract<StageId, 5 | 7>
  className?: string
}

/**
 * The "the system is waiting on you" surface. Deliberately loud: the whole
 * trust argument of the product rests on these two moments being noticed
 * rather than clicked past.
 */
export function HitlCallout({ projectId, stage, className }: HitlCalloutProps) {
  const reduced = usePrefersReducedMotion()
  const definition = getStage(stage)

  const copy =
    stage === 5
      ? {
          title: 'Your review is needed: gap refinement',
          body: 'The Insight Agent has finished. Review the gaps it found, keep the ones that matter to your business, and drop the rest before any strategy is written.',
          cta: 'Review gaps',
        }
      : {
          title: 'Your approval is needed: final strategy',
          body: 'The Strategist has drafted a strategy and the Critic has challenged it. Read both, then approve it for execution or send it back for revision.',
          cta: 'Review strategy',
        }

  return (
    <motion.aside
      initial={reduced ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={spring}
      className={cn(
        'glass relative overflow-hidden rounded-lg border-brand-butter-cream/35 p-5',
        className,
      )}
    >
      {!reduced ? (
        <motion.span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-gradient-to-r from-brand-butter-cream/12 via-transparent to-transparent"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }}
        />
      ) : null}

      <div className="relative flex flex-wrap items-start gap-4">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-butter-cream/20 text-brand-butter-cream">
          <UserRoundCheck className="size-5" />
        </span>
        <div className="min-w-0 flex-1 space-y-1.5">
          <p className="eyebrow text-brand-butter-cream/80">
            Human checkpoint · Stage {definition.id}
          </p>
          <h3 className="font-display text-base font-semibold">{copy.title}</h3>
          <p className="max-w-2xl text-sm text-muted-foreground">{copy.body}</p>
        </div>
        <Button asChild variant="secondary" className="shrink-0">
          <Link to={`/app/projects/${projectId}/${definition.route}`}>
            {copy.cta}
            <ArrowRight />
          </Link>
        </Button>
      </div>
    </motion.aside>
  )
}
