import { Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { formatFieldType } from '@/lib/comparison-format'
import type { ComparisonGroup } from '@/types/domain'

interface ParameterGridProps {
  groups: ComparisonGroup[]
  selected: string | null
  loadingKey: string | null
  onSelect: (key: string) => void
}

/** The comparison lenses (A-H for Daraz), each showing who currently leads it. */
export function ParameterGrid({ groups, selected, loadingKey, onSelect }: ParameterGridProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {groups.map((group) => {
        const isSelected = selected === group.key
        return (
          <button
            key={group.key}
            type="button"
            onClick={() => {
              onSelect(group.key)
            }}
            aria-pressed={isSelected}
            className={cn(
              'flex h-full flex-col rounded-lg border bg-card p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              isSelected
                ? 'border-primary/60 bg-primary/5'
                : 'border-border/20 hover:border-primary/35',
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="flex size-7 items-center justify-center rounded-md bg-primary/15 font-display text-sm font-semibold text-primary">
                {group.letter}
              </span>
              <Verdict group={group} />
            </div>

            <h3 className="mt-3 font-display text-sm font-semibold">{group.label}</h3>
            <p className="mt-1 flex-1 text-xs text-muted-foreground">{group.description}</p>

            <div className="mt-3 flex items-center justify-between gap-2">
              <Badge variant="outline" className="truncate">
                {group.semanticFieldTypes.length === 0
                  ? 'Metadata only'
                  : `Semantic: ${group.semanticFieldTypes.map(formatFieldType).join(', ')}`}
              </Badge>
              {loadingKey === group.key ? (
                <Loader2 className="size-3.5 shrink-0 animate-spin text-primary" aria-label="Loading" />
              ) : null}
            </div>
          </button>
        )
      })}
    </div>
  )
}

function Verdict({ group }: { group: ComparisonGroup }) {
  const { ownWins, competitorWins } = group
  if (ownWins > competitorWins) {
    return <Badge variant="success">You lead {ownWins}–{competitorWins}</Badge>
  }
  if (competitorWins > ownWins) {
    return <Badge variant="destructive">Behind {ownWins}–{competitorWins}</Badge>
  }
  return <Badge variant="muted">Level</Badge>
}
