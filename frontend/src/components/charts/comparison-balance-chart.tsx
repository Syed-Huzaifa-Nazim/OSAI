import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ComparisonGroup } from '@/types/domain'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/** Direct metric wins by comparison lens, not an inferred overall score. */
export function ComparisonBalanceChart({ groups }: { groups: ComparisonGroup[] }) {
  const theme = useChartTheme()
  const data = groups.map((group) => ({ label: group.letter, yours: group.ownWins, competitor: group.competitorWins, name: group.label }))

  return (
    <ChartFrame
      title="Comparison balance"
      description="Direct metric wins in each comparison parameter."
      series={[{ label: 'Your brand', color: theme.categorical[1] }, { label: 'Their listing', color: theme.categorical[0] }]}
      table={{ columns: ['Parameter', 'Your wins', 'Competitor wins'], rows: data.map((row) => [row.name, row.yours, row.competitor]) }}
      height={260}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 8, bottom: 4, left: 4 }} barGap={3}>
          <CartesianGrid vertical={false} stroke={theme.grid} />
          <XAxis dataKey="label" tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: theme.axis }} />
          <YAxis allowDecimals={false} tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} width={28} />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey="yours" name="Your wins" fill={theme.categorical[1]} radius={[4, 4, 0, 0]} />
          <Bar dataKey="competitor" name="Competitor wins" fill={theme.categorical[0]} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
