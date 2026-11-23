import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Logo } from '@/components/shared/logo'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { spring } from '@/lib/motion'

/**
 * The loader every scraper shows while it is working.
 *
 * One component for all four (Daraz, Alibaba, website, Instagram), so a fifth
 * needs no new loader: pass the lines that describe what that scraper is
 * actually doing. Nothing here is scraper-specific.
 *
 * Built from the pieces the app already has -- the brand mark, the primary
 * accent, the card surface, the shared spring -- rather than a generic spinner,
 * because it sits on screen for a minute or more and a spinner says nothing
 * about progress. The steps rotate so the wait reads as movement, and the bar
 * is deliberately indeterminate: a scrape cannot honestly report a percentage.
 */

/** How long each step is shown before the next one. */
const STEP_MS = 6000

interface ScrapeLoaderProps {
  /** Which half of the run is happening. */
  phase: 'scraping' | 'embedding'
  /** Lines shown in turn while scraping, most specific first. */
  steps: string[]
  /** The single line shown once the text is being embedded. */
  embedStep: string
  /** What is happening underneath, in one sentence. */
  description: string
  /** Shows a Cancel button: stops the run, and nothing from it is saved. */
  onCancel?: () => void
  cancelling?: boolean
}

export function ScrapeLoader({
  phase,
  steps,
  embedStep,
  description,
  onCancel,
  cancelling = false,
}: ScrapeLoaderProps) {
  const [step, setStep] = useState(0)
  const reduced = usePrefersReducedMotion()

  // Advance, then hold on the last line: a loop back to the first would claim
  // the run had started over.
  useEffect(() => {
    if (phase !== 'scraping' || steps.length < 2) return
    const timer = window.setInterval(() => {
      setStep((current) => Math.min(current + 1, steps.length - 1))
    }, STEP_MS)
    return () => {
      window.clearInterval(timer)
    }
  }, [phase, steps.length])

  const line = phase === 'scraping' ? (steps[step] ?? steps[0]) : embedStep

  return (
    <Card className="flex items-start gap-4 p-6" role="status" aria-live="polite">
      <div className="relative mt-0.5 flex size-11 shrink-0 items-center justify-center">
        {/* The pulse is the only motion on the mark itself, so the brand stays
            legible rather than spinning. */}
        {reduced ? null : (
          <motion.span
            aria-hidden="true"
            className="absolute inset-0 rounded-xl bg-primary/15"
            animate={{ scale: [1, 1.12, 1], opacity: [0.5, 0.9, 0.5] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}
        <span className="absolute inset-0 rounded-xl border border-primary/25 bg-primary/10" />
        <Logo markOnly className="relative" />
      </div>

      <div className="min-w-0 flex-1">
        <AnimatePresence mode="wait" initial={false}>
          <motion.h2
            key={line}
            initial={reduced ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduced ? undefined : { opacity: 0, y: -6 }}
            transition={spring}
            className="font-display text-base font-semibold"
          >
            {line}
          </motion.h2>
        </AnimatePresence>

        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        {onCancel ? (
          <p className="mt-1 text-xs text-muted-foreground">
            Taking too long? Cancel stops it; nothing from this run is saved.
          </p>
        ) : null}

        {/* Indeterminate: a scrape cannot honestly report a percentage. */}
        <div
          className="mt-4 h-1 w-full overflow-hidden rounded-full bg-border/30"
          aria-hidden="true"
        >
          {reduced ? (
            <div className="h-full w-1/3 rounded-full bg-primary/70" />
          ) : (
            <motion.div
              className="h-full w-1/3 rounded-full bg-primary"
              animate={{ x: ['-110%', '330%'] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
            />
          )}
        </div>

        {steps.length > 1 ? (
          <div className="mt-3 flex items-center gap-1.5" aria-hidden="true">
            {steps.map((item, index) => (
              <span
                key={item}
                className={
                  'h-1 w-6 rounded-full transition-colors ' +
                  (phase === 'embedding' || index <= step ? 'bg-primary/60' : 'bg-border/40')
                }
              />
            ))}
          </div>
        ) : null}
      </div>
      {onCancel ? (
        <Button variant="outline" size="sm" className="shrink-0" onClick={onCancel} loading={cancelling}>
          <X />
          Cancel
        </Button>
      ) : null}
    </Card>
  )
}
