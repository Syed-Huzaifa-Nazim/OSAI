import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'

interface StageConnectorProps {
  orientation: 'horizontal' | 'vertical'
  /** Drawn when the stage before it has completed. */
  active: boolean
  /** Continuously animates while the next stage is running. */
  flowing?: boolean
  className?: string
}

/**
 * The line between two stages. It draws itself once the preceding stage
 * completes, and carries a travelling highlight while the next stage runs,
 * so the eye is pulled along the pipeline in the direction of progress.
 */
export function StageConnector({
  orientation,
  active,
  flowing = false,
  className,
}: StageConnectorProps) {
  const reduced = usePrefersReducedMotion()
  const isHorizontal = orientation === 'horizontal'

  return (
    <div
      className={cn(
        'relative shrink-0 overflow-hidden',
        isHorizontal ? 'h-px min-w-6 flex-1' : 'ml-[27px] h-8 w-px',
        className,
      )}
      aria-hidden="true"
    >
      <span className="absolute inset-0 bg-border/20" />
      <motion.span
        className="absolute inset-0 origin-left bg-primary/70"
        style={isHorizontal ? undefined : { transformOrigin: 'top' }}
        initial={false}
        animate={{ scaleX: isHorizontal && active ? 1 : isHorizontal ? 0 : 1, scaleY: isHorizontal ? 1 : active ? 1 : 0 }}
        transition={reduced ? { duration: 0 } : { duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      />
      {flowing && !reduced ? (
        <motion.span
          className={cn(
            'absolute bg-gradient-to-r from-transparent via-primary to-transparent',
            isHorizontal ? 'inset-y-0 w-8' : 'inset-x-0 h-8 bg-gradient-to-b',
          )}
          animate={isHorizontal ? { x: ['-100%', '400%'] } : { y: ['-100%', '400%'] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: 'linear' }}
        />
      ) : null}
    </div>
  )
}
