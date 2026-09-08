import { cn, formatPercent } from '@/lib/utils'

interface ConfidenceMeterProps {
  /** 0-1. */
  value: number
  className?: string
  showLabel?: boolean
}

/**
 * Agent confidence, shown as a segmented bar rather than a smooth gradient, * discrete segments discourage over-reading small differences.
 */
export function ConfidenceMeter({ value, className, showLabel = true }: ConfidenceMeterProps) {
  const segments = 5
  const filled = Math.round(value * segments)
  const tone =
    value >= 0.85 ? 'bg-success' : value >= 0.7 ? 'bg-primary' : 'bg-brand-butter-cream'

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div
        className="flex items-center gap-0.5"
        role="meter"
        aria-valuenow={Math.round(value * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Agent confidence"
      >
        {Array.from({ length: segments }).map((_, index) => (
          <span
            key={index}
            className={cn(
              'h-1.5 w-4 rounded-full transition-colors',
              index < filled ? tone : 'bg-muted',
            )}
          />
        ))}
      </div>
      {showLabel ? (
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          {formatPercent(value)}
        </span>
      ) : null}
    </div>
  )
}
