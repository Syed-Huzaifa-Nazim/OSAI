import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { formatDerived, formatFieldType, formatMetric } from '@/lib/comparison-format'
import type { MetricRow, ParameterComparison, ProductImage, ProductSide } from '@/types/domain'
import { ImageStrip } from './product-gallery'

interface ParameterResultsProps {
  result: ParameterComparison
  /** Both listings' photos, shown when the parameter compares images. */
  images?: { own: ProductImage[]; competitor: ProductImage[] }
}

/** The read-out for one selected parameter. */
export function ParameterResults({ result, images }: ParameterResultsProps) {
  const { parameter } = result
  // Keyed off the metric, not the parameter name, so any platform's parameter
  // that counts images gets the photos beside the count.
  const comparesImages = parameter.metrics.some((metric) => metric.field === 'image_count')

  return (
    <Card className="space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/15 font-display text-lg font-semibold text-primary">
            {parameter.letter}
          </span>
          <div className="min-w-0">
            <h2 className="font-display text-lg font-semibold">{parameter.label}</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">{parameter.description}</p>
          </div>
        </div>
        <Badge variant="outline">
          {result.metadataOnly
            ? 'Metadata comparison'
            : `Semantic search · ${parameter.semanticFieldTypes.map(formatFieldType).join(', ')}`}
        </Badge>
      </div>

      {parameter.insights.length > 0 ? (
        <div className="rounded-lg border border-primary/25 bg-primary/5 p-4">
          <h3 className="font-display text-sm font-semibold">Read-out</h3>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-muted-foreground">
            {parameter.insights.map((insight, index) => (
              <li key={index}>{insight}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <MetricTable metrics={parameter.metrics} />

      {comparesImages && images ? (
        <div className="space-y-3">
          <h3 className="font-display text-sm font-semibold">Product images</h3>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3 rounded-lg border border-border/20 bg-muted/15 p-4">
              <div className="flex items-center justify-between gap-2">
                <Badge variant="default">Your product</Badge>
                <span className="text-xs text-muted-foreground">
                  {images.own.length} image{images.own.length === 1 ? '' : 's'}
                </span>
              </div>
              <ImageStrip images={images.own} productName={result.own.productName} />
            </div>
            <div className="space-y-3 rounded-lg border border-border/20 bg-muted/15 p-4">
              <div className="flex items-center justify-between gap-2">
                <Badge variant="secondary">Competitor</Badge>
                <span className="text-xs text-muted-foreground">
                  {images.competitor.length} image{images.competitor.length === 1 ? '' : 's'}
                </span>
              </div>
              <ImageStrip images={images.competitor} productName={result.competitor.productName} />
            </div>
          </div>
        </div>
      ) : null}

      {!result.metadataOnly ? (
        <div className="space-y-3">
          <div>
            <h3 className="font-display text-sm font-semibold">Retrieved content</h3>
            {parameter.query ? (
              <p className="mt-1 text-xs text-muted-foreground">
                Query: <em>&ldquo;{parameter.query}&rdquo;</em>
              </p>
            ) : null}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <SideColumn side={result.own} label="Your product" />
            <SideColumn side={result.competitor} label="Competitor" />
          </div>
        </div>
      ) : null}
    </Card>
  )
}

function MetricTable({ metrics }: { metrics: MetricRow[] }) {
  if (metrics.length === 0) return null

  return (
    <div className="overflow-hidden rounded-lg border border-border/20">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-border/20 bg-muted/25">
              <th scope="col" className="p-3 font-medium">Metric</th>
              <th scope="col" className="p-3 font-medium">Your product</th>
              <th scope="col" className="p-3 font-medium">Competitor</th>
              <th scope="col" className="p-3 font-medium">Gap</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => (
              <tr key={metric.field} className="border-b border-border/10 last:border-0">
                <th scope="row" className="p-3 align-top font-normal">
                  <span className="block">{metric.label}</span>
                  {metric.higherIsBetter !== null ? (
                    <span className="text-xs text-muted-foreground">
                      {metric.higherIsBetter ? 'higher is better' : 'lower is better'}
                    </span>
                  ) : null}
                </th>
                <ValueCell metric={metric} side="own" />
                <ValueCell metric={metric} side="competitor" />
                <td className="p-3 align-top text-xs">
                  {metric.deltaLabel ? (
                    <span
                      className={cn(
                        metric.winner === 'own' && 'text-success',
                        metric.winner === 'competitor' && 'text-destructive',
                        metric.winner === 'tie' && 'text-muted-foreground',
                      )}
                    >
                      {metric.deltaLabel}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">not comparable</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ValueCell({ metric, side }: { metric: MetricRow; side: 'own' | 'competitor' }) {
  const leads = metric.winner === side
  return (
    <td className={cn('p-3 align-top tabular-nums', leads && 'font-medium')}>
      <span className="break-words">{formatMetric(metric[side], metric.kind, metric.unit, side)}</span>
      {leads ? (
        <Badge variant="success" className="ml-2">
          lead
        </Badge>
      ) : null}
    </td>
  )
}

function SideColumn({ side, label }: { side: ProductSide; label: string }) {
  const derived = Object.entries(side.derived)

  return (
    <div className="space-y-3 rounded-lg border border-border/20 bg-muted/15 p-4">
      <div className="min-w-0">
        <Badge variant={side.role === 'own' ? 'default' : 'secondary'}>{label}</Badge>
        <h4 className="mt-2 truncate text-sm font-medium" title={side.productName}>
          {side.productName}
        </h4>
      </div>

      {derived.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {derived.map(([key, value]) => {
            const chip = formatDerived(key, value)
            return (
              <Badge key={key} variant="muted">
                {chip.label}: <span className="font-mono">{chip.value}</span>
              </Badge>
            )
          })}
        </div>
      ) : null}

      {side.snippets.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No matching text was stored for this parameter.
        </p>
      ) : (
        <ul className="space-y-2">
          {side.snippets.map((snippet, index) => (
            <li
              key={`${snippet.fieldType}-${snippet.chunkIndex}-${index}`}
              className="rounded-md border border-border/15 bg-card p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <Badge variant="outline">{formatFieldType(snippet.fieldType)}</Badge>
                {snippet.score !== null ? (
                  <span
                    className="font-mono text-xs text-muted-foreground"
                    title="Cosine similarity to the parameter query"
                  >
                    {Math.round(snippet.score * 100)}% match
                  </span>
                ) : null}
              </div>
              <p className="mt-2 whitespace-pre-line text-sm text-muted-foreground">
                {snippet.text}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
