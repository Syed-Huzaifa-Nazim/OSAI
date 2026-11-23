import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { AlertTriangle, ArrowRight, ScanSearch, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'

/** What the Instagram analysis really does, in the order it does it (engine layers 1-6). */
const INSTAGRAM_STEPS = [
  'Reading your posts and your competitor’s',
  'Comparing reels, photos and carousels',
  'Checking when each account posts (Pakistan time)',
  'Reading every caption with our caption model',
  'Looking at each picture: faces, jewellery worn or on display',
  'Watching the first 3 seconds of every reel',
  'Scoring picture quality with our trained model',
  'Comparing you with other jewellery shops on Instagram',
  'Testing which differences are real, not chance',
]

/** What the Daraz analysis really does, in order (DarazInsightAgent + the Daraz Gap Engine). */
const DARAZ_STEPS = [
  'Finding the search word buyers use for your listing',
  'Reading the top 80 Daraz results for that word, with ranks',
  'Reading both listings: price, offers, photos and options',
  'Looking at each main photo with our picture model',
  'Reading the newest reviews with the review models',
  'Comparing you with the top 20 listings for that word',
  'Keeping only changes proven to go with rank and sales',
]

const KINDS = {
  instagram: {
    steps: INSTAGRAM_STEPS,
    time: 'This usually takes 5 to 12 minutes, because every reel is downloaded and watched.',
  },
  daraz: {
    steps: DARAZ_STEPS,
    time: 'This usually takes 1 to 3 minutes: Daraz search, both listings and their reviews are read live.',
  },
} as const

function clock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

/** Pulsing rings and a turning scanner while the analysis runs. */
function Scanner() {
  const reduced = useReducedMotion()
  return (
    <div className="relative mx-auto flex size-36 items-center justify-center" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="absolute inset-0 rounded-full border-2 border-primary/30"
          initial={{ scale: 0.5, opacity: 0.8 }}
          animate={reduced ? { opacity: 0.4 } : { scale: 1.15, opacity: 0 }}
          transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.8, ease: 'easeOut' }}
        />
      ))}
      <motion.svg
        viewBox="0 0 100 100"
        className="absolute inset-3"
        animate={reduced ? undefined : { rotate: 360 }}
        transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
      >
        <defs>
          <linearGradient id="scan-arc" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="hsl(var(--primary))" stopOpacity="0" />
            <stop offset="1" stopColor="hsl(var(--primary))" />
          </linearGradient>
        </defs>
        <circle
          cx="50"
          cy="50"
          r="44"
          fill="none"
          stroke="url(#scan-arc)"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray="90 200"
        />
      </motion.svg>
      <span className="relative flex size-20 items-center justify-center rounded-full bg-primary/10 text-primary shadow-glow">
        <ScanSearch className="size-9" />
      </span>
    </div>
  )
}

/** A green circle that pops in and draws its check mark. */
function SuccessCheck() {
  return (
    <motion.div
      className="mx-auto flex size-28 items-center justify-center rounded-full bg-success/15"
      initial={{ scale: 0.4, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 260, damping: 16 }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 52 52" className="size-20">
        <motion.circle
          cx="26"
          cy="26"
          r="24"
          fill="none"
          stroke="hsl(var(--success))"
          strokeWidth="3"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
        <motion.path
          d="M15 27 l7 7 l15 -16"
          fill="none"
          stroke="hsl(var(--success))"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.45, delay: 0.4, ease: 'easeOut' }}
        />
      </svg>
    </motion.div>
  )
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  state: 'running' | 'done' | 'failed'
  /** The stage's own line, e.g. "3 gaps identified". */
  message?: string | null
  error?: string | null
  reviewPath: string
  /** Which analysis runs; it decides the steps and the time shown. */
  kind?: keyof typeof KINDS
  /** Stops the analysis; nothing from it is saved and the earlier gaps stay. */
  onCancel?: () => void
  cancelling?: boolean
}

/** Shown while "Find gaps" runs: what is happening now, then a green check and the way to the gaps. */
export function FindGapsDialog({
  open,
  onOpenChange,
  state,
  message,
  error,
  reviewPath,
  kind = 'instagram',
  onCancel,
  cancelling = false,
}: Props) {
  const { steps: STEPS, time } = KINDS[kind]
  const [step, setStep] = useState(0)
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    if (!open || state !== 'running') return
    setSeconds(0)
    setStep(0)
    const tick = window.setInterval(() => {
      setSeconds((s) => s + 1)
    }, 1000)
    const next = window.setInterval(() => {
      setStep((s) => (s + 1) % STEPS.length)
    }, 3200)
    return () => {
      window.clearInterval(tick)
      window.clearInterval(next)
    }
  }, [open, state, STEPS.length])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md overflow-hidden text-center">
        {state === 'running' ? (
          <div className="space-y-5 py-2">
            <Scanner />
            <div>
              <DialogTitle className="text-xl">Finding your gaps</DialogTitle>
              <DialogDescription className="mt-1">{time}</DialogDescription>
            </div>
            <div
              className="relative h-12 overflow-hidden rounded-2xl bg-primary/5"
              aria-live="polite"
            >
              <AnimatePresence mode="wait">
                <motion.p
                  key={step}
                  initial={{ y: 18, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: -18, opacity: 0 }}
                  transition={{ duration: 0.35 }}
                  className="absolute inset-0 flex items-center justify-center px-4 text-sm font-medium text-primary"
                >
                  {STEPS[step]}…
                </motion.p>
              </AnimatePresence>
            </div>
            <div className="flex justify-center gap-1.5" aria-hidden="true">
              {STEPS.map((s, i) => (
                <span
                  key={s}
                  className={`h-1.5 rounded-full transition-all ${i === step ? 'w-6 bg-primary' : 'w-1.5 bg-primary/25'}`}
                />
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              {clock(seconds)} so far · you can close this window, the analysis keeps going
            </p>
            {onCancel ? (
              <div className="space-y-1">
                <Button variant="outline" size="sm" onClick={onCancel} loading={cancelling}>
                  <X />
                  Cancel analysis
                </Button>
                <p className="text-xs text-muted-foreground">
                  Nothing from this run is saved; your earlier gaps stay as they were.
                </p>
              </div>
            ) : null}
          </div>
        ) : state === 'done' ? (
          <div className="space-y-5 py-2">
            <SuccessCheck />
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <DialogTitle className="text-xl">Analysis complete</DialogTitle>
              <DialogDescription className="mt-1">
                {message ? `${message}. ` : ''}Keep the ones that matter to your shop and drop the
                rest.
              </DialogDescription>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
            >
              <Button asChild size="lg" className="rounded-full">
                <Link to={reviewPath}>
                  Review gaps <ArrowRight />
                </Link>
              </Button>
            </motion.div>
          </div>
        ) : (
          <div className="space-y-4 py-2">
            <span className="mx-auto flex size-20 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <AlertTriangle className="size-9" aria-hidden="true" />
            </span>
            <DialogTitle className="text-xl">The analysis stopped</DialogTitle>
            <DialogDescription>
              {error ?? 'Something went wrong. Please try again.'}
            </DialogDescription>
            <Button
              variant="outline"
              onClick={() => {
                onOpenChange(false)
              }}
            >
              Close
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
