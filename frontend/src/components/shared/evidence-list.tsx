import { ExternalLink, Image as ImageIcon, Quote } from 'lucide-react'
import { motion } from 'framer-motion'
import type { Evidence } from '@/types/domain'
import { cn, formatPercent, prettyUrl } from '@/lib/utils'
import { staggerContainer, staggerItem } from '@/lib/motion'
import { SafeImage } from './safe-image'

/**
 * The evidence trail behind a claim. Nothing the agents assert is rendered
 * without one of these: it is the difference between this product and a
 * generic suggestion engine.
 */
export function EvidenceList({
  evidence,
  className,
  sourceThumbnails,
}: {
  evidence: Evidence[]
  className?: string
  sourceThumbnails?: Record<string, string>
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
          className="rounded-xl border border-primary/15 bg-gradient-to-br from-amber-50/80 via-white/70 to-emerald-50/70 p-3 shadow-sm dark:from-amber-950/20 dark:via-card dark:to-emerald-950/20"
        >
          <div className="flex items-start gap-3">
            {sourceThumbnails?.[item.sourceId] ? (
              <SafeImage
                src={sourceThumbnails?.[item.sourceId] ?? ''}
                alt={`${item.sourceTitle} thumbnail`}
                className="size-[76px] shrink-0 rounded-lg border border-white/80 shadow-sm"
                fit="cover"
              />
            ) : (
              <span className="flex size-[76px] shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-amber-300 via-orange-300 to-emerald-300 text-white shadow-sm">
                <ImageIcon className="size-6 drop-shadow" aria-hidden="true" />
              </span>
            )}
            <div className="min-w-0 flex-1 space-y-2">
              <p className="flex items-start gap-2 text-sm leading-relaxed text-foreground">
                <Quote className="mt-0.5 size-3.5 shrink-0 text-primary/80" aria-hidden="true" />
                <span>{item.quote}</span>
              </p>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <a
                  href={item.sourceUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  Open source: {prettyUrl(item.sourceUrl)}
                  <ExternalLink className="size-3" aria-hidden="true" />
                </a>
                <span aria-hidden="true">·</span>
                <span>{item.sourceTitle}</span>
                <span aria-hidden="true">·</span>
                <span className="rounded-full bg-white/70 px-2 py-0.5 font-medium text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
                  Evidence strength {formatPercent(item.relevance)}
                </span>
              </div>
            </div>
          </div>
        </motion.li>
      ))}
    </motion.ul>
  )
}
