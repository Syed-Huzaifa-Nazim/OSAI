import { Trophy } from 'lucide-react'
import type { DarazPart, DarazStanding as Side } from '@/types/pipeline'

function rank(side: Side, top: number): string {
  if (side.rank) return `#${side.rank}`
  return top ? `not in the top ${top}` : 'not known'
}

function num(value: number | null, prefix = ''): string {
  return value === null || value === undefined
    ? '—'
    : `${prefix}${Math.round(value).toLocaleString()}`
}

/**
 * Where both listings stand on Daraz today: rank, sold, reviews, rating. These are results the seller wants to raise,
 * so they are shown here, small, and never as gaps; the gaps below are the changes that help raise them.
 */
export function DarazStanding({ part }: { part: DarazPart }) {
  const { standing, reviews } = part
  const stats: { label: string; you: string; them: string }[] = [
    {
      label: standing.search_word ? `Rank for “${standing.search_word}”` : 'Search rank',
      you: rank(standing.you, standing.top_listings),
      them: rank(standing.competitor, standing.top_listings),
    },
    { label: 'Sold', you: num(standing.you.sold), them: num(standing.competitor.sold) },
    { label: 'Reviews', you: num(standing.you.reviews), them: num(standing.competitor.reviews) },
    {
      label: 'Rating',
      you: standing.you.rating ? `${standing.you.rating.toFixed(1)} ★` : '—',
      them: standing.competitor.rating ? `${standing.competitor.rating.toFixed(1)} ★` : '—',
    },
  ]
  return (
    <section
      aria-label="Where you stand"
      className="rounded-2xl border border-border/20 bg-card p-4 shadow-sm"
    >
      <div className="flex items-center gap-2">
        <Trophy className="size-4 text-primary" aria-hidden="true" />
        <h2 className="font-display text-base font-bold">Where you stand on Daraz today</h2>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="rounded-xl bg-muted/40 px-3 py-2">
            <dt className="truncate text-xs text-muted-foreground">{s.label}</dt>
            <dd className="mt-0.5 flex items-baseline justify-between gap-2 tabular-nums">
              <span className="font-display text-lg font-bold" title="You">
                {s.you}
              </span>
              <span className="text-xs text-muted-foreground" title="Your competitor">
                vs {s.them}
              </span>
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-xs text-muted-foreground">
        You first, then your competitor. These numbers grow with sales and reviews; the gaps below
        are what you can change today.
      </p>
      {standing.note ? (
        <p className="mt-3 rounded-xl bg-success/10 px-3 py-2 text-sm">{standing.note}</p>
      ) : null}
      {reviews.note ? <p className="mt-2 text-xs text-muted-foreground">{reviews.note}</p> : null}
    </section>
  )
}
