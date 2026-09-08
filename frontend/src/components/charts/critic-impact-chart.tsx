import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { CriticFeedback } from '@/types/domain'
import { titleCase } from '@/lib/utils'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/**
 * What the Critic actually did to the Strategist's draft, by dimension.
 * Evidence for the "reduces hallucinated insights" claim, in one glance.
 */
export function CriticImpactChart({ feedback }: { feedback: CriticFeedback[] }) {
  const theme = useChartTheme()

  const dimensions = ['strength', 'clarity', 'feasibility', 'evidence'] as const
  const data = dimensions
    .map((dimension) => ({
      dimension: titleCase(dimension),
      count: feedback.filter((item) => item.dimension === dimension).length,
    }))
    .filter((row) => row.count > 0)

  return (
    <ChartFrame
      title="Critic interventions by dimension"
      description="What the Critic challenged in the first draft."
      table={{
        columns: ['Dimension', 'Interventions'],
        rows: data.map((row) => [row.dimension, row.count]),
      }}
      height={200}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 8, bottom: 4, left: 4 }} barGap={2}>
          <CartesianGrid vertical={false} stroke={theme.grid} />
          <XAxis
            dataKey="dimension"
            tick={{ fill: theme.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: theme.axis }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: theme.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={28}
          />
          <Tooltip cursor={{ fill: theme.grid }} content={<ChartTooltip />} />
          <Bar
            dataKey="count"
            name="Interventions"
            radius={[4, 4, 0, 0]}
            barSize={30}
            label={{ position: 'top', fill: theme.textMuted, fontSize: 11 }}
          >
            {data.map((row) => (
              <Cell key={row.dimension} fill={theme.categorical[0]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
