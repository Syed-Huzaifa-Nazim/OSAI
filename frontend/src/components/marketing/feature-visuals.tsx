import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useInView, useReducedMotion } from 'framer-motion'
import { Check, FileText, Heart, ImageIcon, Lightbulb, Link2, Play, Sparkle, Stamp, X } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Small animated pictures for the Features page, one per step. Each shows what the step does, using made-up
 * placeholder content (no real account, post or result); the ones for steps that are not built are marked Preview.
 * They loop only while on screen, and sit still when the user prefers reduced motion.
 */

/** A ticking counter that only runs while the picture is on screen. */
function useTicker(count: number, ms: number) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { margin: '-40px' })
  const reduce = useReducedMotion()
  const [tick, setTick] = useState(0)
  useEffect(() => {
    if (!inView || reduce) return
    const timer = window.setInterval(() => {
      setTick((t) => (t + 1) % count)
    }, ms)
    return () => {
      window.clearInterval(timer)
    }
  }, [inView, reduce, count, ms])
  return { ref, tick: reduce ? count - 1 : tick }
}

function Frame({ children, className, preview }: { children: React.ReactNode; className?: string; preview?: boolean }) {
  return (
    <div
      className={cn(
        'relative h-60 overflow-hidden rounded-2xl border border-border/15 bg-gradient-to-br from-primary/5 via-card to-warning/10 p-5',
        className,
      )}
    >
      {preview ? (
        <span className="absolute right-3 top-3 z-10 rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
          Preview
        </span>
      ) : null}
      {children}
    </div>
  )
}

