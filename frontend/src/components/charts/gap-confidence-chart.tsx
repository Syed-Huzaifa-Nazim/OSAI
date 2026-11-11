import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import type { Gap } from '@/types/domain'
import { titleCase } from '@/lib/utils'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/** Average evidence confidence by opportunity category. */
export function GapConfidenceChart({ gaps }: { gaps: Gap[] }) {
  const theme = useChartTheme()
  const totals = new Map<string, { total: number; count: number }>()
  for (const gap of gaps) {
    const current = totals.get(gap.category) ?? { total: 0, count: 0 }
    totals.set(gap.category, { total: current.total + gap.confidence, count: current.count + 1 })
  }
  const data = [...totals.entries()]
    .map(([category, values]) => ({
      category: titleCase(category),
      confidence: Math.round((values.total / values.count) * 100),
    }))
    .sort((a, b) => a.category.localeCompare(b.category))

  return (
    <ChartFrame
      title="Evidence confidence"
      description="Average retrieval confidence for each opportunity area."
      table={{ columns: ['Category', 'Confidence'], rows: data.map((row) => [row.category, `${row.confidence}%`]) }}
      height={270}
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke={theme.grid} />
          <PolarAngleAxis dataKey="category" tick={{ fill: theme.textMuted, fontSize: 11 }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Tooltip content={<ChartTooltip format={(value) => `${value}%`} />} />
          <Radar
            dataKey="confidence"
            name="Confidence"
            stroke={theme.categorical[1]}
            fill={theme.categorical[1]}
            fillOpacity={0.28}
          />
        </RadarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
