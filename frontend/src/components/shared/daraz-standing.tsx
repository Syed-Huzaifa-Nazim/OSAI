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
 * Daraz results for both listings: rank, sold, reviews, rating, price. These are what the seller wants to raise,
 * so they are shown here and never as gaps; the gaps below are the changes that help raise them.
 */
export function DarazStanding({ part }: { part: DarazPart }) {
  const { standing, reviews } = part
  const rows: { label: string; you: string; them: string }[] = [
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
    {
      label: 'Price',
      you: num(standing.you.price, 'Rs '),
      them: num(standing.competitor.price, 'Rs '),
    },
  ]
  return (
    <section
      aria-label="Where you stand"
      className="rounded-2xl border border-border/20 bg-card p-4 shadow-sm"
    >
      <div className="flex items-center gap-2">
        <Trophy className="size-4 text-primary" aria-hidden="true" />
        <h2 className="font-display text-base font-bold">Where you stand</h2>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        These are results, not gaps. The gaps below are the changes proven to help Daraz jewellery
        listings rank higher or sell more.
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[22rem] text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th className="py-1 pr-3 font-medium" scope="col">
                <span className="sr-only">Measure</span>
              </th>
              <th className="py-1 pr-3 font-semibold text-foreground" scope="col">
                You
              </th>
              <th className="py-1 font-semibold text-foreground" scope="col">
                Competitor
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label} className="border-t border-border/15">
                <th scope="row" className="py-1.5 pr-3 text-left font-medium text-muted-foreground">
                  {r.label}
                </th>
                <td className="py-1.5 pr-3 tabular-nums">{r.you}</td>
                <td className="py-1.5 tabular-nums">{r.them}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {reviews.note ? <p className="mt-2 text-xs text-muted-foreground">{reviews.note}</p> : null}
      {standing.note ? (
        <p className="mt-3 rounded-xl bg-success/10 px-3 py-2 text-sm">{standing.note}</p>
      ) : null}
    </section>
  )
}
