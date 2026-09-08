import { ArrowRight, CircleCheck, CircleSlash, ShieldAlert, Wrench } from 'lucide-react'
import { motion } from 'framer-motion'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { CriticFeedback, CriticVerdict } from '@/types/domain'
import { cn, titleCase } from '@/lib/utils'
import { staggerContainer, staggerItem } from '@/lib/motion'

const VERDICT: Record<
  CriticVerdict,
  { icon: typeof Wrench; label: string; className: string; badge: 'default' | 'secondary' | 'success' | 'destructive' }
> = {
  strengthened: {
    icon: Wrench,
    label: 'Strengthened',
    className: 'text-primary',
    badge: 'default',
  },
  challenged: {
    icon: ShieldAlert,
    label: 'Challenged',
    className: 'text-brand-butter-cream',
    badge: 'secondary',
  },
  rejected: {
    icon: CircleSlash,
    label: 'Rejected',
    className: 'text-destructive',
    badge: 'destructive',
  },
  approved: {
    icon: CircleCheck,
    label: 'Approved as drafted',
    className: 'text-success',
    badge: 'success',
  },
}

/**
 * The Critic transparency surface.
 *
 * "Reduces hallucinated and misleading insights" is the product's central
 * claim, and this panel is the evidence for it: what the Strategist wrote
 * first, what the Critic did about it, and why. Showing only the polished
 * output would make the claim unverifiable.
 */
export function CriticPanel({
  feedback,
  className,
  /** Filters to one initiative; omit for the whole strategy. */
  initiativeId,
}: {
  feedback: CriticFeedback[]
  className?: string
  initiativeId?: string | null
}) {
  const items =
    initiativeId === undefined
      ? feedback
      : feedback.filter((item) => item.targetInitiativeId === initiativeId)

  if (items.length === 0) {
    return (
      <p className={cn('text-sm text-muted-foreground', className)}>
        The Critic did not flag anything here.
      </p>
    )
  }

  return (
    <motion.ul
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className={cn('space-y-3', className)}
    >
      {items.map((item) => {
        const verdict = VERDICT[item.verdict]
        const Icon = verdict.icon
        return (
          <motion.li key={item.id} variants={staggerItem}>
            <Card className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Icon className={cn('size-4', verdict.className)} aria-hidden="true" />
                <Badge variant={verdict.badge}>{verdict.label}</Badge>
                <Badge variant="outline">{titleCase(item.dimension)}</Badge>
                {item.severity === 'major' ? <Badge variant="destructive">Major</Badge> : null}
              </div>

              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{item.comment}</p>

              {item.before ? (
                <div className="mt-4 space-y-2">
                  <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3">
                    <p className="text-[11px] uppercase tracking-wide text-destructive">
                      Strategist&rsquo;s draft
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground line-through decoration-destructive/40">
                      {item.before}
                    </p>
                  </div>

                  {item.after ? (
                    <>
                      <div className="flex justify-center">
                        <ArrowRight
                          className="size-4 rotate-90 text-muted-foreground/50"
                          aria-hidden="true"
                        />
                      </div>
                      <div className="rounded-md border border-success/25 bg-success/5 p-3">
                        <p className="text-[11px] uppercase tracking-wide text-success">
                          After the Critic
                        </p>
                        <p className="mt-1 text-sm text-muted-foreground">{item.after}</p>
                      </div>
                    </>
                  ) : (
                    <p className="text-xs italic text-muted-foreground">
                      Removed from the strategy entirely.
                    </p>
                  )}
                </div>
              ) : null}
            </Card>
          </motion.li>
        )
      })}
    </motion.ul>
  )
}
