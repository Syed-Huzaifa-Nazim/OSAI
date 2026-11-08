import { ExternalLink, Quote } from 'lucide-react'
import { motion } from 'framer-motion'
import type { Evidence } from '@/types/domain'
import { cn, formatPercent, prettyUrl } from '@/lib/utils'
import { staggerContainer, staggerItem } from '@/lib/motion'

/**
 * The evidence trail behind a claim. Nothing the agents assert is rendered
 * without one of these: it is the difference between this product and a
 * generic suggestion engine.
 */
export function EvidenceList({
  evidence,
  className,
}: {
  evidence: Evidence[]
  className?: string
}) {
  if (evidence.length === 0) {
    return (
      <p className={cn('text-xs italic text-muted-foreground', className)}>
        No supporting source was attached to this claim.
      </p>
    )
  }

  return (
    <motion.ul
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className={cn('space-y-2.5', className)}
    >
      {evidence.map((item) => (
        <motion.li
          key={`${item.sourceId}-${item.quote.slice(0, 24)}`}
          variants={staggerItem}
          className="rounded-md border border-border/20 bg-muted/30 p-3"
        >
          <div className="flex items-start gap-2.5">
            <Quote className="mt-0.5 size-3.5 shrink-0 text-primary/70" aria-hidden="true" />
            <div className="min-w-0 space-y-2">
              <p className="text-sm leading-relaxed text-foreground/90">{item.quote}</p>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <a
                  href={item.sourceUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  {prettyUrl(item.sourceUrl)}
                  <ExternalLink className="size-3" aria-hidden="true" />
                </a>
                <span aria-hidden="true">·</span>
                <span>{item.sourceTitle}</span>
                <span aria-hidden="true">·</span>
                <span className="font-mono tabular-nums">
                  {formatPercent(item.relevance)} match
                </span>
              </div>
            </div>
          </div>
        </motion.li>
      ))}
    </motion.ul>
  )
}
