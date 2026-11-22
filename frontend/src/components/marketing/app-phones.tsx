import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Bell, Check, Home, Lightbulb, ListChecks, Play, Sparkle, Trophy, UserRound, X } from 'lucide-react'
import { Phone, Pattern } from '@/components/marketing/phone-trio'
import { cn } from '@/lib/utils'

/**
 * The planned phone app, as three phone screens fanned out: the dashboard, reviewing a gap and reading its
 * explanation. Example content only (the app is not built yet; the section says so). Click a phone behind to
 * bring it to the front.
 */

function StatusBar() {
  return <div className="h-7" aria-hidden="true" />
}

function TabBar({ active }: { active: number }) {
  return (
    <div className="mt-auto flex justify-around border-t border-border/20 bg-card px-2 py-2">
      {[Home, ListChecks, Bell].map((Icon, index) => (
        <Icon key={index} className={cn('size-4', index === active ? 'text-primary' : 'text-muted-foreground/60')} />
      ))}
    </div>
  )
}

function DashboardScreen() {
  return (
    <div className="flex h-[23rem] flex-col sm:h-[26rem]">
      <StatusBar />
      <div className="space-y-3 px-3">
        <div>
          <p className="text-[10px] text-muted-foreground">Good morning</p>
          <p className="font-display text-base font-bold">Your shop today 👋</p>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {[
            { n: '12', l: 'Gaps found', c: 'bg-primary/10 text-primary' },
            { n: '3', l: 'Waiting for you', c: 'bg-warning/25 text-warning-ink' },
          ].map((tile) => (
            <div key={tile.l} className={cn('rounded-xl p-2', tile.c)}>
              <p className="font-display text-lg font-extrabold">{tile.n}</p>
              <p className="text-[9px] font-semibold">{tile.l}</p>
            </div>
          ))}
        </div>
        <div className="rounded-xl border border-warning/40 bg-warning/10 p-2">
          <p className="text-[10px] font-bold">3 gaps need your review</p>
          <span className="mt-1.5 inline-block rounded-full bg-warning px-2 py-0.5 text-[9px] font-bold text-warning-foreground">
            Review gaps →
          </span>
        </div>
        <div className="flex h-14 items-end gap-1 rounded-xl bg-muted/50 px-2 pb-1.5 pt-2" aria-hidden="true">
          {[40, 55, 35, 70, 60, 85, 75].map((h, index) => (
            <span key={index} className={cn('flex-1 rounded-t-[3px]', index % 2 ? 'bg-primary/40' : 'bg-primary')} style={{ height: `${h}%` }} />
          ))}
        </div>
      </div>
      <TabBar active={0} />
    </div>
  )
}

function ReviewScreen() {
  return (
    <div className="flex h-[23rem] flex-col sm:h-[26rem]">
      <StatusBar />
      <div className="space-y-2.5 px-3">
        <p className="font-display text-base font-bold">Review gaps</p>
        <p className="text-[10px] text-muted-foreground">Gap 1 of 3 · swipe to decide</p>
        <div className="rounded-2xl border border-primary/20 bg-card p-2.5 shadow-md">
          <div className="relative h-20 overflow-hidden rounded-xl">
            <img src="/hero/product.jpg" alt="" className="size-full object-cover" />
            <span className="absolute inset-0 flex items-center justify-center">
              <span className="flex size-7 items-center justify-center rounded-full bg-black/45 text-white">
                <Play className="ml-0.5 size-3 fill-current" />
              </span>
            </span>
          </div>
          <div className="mt-2 flex gap-1">
            <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[8px] font-semibold text-primary">Type of post</span>
            <span className="rounded-full bg-success/15 px-1.5 py-0.5 text-[8px] font-semibold text-success">How sure: High</span>
          </div>
          <p className="mt-1.5 text-[11px] font-bold leading-snug">Your competitor posts reels much more often than you do.</p>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          <span className="flex items-center justify-center gap-1 rounded-full bg-success py-1.5 text-[10px] font-bold text-success-foreground">
            <Check className="size-3" /> Keep
          </span>
          <span className="flex items-center justify-center gap-1 rounded-full border border-border/40 py-1.5 text-[10px] font-bold text-destructive">
            <X className="size-3" /> Drop
          </span>
        </div>
      </div>
      <TabBar active={1} />
    </div>
  )
}

