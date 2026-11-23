import { useState, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  CalendarClock,
  Clapperboard,
  Columns3,
  Film,
  ImageIcon,
  LayoutList,
  MessageSquareText,
  ScrollText,
  Search,
  Star,
  Tag,
  TrendingDown,
  UserRound,
  type LucideIcon,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { categoriesFor, groupByCategory, isDarazGap, type GapCategory } from '@/lib/gap-categories'
import { spring, staggerContainer, staggerItem } from '@/lib/motion'
import { cn } from '@/lib/utils'
import type { Gap } from '@/types/domain'
import type { ComparisonRow } from '@/types/pipeline'

interface Look {
  icon: LucideIcon
  tint: string
  chip: string
  bar: string
}

/** Each category's own colour (full class names, so Tailwind keeps them). */
const LOOK: Record<GapCategory | 'ahead' | 'compare' | 'all', Look> = {
  format: {
    icon: Clapperboard,
    tint: 'from-primary/10',
    chip: 'bg-primary/15 text-primary',
    bar: 'bg-primary',
  },
  schedule: {
    icon: CalendarClock,
    tint: 'from-warning/15',
    chip: 'bg-warning/20 text-warning-ink',
    bar: 'bg-warning',
  },
  captions: {
    icon: MessageSquareText,
    tint: 'from-blush/15',
    chip: 'bg-blush/20 text-blush',
    bar: 'bg-blush',
  },
  photos: {
    icon: ImageIcon,
    tint: 'from-success/10',
    chip: 'bg-success/15 text-success',
    bar: 'bg-success',
  },
  reels: {
    icon: Film,
    tint: 'from-primary/15',
    chip: 'bg-primary/15 text-primary',
    bar: 'bg-primary',
  },
  weak: {
    icon: TrendingDown,
    tint: 'from-destructive/10',
    chip: 'bg-destructive/15 text-destructive',
    bar: 'bg-destructive',
  },
  profile: {
    icon: UserRound,
    tint: 'from-secondary',
    chip: 'bg-secondary text-secondary-foreground',
    bar: 'bg-primary',
  },
  price: {
    icon: Tag,
    tint: 'from-warning/15',
    chip: 'bg-warning/20 text-warning-ink',
    bar: 'bg-warning',
  },
  title: {
    icon: Search,
    tint: 'from-primary/10',
    chip: 'bg-primary/15 text-primary',
    bar: 'bg-primary',
  },
  listing_photos: {
    icon: ImageIcon,
    tint: 'from-success/10',
    chip: 'bg-success/15 text-success',
    bar: 'bg-success',
  },
  details: {
    icon: ScrollText,
    tint: 'from-secondary',
    chip: 'bg-secondary text-secondary-foreground',
    bar: 'bg-primary',
  },
  reviews: {
    icon: MessageSquareText,
    tint: 'from-blush/15',
    chip: 'bg-blush/20 text-blush',
    bar: 'bg-blush',
  },
  ahead: {
    icon: Star,
    tint: 'from-success/15',
    chip: 'bg-success/15 text-success',
    bar: 'bg-success',
  },
  compare: {
    icon: Columns3,
    tint: 'from-primary/10',
    chip: 'bg-primary/15 text-primary',
    bar: 'bg-primary',
  },
  all: {
    icon: LayoutList,
    tint: 'from-muted',
    chip: 'bg-card text-foreground',
    bar: 'bg-muted-foreground',
  },
}

interface Props {
  gaps: Gap[]
  /** Renders one gap card with all its actions (keep / drop, explain, note). */
  renderGap: (gap: Gap, opts?: { stacked?: boolean }) => ReactNode
  /** True while the full list below is open. */
  showingAll: boolean
  onShowAll: () => void
  /** What you already do better than the competitor (from the analysis). */
  strengths?: { kind: string; label: string; detail: string }[]
  /** Every trait the trained models measured, side by side. */
  comparison?: ComparisonRow[]
}

type Extra = 'ahead' | 'compare'

type Group = {
  key: ComparisonRow['group']
  title: string
  note: string
  box: string
  icon: string
}

const DARAZ_GROUPS: Group[] = [
  {
    key: 'do_more',
    title: 'Change this',
    note: 'These help Daraz listings rank or sell, and yours is below the top listings.',
    box: 'border-warning/40 bg-warning/5',
    icon: '✅',
  },
  {
    key: 'fine',
    title: 'No change needed',
    note: 'Yours is already in the usual range of the top 20 listings for your search word.',
    box: 'border-border/25 bg-card',
    icon: '👍',
  },
]

const GROUPS: Group[] = [
  {
    key: 'do_more',
    title: 'Do more of this',
    note: 'These work for jewellery shops on Instagram, and you rarely do them.',
    box: 'border-warning/40 bg-warning/5',
    icon: '✅',
  },
  {
    key: 'doing_well',
    title: "You're doing well",
    note: 'These work for jewellery shops, and you already do them. Keep it up.',
    box: 'border-success/30 bg-success/5',
    icon: '⭐',
  },
  {
    key: 'competitor_does',
    title: 'Your competitor does this, you don’t',
    note: 'A clear difference, but not proven to bring more likes. Worth a try.',
    box: 'border-border/25 bg-card',
    icon: '💡',
  },
]

/** Two short bars: how often you and your competitor do it. */
function MiniBars({ row }: { row: ComparisonRow }) {
  if (row.you_share === undefined) {
    return (
      <dl className="mt-2 grid grid-cols-[7rem_1fr] gap-x-2 gap-y-1 text-xs">
        <dt className="font-semibold">You</dt>
        <dd className="text-muted-foreground">{row.you_text}</dd>
        <dt className="font-semibold">Competitor</dt>
        <dd className="text-muted-foreground">{row.competitor_text ?? '—'}</dd>
        {row.typical ? (
          <>
            <dt className="font-semibold">Top 20 listings</dt>
            <dd className="text-muted-foreground">{row.typical}</dd>
          </>
        ) : null}
      </dl>
    )
  }
  const bars = [
    { name: 'You', value: row.you_share, tone: 'bg-primary', text: row.you_text },
    {
      name: 'Competitor',
      value: row.competitor_share ?? 0,
      tone: 'bg-warning',
      text: row.competitor_text,
    },
  ]
  return (
    <div className="mt-2 space-y-1.5">
      {bars.map((b) =>
        b.text ? (
          <div
            key={b.name}
            className="grid grid-cols-[5.5rem_1fr] items-center gap-2 text-xs sm:grid-cols-[6rem_8rem_1fr]"
          >
            <span className="font-semibold">{b.name}</span>
            <span className="hidden h-2 overflow-hidden rounded-full bg-muted sm:block">
              <span
                className={cn('block h-full rounded-full', b.tone)}
                style={{ width: `${Math.round(b.value * 100)}%` }}
              />
            </span>
            <span className="text-muted-foreground">{b.text}</span>
          </div>
        ) : null,
      )}
    </div>
  )
}

/** One category card: its colour, how many gaps, and how many are already decided. */
function Tile({
  look,
  label,
  count,
  line,
  progress,
  onClick,
  active = false,
}: {
  look: Look
  label: string
  count: number | null
  line: string
  progress?: number
  onClick: () => void
  active?: boolean
}) {
  const Icon = look.icon
  return (
    <motion.button
      type="button"
      variants={staggerItem}
      whileHover={{ y: -4 }}
      transition={spring}
      onClick={onClick}
      aria-pressed={active || undefined}
      aria-label={`${label}${count !== null ? `: ${count}` : ''}`}
      className={cn(
        'group relative flex min-h-[8.5rem] flex-col overflow-hidden rounded-2xl border bg-gradient-to-br to-card p-4 text-left shadow-sm transition-shadow hover:shadow-glow',
        look.tint,
        active ? 'border-primary ring-2 ring-primary/30' : 'border-border/20',
      )}
    >
      <span
        className={cn(
          'pointer-events-none absolute -right-6 -top-6 size-24 rounded-full opacity-30 blur-2xl',
          look.bar,
        )}
        aria-hidden="true"
      />
      <div className="relative flex w-full items-start justify-between gap-2">
        <span
          className={cn(
            'flex size-11 items-center justify-center rounded-2xl shadow-sm',
            look.chip,
          )}
        >
          <Icon className="size-5" aria-hidden="true" />
        </span>
        {count !== null ? (
          <span className="font-display text-3xl font-bold tabular-nums leading-none">{count}</span>
        ) : null}
      </div>
      <div className="relative mt-3 min-w-0">
        <p className="font-display text-[0.95rem] font-semibold leading-tight">{label}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">{line}</p>
      </div>
      <div className="relative mt-auto flex items-center gap-2 pt-3">
        {progress !== undefined ? (
          <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <span
              className={cn('block h-full rounded-full transition-all', look.bar)}
              style={{ width: `${progress * 100}%` }}
            />
          </span>
        ) : (
          <span className="flex-1" />
        )}
        <ArrowRight
          className="size-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5"
          aria-hidden="true"
        />
      </div>
    </motion.button>
  )
}

/**
 * One card per kind of gap that was found. A card opens its gaps in a dialog. Kinds with nothing found are not shown
 * as cards; they are listed in one line, so the page stays short but nothing is hidden.
 */
export function GapCategories({
  gaps,
  renderGap,
  showingAll,
  onShowAll,
  strengths = [],
  comparison = [],
}: Props) {
  const [open, setOpen] = useState<GapCategory | null>(null)
  const [extra, setExtra] = useState<Extra | null>(null)
  const groups = groupByCategory(gaps)
  const categories = categoriesFor(gaps)
  const daraz = gaps.some(isDarazGap)
  const groupList = daraz ? DARAZ_GROUPS : GROUPS
  const current = categories.find((c) => c.key === open)
  const inDialog = open ? groups[open] : []
  const found = categories.filter((c) => groups[c.key].length > 0)
  const empty = categories.filter((c) => groups[c.key].length === 0)

  return (
    <>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4"
        aria-label="Gaps by category"
      >
        {found.map(({ key, label }) => {
          const list = groups[key]
          const proven = list.filter((g) => !g.details?.unproven).length
          const decided = list.filter((g) => g.decision !== 'pending').length
          const parts = [
            proven ? `${proven} found` : '',
            list.length - proven
              ? `${list.length - proven} ${daraz ? 'worth fixing' : 'to test'}`
              : '',
            `${decided}/${list.length} decided`,
          ]
          return (
            <Tile
              key={key}
              look={LOOK[key]}
              label={label}
              count={list.length}
              line={parts.filter(Boolean).join(' · ')}
              progress={decided / list.length}
              onClick={() => {
                setOpen(key)
              }}
            />
          )
        })}
        {strengths.length > 0 ? (
          <Tile
            look={LOOK.ahead}
            label="Where you're ahead"
            count={strengths.length}
            line="Keep doing these"
            onClick={() => {
              setExtra('ahead')
            }}
          />
        ) : null}
        {comparison.length > 0 ? (
          <Tile
            look={LOOK.compare}
            label={daraz ? 'Listing check-up' : 'Content check-up'}
            count={null}
            line={
              [
                comparison.filter((r) => r.group === 'do_more').length
                  ? `${comparison.filter((r) => r.group === 'do_more').length} to ${daraz ? 'change' : 'do more'}`
                  : '',
                comparison.filter((r) => r.group === (daraz ? 'fine' : 'doing_well')).length
                  ? `${comparison.filter((r) => r.group === (daraz ? 'fine' : 'doing_well')).length} ${daraz ? 'already fine' : 'going well'}`
                  : '',
              ]
                .filter(Boolean)
                .join(' · ') || 'What your competitor does differently'
            }
            onClick={() => {
              setExtra('compare')
            }}
          />
        ) : null}
        <Tile
          look={LOOK.all}
          label="All gaps"
          count={gaps.length}
          line={showingAll ? 'Showing below' : 'In one list'}
          active={showingAll}
          onClick={onShowAll}
        />
      </motion.div>

      {empty.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">Checked, nothing found:</span>{' '}
          {empty.map((c) => c.label).join(', ')}.
        </p>
      ) : null}

      <Dialog
        open={open !== null}
        onOpenChange={(value) => {
          if (!value) setOpen(null)
        }}
      >
        <DialogContent className="max-h-[88vh] max-w-4xl overflow-y-auto overflow-x-hidden">
          <DialogHeader>
            <DialogTitle>{current?.label}</DialogTitle>
            <DialogDescription>
              {current?.hint}. Keep or drop each gap, or press Explain for the reasons.
            </DialogDescription>
          </DialogHeader>
          <div className="min-w-0 space-y-4">
            {inDialog.map((gap) => renderGap(gap, { stacked: true }))}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={extra !== null}
        onOpenChange={(value) => {
          if (!value) setExtra(null)
        }}
      >
        <DialogContent className="max-h-[88vh] max-w-3xl overflow-y-auto overflow-x-hidden">
          {extra === 'ahead' ? (
            <>
              <DialogHeader>
                <DialogTitle>Where you&apos;re ahead</DialogTitle>
                <DialogDescription>
                  Things you already do better than your competitor. Keep doing them.
                </DialogDescription>
              </DialogHeader>
              <ul className="space-y-3">
                {strengths.map((s) => (
                  <li
                    key={s.label}
                    className="flex gap-3 rounded-2xl border border-success/25 bg-success/5 p-4"
                  >
                    <Star className="mt-0.5 size-4 shrink-0 text-success" aria-hidden="true" />
                    <div className="min-w-0">
                      <p className="font-semibold">{s.label}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{s.detail}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle>
                  {daraz ? 'Your listing check-up' : 'Your content check-up'}
                </DialogTitle>
                <DialogDescription>
                  {daraz
                    ? 'Each thing below is proven to help Daraz jewellery listings sell or rank. Yours is compared with your competitor and with the top 20 listings for your search word.'
                    : 'What your posts, captions and reels show, compared with your competitor and with what works for jewellery shops on Instagram.'}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-6">
                {groupList.map((g) => {
                  const list = comparison.filter((r) => r.group === g.key)
                  if (list.length === 0) return null
                  return (
                    <section key={g.key}>
                      <h3 className="font-display text-base font-bold">
                        <span aria-hidden="true">{g.icon}</span> {g.title}
                      </h3>
                      <p className="mb-3 text-sm text-muted-foreground">{g.note}</p>
                      <ul className="space-y-3">
                        {list.map((row) => (
                          <li key={row.key} className={cn('rounded-2xl border p-4', g.box)}>
                            <p className="font-semibold">{row.title}</p>
                            {row.why ? (
                              <p className="mt-1 text-sm text-muted-foreground">{row.why}</p>
                            ) : null}
                            <MiniBars row={row} />
                            {g.key !== 'doing_well' && row.tip ? (
                              <p className="mt-3 rounded-xl bg-card/80 px-3 py-2 text-sm">
                                <span className="font-semibold text-primary">Try this: </span>
                                {row.tip}
                              </p>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </section>
                  )
                })}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
