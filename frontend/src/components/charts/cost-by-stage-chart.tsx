import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { RunCost } from '@/types/domain'
import { getStage } from '@/lib/pipeline-stages'
import { formatUsd, truncate } from '@/lib/utils'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/** Where the LLM spend went. One series, so no legend, the title names it. */
export function CostByStageChart({ cost }: { cost: RunCost }) {
  const theme = useChartTheme()

  const data = cost.byStage.map((row) => ({
    stage: `${row.stage}. ${truncate(getStage(row.stage).title, 18)}`,
    cost: row.costUsd,
    tokens: row.tokens,
  }))

  return (
    <ChartFrame
      title="Cost by stage"
      description={`${formatUsd(cost.totalCostUsd)} across this run.`}
      table={{
        columns: ['Stage', 'Tokens', 'Cost'],
        rows: data.map((row) => [row.stage, row.tokens.toLocaleString(), formatUsd(row.cost)]),
      }}
      height={240}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }} barGap={2}>
          <CartesianGrid vertical={false} stroke={theme.grid} />
          <XAxis
            dataKey="stage"
            tick={{ fill: theme.textMuted, fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: theme.axis }}
            interval={0}
            angle={-18}
            textAnchor="end"
            height={64}
          />
          <YAxis
            tick={{ fill: theme.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value: number) => formatUsd(value)}
            width={62}
          />
          <Tooltip cursor={{ fill: theme.grid }} content={<ChartTooltip format={formatUsd} />} />
          <Bar dataKey="cost" name="Cost" radius={[4, 4, 0, 0]} barSize={26}>
            {data.map((row) => (
              <Cell key={row.stage} fill={theme.categorical[0]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
