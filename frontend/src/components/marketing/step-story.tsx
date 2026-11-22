import { useRef, useState } from 'react'
import {
  AnimatePresence,
  motion,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
  type MotionValue,
} from 'framer-motion'
import { Link2, ScanSearch, ShieldCheck, Sparkles, Swords, UserRoundCheck, type LucideIcon } from 'lucide-react'
import { USER_STEPS, USER_STEP_TEXT } from '@/lib/user-steps'
import { cn } from '@/lib/utils'
import { spring } from '@/lib/motion'

/**
 * The six steps as a scroll story. On large screens the section pins while you scroll: numbered cards turn on a
 * wheel on the left, and the step in front is told in full on the right. On small screens (or with reduced motion)
 * the cards simply slide in one after another.
 */

type Tone = 'violet' | 'blush' | 'yellow'

const TONE: Record<Tone, { num: string; chip: string; wash: string; ring: string; glow: string; dot: string }> = {
  violet: {
    num: 'from-primary to-primary/20',
    chip: 'border-primary/25 text-primary',
    wash: 'to-primary/20',
    ring: 'border-primary/20',
    glow: 'bg-primary/15',
    dot: 'bg-primary',
  },
  blush: {
    num: 'from-blush to-blush/25',
    chip: 'border-blush/50 text-foreground',
    wash: 'to-blush/35',
    ring: 'border-blush/35',
    glow: 'bg-blush/20',
    dot: 'bg-blush',
  },
  yellow: {
    num: 'from-warning to-warning/25',
    chip: 'border-warning/50 text-warning-ink',
    wash: 'to-warning/30',
    ring: 'border-warning/40',
    glow: 'bg-warning/20',
    dot: 'bg-warning',
  },
}

/** Height of the pinned stage (34rem), which stays 80px below the top of the screen while the steps turn. */
const STAGE_PX = 544

const ICONS: LucideIcon[] = [Link2, ScanSearch, UserRoundCheck, Swords, ShieldCheck, Sparkles]
const TONES: Tone[] = ['violet', 'blush', 'yellow', 'violet', 'yellow', 'blush']

const STEPS = USER_STEPS.map((step, index) => ({
  ...step,
  number: String(index + 1).padStart(2, '0'),
  text: USER_STEP_TEXT[index] ?? '',
  icon: ICONS[index] ?? Sparkles,
  tone: TONES[index] ?? 'violet',
  chip: step.you ? (step.built ? 'Your decision' : 'Your decision · coming soon') : step.built ? 'Runs on its own' : 'Coming soon',
}))

type Step = (typeof STEPS)[number]

function Chip({ step, large = false }: { step: Step; large?: boolean }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border bg-card font-semibold uppercase tracking-[0.14em] shadow-sm',
        large ? 'px-4 py-2 text-xs' : 'px-3 py-1 text-[10px]',
        TONE[step.tone].chip,
      )}
    >
      <step.icon className={large ? 'size-4' : 'size-3.5'} aria-hidden="true" />
      {step.chip}
    </span>
  )
}

/** One numbered card: big gradient number, chip, title and what the step does. */
function StepCard({ step, className }: { step: Step; className?: string }) {
  const tone = TONE[step.tone]
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-[2rem] border border-border/15 bg-gradient-to-br from-card via-card p-6 shadow-[0_24px_60px_-28px_hsl(var(--shadow-color)/0.45)] sm:p-7',
        tone.wash,
        className,
      )}
    >
      <span className={cn('absolute -right-10 -top-10 size-36 rounded-full border-[14px]', tone.ring)} aria-hidden="true" />
      <div className="relative flex items-center gap-5">
        <span
          className={cn(
            'shrink-0 bg-gradient-to-b bg-clip-text font-display text-6xl font-extrabold leading-none text-transparent sm:text-7xl',
            tone.num,
          )}
        >
          {step.number}
        </span>
        <div className="min-w-0 space-y-2">
          <Chip step={step} />
          <p className="font-display text-xl font-bold leading-tight">{step.label}</p>
          <p className="line-clamp-3 text-sm leading-relaxed text-muted-foreground">{step.text}</p>
        </div>
      </div>
    </div>
  )
}

