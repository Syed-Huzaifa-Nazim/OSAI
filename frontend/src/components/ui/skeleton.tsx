import { cn } from '@/lib/utils'

/** Shimmer placeholder. Every data surface renders one while loading. */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('relative overflow-hidden rounded-md bg-muted/60', className)}
      aria-hidden="true"
      {...props}
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-foreground/[0.06] to-transparent" />
    </div>
  )
}

export { Skeleton }
