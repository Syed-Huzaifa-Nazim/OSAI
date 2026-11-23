import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import type { PlatformInfo } from '@/lib/platform-groups'

/** A platform's own logo on a white tile, or its icon when it has no logo. */
export function PlatformMark({ platform, size = 'md' }: { platform: PlatformInfo; size?: 'sm' | 'md' }) {
  const Icon = platform.icon
  const box = size === 'sm' ? 'size-8 rounded-xl' : 'size-10 rounded-xl'
  if (platform.logo) {
    return (
      <span className={cn('flex shrink-0 items-center justify-center border border-border/20 bg-white p-1.5', box)}>
        <img src={platform.logo} alt="" className="size-full object-contain" />
      </span>
    )
  }
  return (
    <span className={cn('flex shrink-0 items-center justify-center', box, platform.tone)}>
      <Icon className={size === 'sm' ? 'size-4' : 'size-5'} aria-hidden="true" />
    </span>
  )
}

/** One platform's projects under a small heading: its logo, its name and how many projects it has. */
export function PlatformSection({
  platform,
  count,
  children,
  className,
}: {
  platform: PlatformInfo
  count: number
  children: ReactNode
  className?: string
}) {
  return (
    <section aria-label={`${platform.label} projects`} className={cn('space-y-3', className)}>
      <div className="flex items-center gap-2.5">
        <PlatformMark platform={platform} size="sm" />
        <h2 className="font-display text-base font-bold">{platform.label}</h2>
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-semibold tabular-nums text-muted-foreground">
          {count}
        </span>
      </div>
      {children}
    </section>
  )
}