/** A card on the wheel: its place follows the scroll position (`pos` runs 0 → 5). */
function WheelCard({ step, index, pos }: { step: Step; index: number; pos: MotionValue<number> }) {
  const d = useTransform(pos, (v) => index - v)
  const y = useTransform(d, (v) => v * 220)
  const x = useTransform(d, (v) => -Math.pow(Math.abs(v), 1.15) * 90)
  const rotate = useTransform(d, (v) => v * 24)
  const scale = useTransform(d, (v) => 1 - Math.min(Math.abs(v), 2) * 0.1)
  const opacity = useTransform(d, (v) => Math.max(0, 1 - Math.abs(v) * 0.42))
  const zIndex = useTransform(d, (v) => 10 - Math.round(Math.abs(v)))
  return (
    <motion.div style={{ x, y, rotate, scale, opacity, zIndex }} className="absolute inset-x-0 top-1/2 -translate-y-1/2">
      <StepCard step={step} />
    </motion.div>
  )
}

function PinnedStory() {
  const box = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: box, offset: ['start 80px', `end ${80 + STAGE_PX}px`] })
  const raw = useTransform(scrollYProgress, [0, 1], [0, STEPS.length - 1])
  const pos = useSpring(raw, { stiffness: 120, damping: 24, mass: 0.6 })
  const [active, setActive] = useState(0)
  useMotionValueEvent(raw, 'change', (v) => {
    setActive(Math.min(STEPS.length - 1, Math.max(0, Math.round(v))))
  })
  const step = STEPS[active] ?? STEPS[0]!

  const goTo = (index: number) => {
    const el = box.current
    if (!el) return
    const top = el.getBoundingClientRect().top + window.scrollY - 80
    const span = el.offsetHeight - STAGE_PX
    window.scrollTo({ top: top + (span * index) / (STEPS.length - 1), behavior: 'smooth' })
  }

  return (
    <div ref={box} className="relative" style={{ height: `calc(${STEPS.length * 60}vh + 34rem)` }}>
      <div className="sticky top-20 flex h-[34rem] items-center overflow-hidden">
        <div className="grid w-full grid-cols-[minmax(0,1fr)_minmax(0,1fr)] items-center gap-14">
          <div className="relative h-[34rem] [mask-image:linear-gradient(to_bottom,transparent,black_14%,black_86%,transparent)]">
            <div className="absolute inset-y-0 left-10 right-4">
              {STEPS.map((s, index) => (
                <WheelCard key={s.label} step={s} index={index} pos={pos} />
              ))}
            </div>
          </div>

          <div className="relative">
            <div className={cn('pointer-events-none absolute -left-12 -top-10 size-96 rounded-full blur-3xl transition-colors duration-700', TONE[step.tone].glow)} aria-hidden="true" />
            <AnimatePresence mode="wait">
              <motion.div
                key={step.label}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -18 }}
                transition={spring}
                className="relative"
                aria-live="polite"
              >
                <p
                  className={cn(
                    'bg-gradient-to-b bg-clip-text font-display text-[9rem] font-extrabold leading-[0.9] text-transparent',
                    TONE[step.tone].num,
                  )}
                >
                  {step.number}
                </p>
                <div className="mt-4">
                  <Chip step={step} large />
                </div>
                <h3 className="mt-4 font-display text-4xl font-bold tracking-tight">{step.label}</h3>
                <p className="mt-3 max-w-md text-lg leading-relaxed text-muted-foreground">{step.text}</p>
              </motion.div>
            </AnimatePresence>
            <div className="relative mt-8 flex items-center gap-2" role="tablist" aria-label="Steps">
              {STEPS.map((s, index) => (
                <button
                  key={s.label}
                  type="button"
                  role="tab"
                  aria-selected={index === active}
                  aria-label={`Step ${index + 1}: ${s.label}`}
                  onClick={() => {
                    goTo(index)
                  }}
                  className={cn(
                    'h-2.5 rounded-full transition-all duration-300',
                    index === active ? cn('w-10', TONE[s.tone].dot) : 'w-2.5 bg-border/50 hover:bg-border',
                  )}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StackedStory() {
  return (
    <ol className="space-y-5">
      {STEPS.map((step, index) => (
        <motion.li
          key={step.label}
          initial={{ opacity: 0, x: index % 2 ? 40 : -40, rotate: index % 2 ? 4 : -4 }}
          whileInView={{ opacity: 1, x: 0, rotate: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={spring}
        >
          <StepCard step={step} />
        </motion.li>
      ))}
    </ol>
  )
}

export function StepStory() {
  const reduce = useReducedMotion()
  return (
    <>
      <div className={reduce ? 'hidden' : 'hidden lg:block'}>
        <PinnedStory />
      </div>
      <div className={reduce ? '' : 'lg:hidden'}>
        <StackedStory />
      </div>
    </>
  )
}
