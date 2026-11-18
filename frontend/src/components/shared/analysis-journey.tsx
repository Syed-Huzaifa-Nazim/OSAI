import { useRef } from 'react'
import { motion, useScroll, useSpring, useTransform } from 'framer-motion'
import { Check, FileSearch, Lightbulb, Rocket, ShieldCheck } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

const STEPS = [
  { label: 'Add your brand', icon: Rocket },
  { label: 'We read both sides', icon: FileSearch },
  { label: 'Find opportunities', icon: Lightbulb },
  { label: 'Choose what to do', icon: ShieldCheck },
]

export function AnalysisJourney({ active = 0, compact = false }: { active?: number; compact?: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  const progress = useSpring(useTransform(scrollYProgress, [0.15, 0.8], [0.08, 0.92]), {
    stiffness: 100,
    damping: 24,
  })

  return (
    <Card ref={ref} className={cn('relative overflow-hidden border-primary/15 bg-card/80 p-5', compact ? 'sm:p-5' : 'sm:p-7')}>
      <motion.div
        aria-hidden="true"
        className="absolute inset-x-5 top-0 h-1 origin-left rounded-full bg-primary/70"
        style={{ scaleX: progress }}
      />
      <div className="relative space-y-5">
        {!compact ? (
          <div>
            <p className="eyebrow">Your route to a decision</p>
            <h2 className="mt-1 font-display text-xl font-semibold">From “what are they doing?” to “here is what we do next.”</h2>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
              You do not need to understand the agents. Just move through the four decisions that matter.
            </p>
          </div>
        ) : null}
        <div className="grid gap-4 sm:grid-cols-4 sm:gap-3">
          {STEPS.map((step, index) => {
            const Icon = step.icon
            const complete = index < active
            const current = index === active
            return (
              <motion.div
                key={step.label}
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: index * 0.08 }}
                className="relative flex items-center gap-3 sm:block"
              >
                <motion.span
                  animate={{ scale: current ? [1, 1.08, 1] : 1 }}
                  transition={{ repeat: current ? Infinity : 0, duration: 2.4 }}
                  className={cn(
                    'relative z-10 flex size-9 shrink-0 items-center justify-center rounded-full border bg-card transition-colors sm:mb-3',
                    complete || current ? 'border-primary bg-primary text-primary-foreground shadow-lg shadow-primary/20' : 'border-border/50 text-muted-foreground',
                  )}
                >
                  {complete ? <Check className="size-4" /> : <Icon className="size-4" />}
                </motion.span>
                <div className="min-w-0">
                  <p className={cn('text-sm font-medium', current && 'text-primary')}>{step.label}</p>
                  {!compact ? <p className="mt-1 text-xs text-muted-foreground">Step {index + 1}</p> : null}
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}
