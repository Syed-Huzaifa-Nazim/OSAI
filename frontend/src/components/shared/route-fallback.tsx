import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Shown while a lazily-loaded route chunk is fetched.
 *
 * Deliberately quiet: on a warm connection this is visible for a few frames,
 * and a full skeleton flashing in and straight back out reads as a glitch. The
 * live region announces the load for anyone who cannot see the spinner.
 */
export function RouteFallback({ className }: { className?: string }) {
  return (
    <div
      className={cn('flex min-h-[50vh] items-center justify-center', className)}
      role="status"
      aria-live="polite"
    >
      <Loader2 className="size-5 animate-spin text-primary" aria-hidden="true" />
      <span className="sr-only">Loading page</span>
    </div>
  )
}
