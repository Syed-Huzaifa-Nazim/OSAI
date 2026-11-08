import { cn } from '@/lib/utils'

interface LogoProps {
  className?: string
  /** Hides the wordmark, leaving only the mark (for the collapsed sidebar). */
  markOnly?: boolean
}

/**
 * Three inputs converging on one validated output, the HITL story as a mark.
 */
export function Logo({ className, markOnly = false }: LogoProps) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <svg
        viewBox="0 0 32 32"
        className="size-7 shrink-0"
        role="img"
        aria-label="OptiStratixAI"
      >
        <circle cx="8" cy="8" r="2.6" className="fill-brand-butter-cream" />
        <circle cx="8" cy="24" r="2.6" className="fill-brand-warm-gray" />
        <circle cx="23" cy="16" r="3.6" className="fill-primary" />
        <path
          d="M10.4 9.4 L19.8 14.4 M10.4 22.6 L19.8 17.6"
          className="stroke-primary"
          strokeWidth="1.7"
          strokeLinecap="round"
          opacity="0.8"
        />
      </svg>
      {markOnly ? null : (
        <span className="font-display text-base font-semibold tracking-tight">
          OptiStratix<span className="text-primary">AI</span>
        </span>
      )}
    </span>
  )
}
