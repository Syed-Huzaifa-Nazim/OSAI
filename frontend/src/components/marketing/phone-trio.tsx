import { motion, useReducedMotion } from 'framer-motion'
import { cn } from '@/lib/utils'

/** A phone frame and a floating dotted square, used by the phone app preview (app-phones.tsx). */

export function Phone({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        'relative w-44 overflow-hidden rounded-[2rem] border-[6px] border-foreground/85 bg-card shadow-[0_30px_60px_-24px_hsl(var(--shadow-color)/0.55)] sm:w-52',
        className,
      )}
    >
      <span className="absolute left-1/2 top-1.5 z-10 h-4 w-16 -translate-x-1/2 rounded-full bg-foreground/85" aria-hidden="true" />
      {children}
    </div>
  )
}

/** A soft dotted square floating behind the phones (like stitched fabric). */
export function Pattern({ className, delay }: { className: string; delay: number }) {
  const reduce = useReducedMotion()
  return (
    <motion.span
      className={cn(
        'absolute size-24 rounded-2xl [background-image:radial-gradient(currentColor_2px,transparent_2.5px)] [background-size:10px_10px] sm:size-28',
        className,
      )}
      animate={reduce ? undefined : { y: [0, -10, 0], rotate: [0, 4, 0] }}
      transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay }}
      aria-hidden="true"
    />
  )
}
