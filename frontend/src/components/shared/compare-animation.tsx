import { motion, useReducedMotion } from 'framer-motion'
import { Play, Search, Sparkle } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * What the app does, as a looping picture: two pages side by side ("You" and "Competitor"), a magnifying glass
 * reads both, and the post the competitor has where you have nothing lights up as "Gap found".
 * Everything is drawn with theme colours, so it stays sharp and follows dark mode. Still when motion is reduced.
 */

const LOOP = 6 // seconds per cycle; every part uses the same clock so they stay in step
const GAP_TILE = 4 // the tile (0-5) where the competitor has a reel and you have nothing

function MiniPage({ who, side }: { who: string; side: 'own' | 'rival' }) {
  const reduce = useReducedMotion()
  const rival = side === 'rival'
  return (
    <div
      className={cn(
        'card-soft absolute w-[44%] border border-border/15 p-2.5',
        rival ? 'right-[2%] top-[10%] rotate-[4deg]' : 'left-[2%] top-[20%] -rotate-[4deg]',
      )}
    >
      <div className="mb-2 flex items-center gap-1.5">
        <span className={cn('size-4 rounded-full', rival ? 'bg-primary' : 'bg-primary/50')} />
        <span className="h-1.5 w-10 rounded-full bg-muted-foreground/25" />
      </div>
      <div className="grid grid-cols-3 gap-1">
        {Array.from({ length: 6 }, (_, index) => {
          const isGap = index === GAP_TILE
          if (isGap && !rival) {
            return (
              <span key={index} className="relative aspect-square rounded-md border border-dashed border-border/50">
                <motion.span
                  className="absolute inset-0 rounded-md border-2 border-dashed border-warning"
                  animate={reduce ? { opacity: 1 } : { opacity: [0, 0, 1, 1, 0] }}
                  transition={reduce ? undefined : { duration: LOOP, repeat: Infinity, times: [0, 0.45, 0.52, 0.85, 0.92] }}
                />
              </span>
            )
          }
          return (
            <span
              key={index}
              className={cn(
                'relative flex aspect-square items-center justify-center rounded-md',
                isGap ? 'bg-primary text-primary-foreground' : index % 2 ? 'bg-primary/15' : 'bg-primary/30',
              )}
            >
              {isGap ? (
                <>
                  <Play className="size-3 fill-current" />
                  <motion.span
                    className="absolute -inset-1 rounded-lg ring-[3px] ring-warning"
                    animate={reduce ? { opacity: 1 } : { opacity: [0, 0, 1, 1, 0], scale: [0.8, 0.8, 1, 1, 0.8] }}
                    transition={
                      reduce ? undefined : { duration: LOOP, repeat: Infinity, times: [0, 0.4, 0.46, 0.85, 0.92] }
                    }
                  />
                </>
              ) : null}
            </span>
          )
        })}
      </div>
      <p
        className={cn(
          'mt-2 text-center text-[10px] font-semibold',
          rival ? 'text-primary' : 'text-muted-foreground',
        )}
      >
        {who}
      </p>
    </div>
  )
}

export function CompareAnimation({ className }: { className?: string }) {
  const reduce = useReducedMotion()
  return (
    <div className={cn('relative mx-auto h-52 w-full max-w-xs sm:h-60', className)} aria-hidden="true">
      <div className="absolute inset-[8%] rounded-full bg-primary/10 blur-2xl" />
      <MiniPage who="You" side="own" />
      <MiniPage who="Competitor" side="rival" />

      <span className="absolute left-1/2 top-[46%] flex size-8 -translate-x-1/2 items-center justify-center rounded-full bg-card text-[10px] font-extrabold text-primary shadow-md ring-4 ring-primary/10">
        VS
      </span>

      {/* the "Gap found" tag over the competitor's reel */}
      <motion.span
        className="absolute right-[4%] top-0 flex items-center gap-1 rounded-full bg-warning px-2.5 py-1 text-[11px] font-bold text-warning-foreground shadow-lg"
        animate={reduce ? { opacity: 1 } : { opacity: [0, 0, 1, 1, 0], y: [8, 8, 0, 0, 8], scale: [0.7, 0.7, 1, 1, 0.7] }}
        transition={reduce ? undefined : { duration: LOOP, repeat: Infinity, times: [0, 0.46, 0.53, 0.85, 0.92] }}
      >
        <Sparkle className="size-3 fill-current" /> Gap found
      </motion.span>

      {/* the magnifying glass: reads your page, then the competitor's, then stops on the gap */}
      <motion.span
        className="absolute flex size-14 items-center justify-center rounded-full bg-card/90 text-primary shadow-xl ring-[6px] ring-primary/15 backdrop-blur-sm sm:size-16"
        animate={
          reduce
            ? { left: '76%', top: '58%' }
            : {
                left: ['8%', '22%', '10%', '58%', '76%', '76%', '8%'],
                top: ['30%', '50%', '58%', '24%', '58%', '58%', '30%'],
              }
        }
        transition={
          reduce
            ? undefined
            : { duration: LOOP, repeat: Infinity, ease: 'easeInOut', times: [0, 0.12, 0.22, 0.32, 0.4, 0.86, 1] }
        }
      >
        <Search className="size-7 sm:size-8" strokeWidth={2.6} />
      </motion.span>

      <Sparkle className="absolute bottom-[6%] left-[6%] size-4 fill-warning text-warning" />
    </div>
  )
}
