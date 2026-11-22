import { cn } from '@/lib/utils'

interface LogoProps {
  className?: string
  /** Hides the wordmark, leaving only the mark (for the collapsed sidebar). */
  markOnly?: boolean
}

/** The OptiStratixAI mark (public/brand/logo-wide.png): rising bars, a ring and an upward arrow. */
export function Logo({ className, markOnly = false }: LogoProps) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <img
        src="/brand/logo-wide.png"
        alt={markOnly ? 'OptiStratixAI' : ''}
        className="h-8 w-auto shrink-0 select-none"
        draggable={false}
      />
      {markOnly ? null : <span className="font-display text-base font-bold tracking-tight">OptiStratixAI</span>}
    </span>
  )
}