/* ---------------------------------------------------------------- 1 collect */
export function CollectVisual() {
  const { ref, tick } = useTicker(14, 260)
  const shown = Math.min(tick, 12)
  return (
    <div ref={ref}>
      <Frame>
        <div className="flex h-full gap-4">
          <div className="flex w-[42%] flex-col justify-center gap-2.5">
            {['Your page', 'Competitor'].map((who, index) => (
              <motion.div
                key={who}
                initial={{ x: -20, opacity: 0 }}
                whileInView={{ x: 0, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.15 }}
                className={cn(
                  'flex items-center gap-2 rounded-full border bg-card px-3 py-2 text-xs font-semibold shadow-sm',
                  index ? 'border-warning/40' : 'border-primary/25',
                )}
              >
                <Link2 className={cn('size-3.5', index ? 'text-warning-ink' : 'text-primary')} />
                {who}
              </motion.div>
            ))}
            <p className="mt-1 pl-1 text-xs text-muted-foreground">
              <span className="font-display text-xl font-extrabold text-foreground">{Math.round((shown / 12) * 30)}</span> posts read
            </p>
          </div>
          <div className="grid flex-1 grid-cols-4 content-center gap-1.5">
            {Array.from({ length: 12 }, (_, index) => (
              <motion.span
                key={index}
                animate={{ opacity: index < shown ? 1 : 0.15, scale: index < shown ? 1 : 0.85 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                className={cn(
                  'relative flex aspect-square items-center justify-center overflow-hidden rounded-md',
                  index % 3 === 0 ? 'bg-muted' : index % 2 ? 'bg-primary/20' : 'bg-warning/30',
                )}
              >
                {index % 3 === 0 ? <img src="/hero/product.jpg" alt="" className="size-full object-cover" /> : null}
                {index % 4 === 1 ? <Play className="size-3 fill-current text-primary" /> : null}
              </motion.span>
            ))}
          </div>
        </div>
      </Frame>
    </div>
  )
}

/* ---------------------------------------------------------------- 2 gaps */
export function GapsVisual() {
  const { ref, tick } = useTicker(4, 1400)
  const grown = tick > 0
  const rows = [
    { label: 'Reels', you: 2, them: 18 },
    { label: 'Carousels', you: 5, them: 14 },
    { label: 'Photos', you: 23, them: 9 },
  ]
  return (
    <div ref={ref}>
      <Frame>
        <div className="flex h-full flex-col justify-center gap-3">
          {rows.map((row, index) => (
            <div key={row.label} className="space-y-1">
              <div className="flex items-center justify-between text-[11px] font-semibold">
                <span>{row.label}</span>
                {index === 0 ? (
                  <AnimatePresence>
                    {tick >= 2 ? (
                      <motion.span
                        initial={{ scale: 0.5, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="inline-flex items-center gap-1 rounded-full bg-warning px-2 py-0.5 text-[10px] font-bold text-warning-foreground"
                      >
                        <Sparkle className="size-2.5 fill-current" /> Gap found · How sure: High
                      </motion.span>
                    ) : null}
                  </AnimatePresence>
                ) : null}
              </div>
              {[
                { who: 'You', value: row.you, tone: 'bg-primary' },
                { who: 'Competitor', value: row.them, tone: 'bg-warning' },
              ].map((bar) => (
                <div key={bar.who} className="flex items-center gap-2">
                  <span className="w-16 text-[10px] text-muted-foreground">{bar.who}</span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <motion.span
                      className={cn('block h-full rounded-full', bar.tone, index === 0 && tick >= 2 && 'shadow-[0_0_0_2px_hsl(var(--warning)/0.4)]')}
                      animate={{ width: grown ? `${(bar.value / 30) * 100}%` : '0%' }}
                      transition={{ duration: 0.8, ease: 'easeOut', delay: index * 0.1 }}
                    />
                  </div>
                  <span className="w-9 text-right text-[10px] font-semibold tabular-nums">{bar.value}/30</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </Frame>
    </div>
  )
}

/* ---------------------------------------------------------------- 3 explain */
const INSIGHT = 'Your competitor posted reels in 18 of their last 30 posts, and those reels got more likes than their other posts.'

export function ExplainVisual() {
  const { ref, tick } = useTicker(INSIGHT.length + 30, 45)
  const typed = INSIGHT.slice(0, Math.min(tick, INSIGHT.length))
  const done = tick >= INSIGHT.length
  return (
    <div ref={ref}>
      <Frame>
        <div className="flex h-full items-center">
          <div className="w-full rounded-2xl border border-primary/15 bg-card/90 p-4 shadow-sm">
            <div className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-full bg-warning/30 text-warning-ink">
                <Lightbulb className="size-4 fill-warning" />
              </span>
              <p className="font-display text-sm font-bold text-primary">Key insight</p>
              <span className="ml-auto rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-semibold text-success">Based on real posts</span>
            </div>
            <p className="mt-3 min-h-[3.75rem] text-xs leading-relaxed">
              {typed}
              {!done ? <span className="ml-0.5 inline-block h-3 w-1 animate-pulse bg-primary align-middle" /> : null}
            </p>
            <div className="mt-2 flex items-center gap-1.5">
              {[1, 2, 3].map((n) => (
                <motion.span
                  key={n}
                  animate={{ scale: done ? 1 : 0, opacity: done ? 1 : 0 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 18, delay: n * 0.08 }}
                  className="flex size-8 items-center justify-center overflow-hidden rounded-md bg-muted"
                >
                  <img src="/hero/product.jpg" alt="" className="size-full object-cover" />
                </motion.span>
              ))}
              <motion.span
                animate={{ opacity: done ? 1 : 0 }}
                className="ml-auto text-[10px] font-semibold text-primary underline"
              >
                source
              </motion.span>
            </div>
          </div>
        </div>
      </Frame>
    </div>
  )
}

/* ---------------------------------------------------------------- 4 review */
const REVIEW_CARDS = [
  'Your competitor posts reels much more often than you do.',
  'Your competitor uses more hashtags that get reach.',
  'Your photos look less sharp than your competitor’s.',
]

export function ReviewVisual() {
  const reduce = useReducedMotion()
  const [index, setIndex] = useState(0)
  const [last, setLast] = useState<'keep' | 'drop'>('keep')
  const decide = (choice: 'keep' | 'drop') => {
    setLast(choice)
    setIndex((i) => (i + 1) % REVIEW_CARDS.length)
  }
  const { ref, tick } = useTicker(1000, 2600)
  useEffect(() => {
    if (tick > 0) decide(tick % 3 === 2 ? 'drop' : 'keep')
  }, [tick])
  return (
    <div ref={ref}>
      <Frame>
        <div className="relative flex h-full flex-col items-center justify-center">
          <div className="relative h-28 w-full max-w-xs">
            {[2, 1].map((depth) => (
              <span
                key={depth}
                className="absolute inset-x-0 top-0 h-24 rounded-2xl border border-border/20 bg-card"
                style={{ transform: `translateY(${depth * 8}px) scale(${1 - depth * 0.05})`, opacity: 1 - depth * 0.3 }}
              />
            ))}
            <AnimatePresence mode="popLayout" custom={last}>
              <motion.div
                key={index}
                custom={last}
                initial={reduce ? false : { y: 20, opacity: 0, scale: 0.95 }}
                animate={{ y: 0, x: 0, rotate: 0, opacity: 1, scale: 1 }}
                variants={{ out: (dir: 'keep' | 'drop') => ({ x: dir === 'keep' ? 220 : -220, rotate: dir === 'keep' ? 14 : -14, opacity: 0 }) }}
                exit="out"
                transition={{ type: 'spring', stiffness: 260, damping: 24 }}
                className="absolute inset-x-0 top-0 rounded-2xl border border-primary/20 bg-card p-3 shadow-lg"
              >
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">Gap {index + 1} of 3</span>
                <p className="mt-2 text-xs font-semibold leading-snug">{REVIEW_CARDS[index]}</p>
              </motion.div>
            </AnimatePresence>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => {
                decide('keep')
              }}
              className="inline-flex items-center gap-1 rounded-full bg-success px-3 py-1.5 text-xs font-bold text-success-foreground shadow transition hover:scale-105"
            >
              <Check className="size-3.5" /> Keep
            </button>
            <button
              type="button"
              onClick={() => {
                decide('drop')
              }}
              className="inline-flex items-center gap-1 rounded-full border border-border/40 bg-card px-3 py-1.5 text-xs font-bold text-destructive transition hover:scale-105"
            >
              <X className="size-3.5" /> Drop
            </button>
          </div>
          <p className="mt-2 text-[10px] text-muted-foreground">Try it: click Keep or Drop</p>
        </div>
      </Frame>
    </div>
  )
}

/* ---------------------------------------------------------------- 5 strategy + critic */
export function StrategyVisual() {
  const { ref, tick } = useTicker(5, 1200)
  return (
    <div ref={ref}>
      <Frame preview>
        <div className="flex h-full items-center gap-3">
          <div className="flex-1 rounded-xl border border-border/20 bg-card p-3 shadow-sm">
            <p className="flex items-center gap-1.5 text-[11px] font-bold">
              <FileText className="size-3.5 text-primary" /> Plan, draft 1
            </p>
            <div className="mt-2 space-y-1.5 text-[10px] leading-snug">
              <p>1. Post two reels a week for a month.</p>
              <p className="relative">
                <span className={cn('transition-colors', tick >= 1 && 'text-muted-foreground line-through decoration-destructive decoration-2')}>
                  2. Reels always double your sales.
                </span>
              </p>
              <AnimatePresence>
                {tick >= 2 ? (
                  <motion.p initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} className="rounded bg-success/15 px-1 text-success">
                    2. Compare likes on reels with your usual posts.
                  </motion.p>
                ) : null}
              </AnimatePresence>
              <p>3. Use the hashtags that brought reach.</p>
            </div>
          </div>
          <AnimatePresence>
            {tick >= 1 ? (
              <motion.div
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="w-28 rounded-xl border border-destructive/25 bg-destructive/5 p-2.5 text-[10px] leading-snug"
              >
                <p className="font-bold text-destructive">Critic</p>
                <p className="mt-1 text-muted-foreground">Point 2 has no proof. Replaced with a test you can measure.</p>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </Frame>
    </div>
  )
}

/* ---------------------------------------------------------------- 6 approve */
export function ApproveVisual() {
  const { ref, tick } = useTicker(4, 1300)
  const approved = tick >= 2
  return (
    <div ref={ref}>
      <Frame preview>
        <div className="flex h-full items-center justify-center">
          <div className="relative w-60 rounded-2xl border border-border/20 bg-card p-4 shadow-md">
            <p className="text-[11px] font-bold">Plan for the next 4 weeks</p>
            <div className="mt-2 space-y-1.5" aria-hidden="true">
              <span className="block h-1.5 w-full rounded-full bg-muted" />
              <span className="block h-1.5 w-5/6 rounded-full bg-muted" />
              <span className="block h-1.5 w-2/3 rounded-full bg-muted" />
            </div>
            <div className="mt-3 flex gap-1.5">
              <span className={cn('flex-1 rounded-full py-1 text-center text-[10px] font-bold transition-colors', approved ? 'bg-success text-success-foreground' : 'bg-muted')}>
                Approve
              </span>
              <span className="flex-1 rounded-full border border-border/40 py-1 text-center text-[10px] font-semibold text-muted-foreground">
                Ask for changes
              </span>
            </div>
            <AnimatePresence>
              {approved ? (
                <motion.span
                  initial={{ scale: 2.4, opacity: 0, rotate: -30 }}
                  animate={{ scale: 1, opacity: 1, rotate: -12 }}
                  exit={{ opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 14 }}
                  className="absolute -right-4 -top-4 flex items-center gap-1 rounded-lg border-[3px] border-success bg-card px-2 py-1 font-display text-sm font-extrabold uppercase text-success shadow-lg"
                >
                  <Stamp className="size-4" /> Approved
                </motion.span>
              ) : null}
            </AnimatePresence>
          </div>
        </div>
      </Frame>
    </div>
  )
}

/* ---------------------------------------------------------------- 7 content */
const CAPTION = 'New arrivals are here. Swipe to see every colour →'

export function ContentVisual() {
  const { ref, tick } = useTicker(CAPTION.length + 24, 60)
  const typed = CAPTION.slice(0, Math.min(tick, CAPTION.length))
  return (
    <div ref={ref}>
      <Frame preview>
        <div className="flex h-full items-center justify-center gap-3">
          <motion.div
            whileHover={{ y: -6, rotate: -2 }}
            className="w-32 rounded-xl border border-border/20 bg-card p-2.5 shadow-md"
          >
            <p className="flex items-center gap-1 text-[10px] font-bold text-primary">
              <FileText className="size-3" /> Caption
            </p>
            <p className="mt-1.5 min-h-[3.2rem] text-[10px] leading-snug">{typed}</p>
          </motion.div>
          <motion.div whileHover={{ y: -6, rotate: 2 }} className="w-24 overflow-hidden rounded-xl border border-border/20 bg-card shadow-md">
            <img src="/hero/product.jpg" alt="" className="h-24 w-full object-cover" />
            <p className="flex items-center gap-1 p-1.5 text-[10px] font-bold">
              <ImageIcon className="size-3 text-primary" /> Image
              <Heart className="ml-auto size-3 fill-blush text-blush" />
            </p>
          </motion.div>
          <motion.div
            whileHover={{ y: -6, rotate: 3 }}
            className="relative flex h-32 w-20 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-b from-primary to-warning shadow-md"
          >
            <motion.span
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ duration: 1.6, repeat: Infinity }}
              className="flex size-9 items-center justify-center rounded-full bg-card/90 text-primary"
            >
              <Play className="ml-0.5 size-4 fill-current" />
            </motion.span>
            <span className="absolute bottom-1.5 text-[9px] font-bold text-primary-foreground">Reel</span>
          </motion.div>
        </div>
      </Frame>
    </div>
  )
}
