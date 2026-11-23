import { Link } from 'react-router-dom'
import { LayoutGrid } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { PlatformInfo, PlatformKey } from '@/lib/platform-groups'
import { PlatformMark } from './platform-section'

export type PlatformChoice = PlatformKey | 'all'

interface Item {
  key: PlatformChoice
  label: string
  icon: PlatformInfo['icon']
  tone: string
  logo?: string
  count: number
  /** Extra line under the count, e.g. "1 awaiting you". */
  note?: string
}

function items(groups: (PlatformInfo & { count: number; note?: string })[], withAll: boolean): Item[] {
  const total = groups.reduce((sum, g) => sum + g.count, 0)
  const all: Item = { key: 'all', label: 'All', icon: LayoutGrid, tone: 'bg-muted text-foreground', count: total }
  return [...(withAll ? [all] : []), ...groups]
}

function Body({ item, active }: { item: Item; active: boolean }) {
  return (
    <>
      <PlatformMark platform={{ ...item, key: item.key === 'all' ? 'demo' : item.key }} />
      <span className="min-w-0 text-left">
        <span className={cn('block truncate font-display text-sm font-bold', active && 'text-primary')}>
          {item.label}
        </span>
        <span className="block text-xs text-muted-foreground">
          {item.count} project{item.count === 1 ? '' : 's'}
          {item.note ? ` · ${item.note}` : ''}
        </span>
      </span>
    </>
  )
}

const BOX =
  'flex items-center gap-3 rounded-2xl border bg-card p-3 text-left shadow-sm transition-all hover:border-primary/40 hover:shadow-glow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

/** Platform cards (All, Instagram, Daraz...): pick one to see only its projects. */
export function PlatformPicker({
  groups,
  value,
  onChange,
  withAll = true,
}: {
  groups: (PlatformInfo & { count: number; note?: string })[]
  value: PlatformChoice
  onChange: (value: PlatformChoice) => void
  withAll?: boolean
}) {
  return (
    <div role="tablist" aria-label="Platforms" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {items(groups, withAll).map((item) => {
        const active = item.key === value
        return (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => {
              onChange(item.key)
            }}
            className={cn(BOX, active ? 'border-primary/60 ring-2 ring-primary/20' : 'border-border/20')}
          >
            <Body item={item} active={active} />
          </button>
        )
      })}
    </div>
  )
}

/** The same cards as links (the dashboard): each opens the Projects page on that platform. */
export function PlatformLinks({ groups }: { groups: (PlatformInfo & { count: number; note?: string })[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items(groups, false).map((item) => (
        <Link key={item.key} to={`/app/projects?platform=${item.key}`} className={cn(BOX, 'border-border/20')}>
          <Body item={item} active={false} />
        </Link>
      ))}
    </div>
  )
}
