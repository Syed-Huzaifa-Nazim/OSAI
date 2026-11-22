import { useEffect, useRef, useState } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'
import { Check, FileText, Play, Search, Server, ShieldCheck, Sparkle } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Small moving pictures for the "What runs underneath" cards (How it works page). Example content only.
 * They run while on screen and sit still with reduced motion.
 */

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

const BOX = 'relative flex h-24 items-center overflow-hidden rounded-xl px-4'

/** Logos send posts into a growing stack. */
export function CollectMini() {
  const { ref, tick } = useTicker(7, 450)
  return (
    <div ref={ref} className={cn(BOX, 'justify-between bg-gradient-to-r from-primary/10 to-card')} aria-hidden="true">
      <div className="flex flex-col gap-1.5">
        {['/hero/instagram.png', '/hero/daraz-mark.png', '/hero/alibaba-mark.png'].map((src, index) => (
          <motion.img
            key={src}
            src={src}
            alt=""
            animate={{ x: index === tick % 3 ? 4 : 0 }}
            className="size-6 rounded-md bg-card object-contain p-0.5 shadow-sm"
          />
        ))}
      </div>
      <motion.span
        animate={{ x: [0, 40, 80], opacity: [0, 1, 0] }}
        transition={{ duration: 1.3, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute left-14 top-1/2 size-2.5 -translate-y-1/2 rounded-full bg-warning"
      />
      <div className="grid grid-cols-3 gap-1">
        {Array.from({ length: 6 }, (_, index) => (
          <motion.span
            key={index}
            animate={{ opacity: index < tick ? 1 : 0.15, scale: index < tick ? 1 : 0.8 }}
            className={cn('flex size-6 items-center justify-center rounded', index % 2 ? 'bg-primary/25' : 'bg-warning/35')}
          >
            {index === 2 ? <Play className="size-2.5 fill-current text-primary" /> : null}
          </motion.span>
        ))}
      </div>
    </div>
  )
}

/** Two bars, then a stamp: statistics say the difference is a real gap, not a coincidence. */
export function GapsMini() {
  const { ref, tick } = useTicker(4, 900)
  return (
    <div ref={ref} className={cn(BOX, 'gap-4 bg-gradient-to-r from-warning/15 to-card')} aria-hidden="true">
      <div className="flex-1 space-y-2">
        {[
          { who: 'You', w: 12, c: 'bg-primary' },
          { who: 'Competitor', w: 70, c: 'bg-warning' },
        ].map((bar) => (
          <div key={bar.who} className="flex items-center gap-2">
            <span className="w-16 text-[10px] text-muted-foreground">{bar.who}</span>
            <div className="h-2.5 flex-1 rounded-full bg-muted">
              <motion.span className={cn('block h-full rounded-full', bar.c)} animate={{ width: tick ? `${bar.w}%` : '0%' }} transition={{ duration: 0.7 }} />
            </div>
          </div>
        ))}
      </div>
      <motion.span
        animate={{ scale: tick >= 2 ? 1 : 0, rotate: tick >= 2 ? -8 : -30 }}
        transition={{ type: 'spring', stiffness: 300, damping: 14 }}
        className="flex items-center gap-1 rounded-lg border-2 border-success bg-card px-2 py-1 text-[10px] font-extrabold uppercase text-success"
      >
        <ShieldCheck className="size-3.5" /> Real gap
      </motion.span>
    </div>
  )
}

/** A photo with a score dial filling up. */
export function QualityMini() {
  const { ref, tick } = useTicker(5, 700)
  const score = [1.2, 2.4, 3.1, 3.8, 3.8][tick] ?? 3.8
  return (
    <div ref={ref} className={cn(BOX, 'gap-4 bg-gradient-to-r from-blush/15 to-card')} aria-hidden="true">
      <span className="relative size-16 shrink-0 overflow-hidden rounded-lg shadow-md">
        <img src="/hero/product.jpg" alt="" className="size-full object-cover" />
        <motion.span
          className="absolute inset-x-0 h-0.5 bg-warning shadow-[0_0_8px_hsl(var(--warning))]"
          animate={{ top: ['0%', '100%', '0%'] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: 'linear' }}
        />
      </span>
      <div className="flex-1">
        <p className="text-[10px] font-semibold text-muted-foreground">Picture quality (example)</p>
        <p className="font-display text-xl font-extrabold tabular-nums">
          {score.toFixed(1)}
          <span className="text-xs font-semibold text-muted-foreground"> / 5</span>
        </p>
        <div className="mt-1 h-1.5 rounded-full bg-muted">
          <motion.span className="block h-full rounded-full bg-gradient-to-r from-blush to-primary" animate={{ width: `${(score / 5) * 100}%` }} />
        </div>
      </div>
    </div>
  )
}

/** A search typed in, and the closest posts lighting up by how close they are. */
const QUERY = 'reels'
export function SearchMini() {
  const { ref, tick } = useTicker(QUERY.length + 5, 300)
  const typed = QUERY.slice(0, Math.min(tick, QUERY.length))
  const done = tick > QUERY.length
  return (
    <div ref={ref} className={cn(BOX, 'flex-col items-stretch justify-center gap-2 bg-gradient-to-r from-primary/10 to-card')} aria-hidden="true">
      <span className="flex items-center gap-1.5 rounded-full border border-border/30 bg-card px-2.5 py-1 text-[11px]">
        <Search className="size-3 text-primary" />
        {typed}
        <span className="h-3 w-px animate-pulse bg-primary" />
      </span>
      <div className="flex gap-1.5">
        {[92, 78, 61].map((match, index) => (
          <motion.span
            key={match}
            animate={{ opacity: done ? 1 : 0.2, y: done ? 0 : 4 }}
            transition={{ delay: index * 0.1 }}
            className="flex-1 rounded-md bg-card p-1 text-center shadow-sm"
          >
            <span className="block h-1 rounded-full bg-primary" style={{ width: `${match}%` }} />
            <span className="text-[9px] font-semibold text-muted-foreground">{match}% match</span>
          </motion.span>
        ))}
      </div>
    </div>
  )
}

/** An answer appearing with numbered posts and a checked source. */
export function ExplainMini() {
  const { ref, tick } = useTicker(4, 800)
  return (
    <div ref={ref} className={cn(BOX, 'gap-3 bg-gradient-to-r from-warning/15 to-card')} aria-hidden="true">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <Sparkle className="size-4 fill-current" />
      </span>
      <div className="flex-1 rounded-xl rounded-tl-sm bg-card p-2 shadow-sm">
        <div className="space-y-1">
          <motion.span className="block h-1.5 rounded-full bg-muted" animate={{ width: tick >= 1 ? '95%' : '20%' }} />
          <motion.span className="block h-1.5 rounded-full bg-muted" animate={{ width: tick >= 2 ? '70%' : '10%' }} />
        </div>
        <div className="mt-1.5 flex items-center gap-1">
          {[1, 2].map((n) => (
            <motion.span
              key={n}
              animate={{ scale: tick >= 2 ? 1 : 0 }}
              className="flex size-4 items-center justify-center rounded-full bg-primary/15 text-[9px] font-bold text-primary"
            >
              {n}
            </motion.span>
          ))}
          <motion.span animate={{ opacity: tick >= 3 ? 1 : 0 }} className="ml-auto flex items-center gap-0.5 text-[9px] font-bold text-success">
            <Check className="size-3" /> source checked
          </motion.span>
        </div>
      </div>
    </div>
  )
}

/** The three parts of the app stacking up. */
export function AppMini() {
  const { ref, tick } = useTicker(4, 700)
  const layers = [
    { icon: FileText, label: 'PDF reports', c: 'bg-warning text-warning-foreground' },
    { icon: Sparkle, label: 'React app', c: 'bg-primary text-primary-foreground' },
    { icon: Server, label: 'FastAPI backend', c: 'bg-foreground text-background' },
  ]
  return (
    <div ref={ref} className={cn(BOX, 'justify-center bg-gradient-to-r from-primary/10 to-blush/10')} aria-hidden="true">
      <div className="relative h-20 w-44">
        {layers.map((layer, index) => {
          const from = layers.length - 1 - index
          return (
            <motion.span
              key={layer.label}
              animate={{ y: tick >= from ? index * 22 : -30, opacity: tick >= from ? 1 : 0 }}
              transition={{ type: 'spring', stiffness: 260, damping: 18 }}
              className={cn('absolute inset-x-0 flex h-7 items-center gap-1.5 rounded-lg px-2.5 text-[10px] font-bold shadow-md', layer.c)}
              style={{ zIndex: index }}
            >
              <layer.icon className="size-3.5" /> {layer.label}
            </motion.span>
          )
        })}
      </div>
    </div>
  )
}
