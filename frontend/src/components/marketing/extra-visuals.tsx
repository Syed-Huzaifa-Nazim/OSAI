import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useInView, useReducedMotion } from 'framer-motion'
import { Brain, Check, Database, Download, FileText, MousePointer2, Search, ShieldCheck, UserRound, X } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Ticks while on screen; sits at the last frame with reduced motion. */
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

/* ------------------------------------------------------------- gap report (landing, last section) */
const REPORT_GAPS = [
  'Your competitor posts reels much more often',
  'Your competitor uses hashtags that get reach',
  'Your photos look less sharp',
]

/** The branded PDF report filling in, gap by gap, then "Download PDF" being clicked. Example content. */
export function ReportVisual() {
  const { ref, tick } = useTicker(9, 800)
  const shown = Math.min(tick, REPORT_GAPS.length)
  const clicking = tick >= 5 && tick <= 6
  return (
    <div ref={ref} className="relative mx-auto h-[24rem] w-full max-w-md" aria-label="Example gap report" role="img">
      <div className="absolute inset-6 rounded-full bg-primary/15 blur-3xl" aria-hidden="true" />
      {/* pages behind */}
      <span className="absolute left-[14%] top-8 h-[19rem] w-[68%] rotate-[-7deg] rounded-2xl border border-border/20 bg-card/70 shadow-md" />
      <span className="absolute left-[18%] top-6 h-[19rem] w-[68%] rotate-[5deg] rounded-2xl border border-border/20 bg-card/80 shadow-md" />
      {/* front page */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        whileInView={{ y: 0, opacity: 1 }}
        viewport={{ once: true }}
        className="absolute left-[15%] top-4 w-[70%] overflow-hidden rounded-2xl border border-border/20 bg-card shadow-2xl"
      >
        <div className="flex items-center gap-2 border-b-2 border-primary px-4 py-3">
          <img src="/brand/logo-wide.png" alt="" className="h-6 w-auto" />
          <span className="font-display text-xs font-bold">OptiStratixAI</span>
          <span className="ml-auto text-[10px] text-muted-foreground">Gap report</span>
        </div>
        <div className="space-y-2.5 p-4">
          <p className="font-display text-sm font-bold">You vs your competitor</p>
          {REPORT_GAPS.map((gap, index) => (
            <motion.div
              key={gap}
              animate={{ opacity: index < shown ? 1 : 0.2, x: index < shown ? 0 : -8 }}
              transition={{ type: 'spring', stiffness: 260, damping: 22 }}
              className="flex items-start gap-2 rounded-lg bg-muted/40 p-2"
            >
              <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-success text-success-foreground">
                <Check className="size-2.5" strokeWidth={3} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-semibold leading-snug">{gap}</p>
                <span className="mt-1 block h-1 w-3/4 rounded-full bg-muted" />
              </div>
              <span className="size-8 shrink-0 overflow-hidden rounded-md">
                <img src="/hero/product.jpg" alt="" className="size-full object-cover" />
              </span>
            </motion.div>
          ))}
          <motion.span
            animate={{ scale: clicking ? 0.94 : 1 }}
            className={cn(
              'mt-1 flex items-center justify-center gap-1.5 rounded-full py-2 text-xs font-bold transition-colors',
              tick >= 6 ? 'bg-success text-success-foreground' : 'bg-primary text-primary-foreground',
            )}
          >
            {tick >= 6 ? <Check className="size-3.5" /> : <Download className="size-3.5" />}
            {tick >= 6 ? 'Downloaded' : 'Download PDF'}
          </motion.span>
        </div>
      </motion.div>
      {/* the pointer */}
      <motion.span
        className="absolute text-foreground drop-shadow"
        animate={{ left: tick >= 4 ? '52%' : '86%', top: tick >= 4 ? '78%' : '88%', opacity: tick >= 3 && tick < 8 ? 1 : 0 }}
        transition={{ type: 'spring', stiffness: 120, damping: 18 }}
        aria-hidden="true"
      >
        <MousePointer2 className="size-6 fill-card" />
      </motion.span>
      <motion.span
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute right-0 top-16 flex items-center gap-1.5 rounded-full bg-warning px-3 py-1.5 text-[11px] font-bold text-warning-foreground shadow-lg"
      >
        <FileText className="size-3.5" /> Your logo, your gaps
      </motion.span>
    </div>
  )
}

/* ------------------------------------------------------------- about: objective visuals */
const RAG_STEPS = [
  { icon: Database, label: 'Posts' },
  { icon: Search, label: 'Search' },
  { icon: Brain, label: 'LLM' },
  { icon: ShieldCheck, label: 'Checked' },
]

/** Retrieval-augmented generation as a flow: a dot travels from the posts to a checked answer. */
export function RagVisual() {
  const { ref, tick } = useTicker(RAG_STEPS.length, 900)
  return (
    <div ref={ref} className="relative flex h-28 items-center justify-between rounded-2xl bg-gradient-to-r from-primary/10 via-card to-success/10 px-4" aria-hidden="true">
      <span className="absolute left-8 right-8 top-[42%] h-0.5 bg-border/50" />
      <motion.span
        className="absolute top-[42%] size-3 -translate-y-1/2 rounded-full bg-warning shadow-[0_0_0_4px_hsl(var(--warning)/0.3)]"
        animate={{ left: `${8 + (tick / (RAG_STEPS.length - 1)) * 82}%` }}
        transition={{ type: 'spring', stiffness: 120, damping: 18 }}
      />
      {RAG_STEPS.map((step, index) => (
        <div key={step.label} className="relative z-10 flex flex-col items-center gap-1.5">
          <motion.span
            animate={{ scale: index === tick ? 1.15 : 1 }}
            className={cn(
              'flex size-10 items-center justify-center rounded-xl shadow-sm transition-colors',
              index <= tick ? (index === RAG_STEPS.length - 1 ? 'bg-success text-success-foreground' : 'bg-primary text-primary-foreground') : 'bg-card text-muted-foreground',
            )}
          >
            <step.icon className="size-5" />
          </motion.span>
          <span className="text-[10px] font-semibold text-muted-foreground">{step.label}</span>
        </div>
      ))}
    </div>
  )
}

const PLATFORMS = [
  { src: '/hero/instagram.png', name: 'Instagram' },
  { src: '/hero/daraz-mark.png', name: 'Daraz' },
  { src: '/hero/alibaba-mark.png', name: 'Alibaba' },
  { src: '/hero/facebook.png', name: 'Facebook', soon: true },
]

/** The places a comparison can run, lighting up one after another; Facebook marked as coming. */
export function PlatformsVisual() {
  const { ref, tick } = useTicker(3, 1100)
  return (
    <div ref={ref} className="flex h-28 items-center justify-around rounded-2xl bg-gradient-to-r from-blush/15 via-card to-primary/10 px-3" aria-hidden="true">
      {PLATFORMS.map((platform, index) => (
        <motion.div
          key={platform.name}
          animate={{ y: !platform.soon && index === tick ? -8 : 0, scale: !platform.soon && index === tick ? 1.12 : 1 }}
          transition={{ type: 'spring', stiffness: 260, damping: 16 }}
          className="flex flex-col items-center gap-1.5"
        >
          <span className={cn('flex size-12 items-center justify-center rounded-2xl bg-card p-2 shadow-md', platform.soon && 'opacity-40 grayscale')}>
            <img src={platform.src} alt="" className="size-full object-contain" />
          </span>
          <span className="text-[10px] font-semibold text-muted-foreground">{platform.soon ? `${platform.name} · soon` : platform.name}</span>
        </motion.div>
      ))}
    </div>
  )
}

/** A person deciding: the gap card flips between Kept and Dropped. */
export function LoopVisual() {
  const { ref, tick } = useTicker(2, 1600)
  const kept = tick === 0
  return (
    <div ref={ref} className="flex h-28 items-center justify-center gap-4 rounded-2xl bg-gradient-to-r from-warning/15 via-card to-success/10 px-4" aria-hidden="true">
      <span className="flex size-12 items-center justify-center rounded-full bg-warning/30 text-warning-ink shadow-sm ring-4 ring-warning/15">
        <UserRound className="size-6" />
      </span>
      <div className="w-44 rounded-xl border border-border/20 bg-card p-2.5 shadow-md">
        <p className="text-[10px] font-semibold leading-snug">Your competitor posts reels more often.</p>
        <div className="mt-2 flex items-center gap-1.5">
          <span className={cn('flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold transition-colors', kept ? 'bg-success text-success-foreground' : 'bg-muted text-muted-foreground')}>
            <Check className="size-2.5" /> Keep
          </span>
          <span className={cn('flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold transition-colors', !kept ? 'bg-destructive text-destructive-foreground' : 'bg-muted text-muted-foreground')}>
            <X className="size-2.5" /> Drop
          </span>
          <AnimatePresence mode="wait">
            <motion.span
              key={kept ? 'k' : 'd'}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="ml-auto text-[9px] font-bold text-muted-foreground"
            >
              {kept ? 'Kept' : 'Dropped'}
            </motion.span>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