function ExplainScreen() {
  return (
    <div className="flex h-[23rem] flex-col sm:h-[26rem]">
      <StatusBar />
      <div className="space-y-2.5 px-3">
        <p className="font-display text-base font-bold">Why this gap?</p>
        <div className="rounded-xl bg-gradient-to-r from-primary/10 to-card p-2.5">
          <p className="flex items-center gap-1 text-[10px] font-bold text-primary">
            <Lightbulb className="size-3 fill-warning text-warning-ink" /> Key insight
          </p>
          <p className="mt-1 text-[9.5px] leading-snug">
            Your competitor posted reels in 18 of their last 30 posts, and those got more likes than their other posts.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-1.5 text-center">
          <div className="rounded-xl bg-primary/10 p-1.5">
            <UserRound className="mx-auto size-3.5 text-primary" />
            <p className="font-display text-sm font-extrabold">2/30</p>
            <p className="text-[8px] text-muted-foreground">You</p>
          </div>
          <div className="rounded-xl bg-warning/25 p-1.5">
            <Trophy className="mx-auto size-3.5 fill-warning text-warning-ink" />
            <p className="font-display text-sm font-extrabold">18/30</p>
            <p className="text-[8px] text-muted-foreground">Competitor</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-1">
          {[0, 1, 2].map((index) => (
            <span key={index} className="aspect-square overflow-hidden rounded-md">
              <img src="/hero/product.jpg" alt="" className="size-full object-cover" style={{ objectPosition: `${index * 40}% 50%` }} />
            </span>
          ))}
        </div>
      </div>
      <TabBar active={1} />
    </div>
  )
}

const SCREENS = [
  { key: 'dashboard', label: 'Dashboard', screen: DashboardScreen },
  { key: 'review', label: 'Review gaps', screen: ReviewScreen },
  { key: 'explain', label: 'Explanation', screen: ExplainScreen },
]

export function AppPhones() {
  const reduce = useReducedMotion()
  const [front, setFront] = useState(1)

  return (
    <div className="relative mx-auto h-[27rem] w-full max-w-xl sm:h-[31rem]">
      <Pattern className="left-0 top-8 text-primary/40" delay={0} />
      <Pattern className="bottom-6 left-[6%] text-blush/60" delay={1.2} />
      <Pattern className="right-2 top-4 text-primary/30" delay={0.6} />
      <Pattern className="bottom-2 right-[6%] text-warning/60" delay={1.8} />

      {SCREENS.map((item, index) => {
        let offset = index - front
        if (offset > 1) offset -= 3
        if (offset < -1) offset += 3
        const isFront = offset === 0
        return (
          <motion.button
            key={item.key}
            type="button"
            onClick={() => {
              setFront(index)
            }}
            aria-label={`Show the ${item.label} screen`}
            aria-pressed={isFront}
            className="absolute left-1/2 top-1/2 text-left"
            initial={reduce ? false : { x: '-50%', y: '-50%', rotate: 0, opacity: 0 }}
            whileInView={{ opacity: 1 }}
            animate={{
              x: `${-50 + offset * 62}%`,
              y: isFront ? '-50%' : '-46%',
              rotate: offset * 8,
              scale: isFront ? 1 : 0.88,
            }}
            viewport={{ once: true }}
            transition={{ type: 'spring', stiffness: 140, damping: 18 }}
            style={{ zIndex: isFront ? 3 : 1 }}
            whileHover={isFront ? { y: '-52%' } : { scale: 0.92 }}
          >
            <Phone className={cn('sm:w-56', isFront ? 'w-48' : 'w-44 opacity-90')}>
              <item.screen />
            </Phone>
          </motion.button>
        )
      })}

      <div className="absolute inset-x-0 -bottom-2 flex justify-center gap-2">
        {SCREENS.map((item, index) => (
          <button
            key={item.key}
            type="button"
            onClick={() => {
              setFront(index)
            }}
            className={cn(
              'rounded-full px-3 py-1 text-xs font-semibold transition',
              index === front ? 'bg-primary text-primary-foreground shadow' : 'bg-card text-muted-foreground hover:text-foreground',
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      <Sparkle className="absolute right-[18%] top-0 size-5 fill-warning text-warning" aria-hidden="true" />
    </div>
  )
}
