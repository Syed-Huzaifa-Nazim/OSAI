import { useEffect, useRef, useState } from 'react'
import { motion, useInView, useReducedMotion, type PanInfo } from 'framer-motion'
import { ChevronLeft, ChevronRight, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Cards fanned like a hand of cards: one upright in front with a thick yellow frame, the others tilted behind it.
 * Click a card behind, swipe the front one, use the arrows, or wait: the next card comes forward every few
 * seconds (paused while the pointer is over the fan).
 */

export interface FanItem {
  icon: LucideIcon
  title: string
  body: string
}

const FRAMES = ['border-blush/45', 'border-primary/30', 'border-warning/45']
const AUTO_MS = 5500

export function FanCards({ items, label }: { items: FanItem[]; label: string }) {
  const reduce = useReducedMotion()
  const [front, setFront] = useState(Math.floor(items.length / 2))
  const [paused, setPaused] = useState(false)
  const stage = useRef<HTMLDivElement>(null)
  const inView = useInView(stage, { once: true, margin: '-80px' })
  const count = items.length
  const go = (step: number) => {
    setFront((current) => (current + step + count) % count)
  }

  useEffect(() => {
    if (paused || reduce || !inView || count < 2) return
    const timer = window.setInterval(() => {
      setFront((current) => (current + 1) % count)
    }, AUTO_MS)
    return () => {
      window.clearInterval(timer)
    }
  }, [paused, reduce, inView, count])

  const onDragEnd = (_: unknown, info: PanInfo) => {
    if (info.offset.x < -60) go(1)
    else if (info.offset.x > 60) go(-1)
  }

  return (
    <div
      className="relative"
      onMouseEnter={() => {
        setPaused(true)
      }}
      onMouseLeave={() => {
        setPaused(false)
      }}
      role="region"
      aria-roledescription="carousel"
      aria-label={label}
    >
      <div
        ref={stage}
        className="relative mx-auto h-[25rem] max-w-4xl overflow-hidden px-4 py-6 sm:h-[24rem] sm:overflow-visible"
      >
        {items.map((item, index) => {
          // Where this card sits relative to the front one: 0 front, -1 left, +1 right, further = hidden behind.
          let offset = index - front
          if (offset > count / 2) offset -= count
          if (offset < -count / 2) offset += count
          const isFront = offset === 0
          const side = Math.abs(offset) === 1
          const target = {
            x: `${offset * 58}%`,
            y: isFront ? 0 : side ? 34 : 50,
            rotate: offset * 9,
            scale: isFront ? 1 : side ? 0.86 : 0.75,
            opacity: isFront ? 1 : side ? 0.85 : 0,
          }
          return (
            <motion.article
              key={item.title}
              initial={reduce ? false : { x: 0, y: 40, rotate: 0, scale: 0.8, opacity: 0 }}
              animate={inView || reduce ? target : { x: 0, y: 40, rotate: 0, scale: 0.8, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 180, damping: 24 }}
              style={{ zIndex: 10 - Math.abs(offset) }}
              drag={isFront && !reduce ? 'x' : false}
              dragConstraints={{ left: 0, right: 0 }}
              dragElastic={0.35}
              onDragEnd={onDragEnd}
              onClick={() => {
                if (!isFront) setFront(index)
              }}
              aria-hidden={!isFront}
              className={cn(
                'absolute inset-x-0 top-6 mx-auto w-[min(26rem,82%)] select-none overflow-hidden rounded-[2rem] bg-card p-6 shadow-[0_30px_60px_-30px_hsl(var(--shadow-color)/0.5)] sm:p-8',
                isFront ? 'cursor-grab border-[10px] border-warning active:cursor-grabbing' : cn('cursor-pointer border-[10px]', FRAMES[index % FRAMES.length]),
              )}
            >
              <item.icon
                className={cn('absolute right-6 top-6 size-14', isFront ? 'text-warning' : 'text-warning/40')}
                strokeWidth={2.4}
                aria-hidden="true"
              />
              <span className="absolute -bottom-10 -right-10 size-36 rounded-full border-[14px] border-warning/10" aria-hidden="true" />
              <p className="font-mono text-xs uppercase tracking-[0.25em] text-muted-foreground">
                {String(index + 1).padStart(2, '0')} / {String(count).padStart(2, '0')}
              </p>
              <h3 className="mt-4 pr-14 font-display text-xl font-bold leading-snug sm:text-2xl">{item.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">{item.body}</p>
            </motion.article>
          )
        })}
      </div>

      <div className="mt-2 flex items-center justify-center gap-3">
        <button
          type="button"
          onClick={() => {
            go(-1)
          }}
          className="flex size-10 items-center justify-center rounded-full border border-border/30 bg-card text-primary shadow-sm transition hover:bg-primary hover:text-primary-foreground"
          aria-label="Previous card"
        >
          <ChevronLeft className="size-4" />
        </button>
        <div className="flex items-center gap-2">
          {items.map((item, index) => (
            <button
              key={item.title}
              type="button"
              onClick={() => {
                setFront(index)
              }}
              aria-label={`Show card ${index + 1}`}
              aria-current={index === front}
              className={cn('h-2.5 rounded-full transition-all', index === front ? 'w-8 bg-warning' : 'w-2.5 bg-border/50 hover:bg-border')}
            />
          ))}
        </div>
        <button
          type="button"
          onClick={() => {
            go(1)
          }}
          className="flex size-10 items-center justify-center rounded-full border border-border/30 bg-card text-primary shadow-sm transition hover:bg-primary hover:text-primary-foreground"
          aria-label="Next card"
        >
          <ChevronRight className="size-4" />
        </button>
      </div>
    </div>
  )
}
