import { Brain, Film, MessageCircle, TrendingUp, ImageIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { AnalysisPart } from '@/types/pipeline'

const pct = (value: number | null | undefined) =>
  value === null || value === undefined ? 'n/a' : `${Math.round(value * 100)}%`

const mix = (shares: Record<string, number> | undefined) =>
  shares && Object.keys(shares).length > 0
    ? Object.entries(shares)
        .sort((a, b) => b[1] - a[1])
        .map(([format, share]) => `${format} ${pct(share)}`)
        .join(', ')
    : 'n/a'

function Row({
  icon,
  title,
  method,
  you,
  them,
  result,
}: {
  icon: ReactNode
  title: string
  method: string
  you?: string
  them?: string
  result: string
}) {
  return (
    <div className="flex gap-3 border-t border-border/15 py-3 first:border-t-0 first:pt-0">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <div className="min-w-0 flex-1 space-y-1 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{title}</p>
          <Badge variant="outline">{method}</Badge>
        </div>
        {you !== undefined ? (
          <p className="text-muted-foreground">
            <span className="text-foreground">You:</span> {you}
          </p>
        ) : null}
        {them !== undefined ? (
          <p className="text-muted-foreground">
            <span className="text-foreground">Competitor:</span> {them}
          </p>
        ) : null}
        <p>{result}</p>
      </div>
    </div>
  )
}

/** What each part of the Instagram analysis found, including parts that produced no gap. */
export function AnalysisSummary({ parts }: { parts: AnalysisPart[] }) {
  return (
    <>
      {parts.map((part) => {
        const m = part.model
        const c = part.comments
        const gapsWord = (n: number | undefined) => `${n ?? 0} gap${n === 1 ? '' : 's'} found`
        return (
          <Card key={part.competitor} className="space-y-1 p-5">
            <p className="mb-3 font-display text-sm font-semibold">
              How your gaps were found: you vs @{part.competitor}
            </p>

            <Row
              icon={<Brain className="size-4" />}
              title="Engagement grade and habits"
              method="Your trained Random Forest + SHAP"
              you={m.status === 'ran' ? `${m.user_grade} (${pct(m.user_good_chance)} chance of "good")` : undefined}
              them={
                m.status === 'ran'
                  ? `${m.competitor_grade} (${pct(m.competitor_good_chance)} chance of "good")`
                  : undefined
              }
              result={
                m.status !== 'ran'
                  ? `Skipped: ${m.reason}`
                  : m.clear_difference
                    ? `The competitor is clearly ahead. ${gapsWord(m.habit_gaps)} in habits.`
                    : `The competitor is not clearly ahead (difference ${Math.round((m.difference ?? 0) * 100)} points; 10 needed). ${m.habit_gaps} habit difference${m.habit_gaps === 1 ? '' : 's'} shown as low confidence.`
              }
            />

            <Row
              icon={<MessageCircle className="size-4" />}
              title="Comment mood"
              method="LLM (Groq)"
              you={
                c.user
                  ? `${pct(c.user.positive)} positive, ${pct(c.user.negative)} negative (${c.user.scored} comments)`
                  : undefined
              }
              them={
                c.competitor
                  ? `${pct(c.competitor.positive)} positive, ${pct(c.competitor.negative)} negative (${c.competitor.scored} comments)`
                  : undefined
              }
              result={
                c.status !== 'ran'
                  ? `Skipped: ${c.reason}`
                  : `${gapsWord(c.gaps)} (a gap needs a 15-point difference against you).`
              }
            />

            <Row
              icon={<Film className="size-4" />}
              title="Post formats"
              method="Direct comparison"
              you={mix(part.media_mix.user)}
              them={mix(part.media_mix.competitor)}
              result={`${gapsWord(part.media_mix.gaps)} (a gap needs a 25-point difference).`}
            />

            <Row
              icon={<TrendingUp className="size-4" />}
              title="Engagement trend (recent vs older posts)"
              method="Direct comparison"
              you={part.trend.user === null || part.trend.user === undefined ? 'n/a' : `${part.trend.user >= 0 ? '+' : ''}${pct(part.trend.user)}`}
              them={
                part.trend.competitor === null || part.trend.competitor === undefined
                  ? 'n/a'
                  : `${part.trend.competitor >= 0 ? '+' : ''}${pct(part.trend.competitor)}`
              }
              result={gapsWord(part.trend.gaps)}
            />

            <Row
              icon={<ImageIcon className="size-4" />}
              title="Image and video quality"
              method="Pretrained model"
              result={part.media_quality.reason}
            />
          </Card>
        )
      })}
    </>
  )
}
