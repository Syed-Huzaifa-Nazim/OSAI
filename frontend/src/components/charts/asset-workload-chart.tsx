import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ContentSuggestion } from '@/types/domain'
import { titleCase } from '@/lib/utils'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/** Groups suggested content by format, surfacing the real estimated workload. */
export function AssetWorkloadChart({ suggestions }: { suggestions: ContentSuggestion[] }) {
  const theme = useChartTheme()
  const totals = new Map<string, { hours: number; count: number }>()
  for (const suggestion of suggestions) {
    if (suggestion.status === 'dismissed') continue
    const current = totals.get(suggestion.kind) ?? { hours: 0, count: 0 }
    totals.set(suggestion.kind, { hours: current.hours + suggestion.estimatedEffortHours, count: current.count + 1 })
  }
  const data = [...totals.entries()]
    .map(([kind, values]) => ({ kind: titleCase(kind), ...values }))
    .sort((a, b) => b.hours - a.hours)

  return (
    <ChartFrame
      title="Content workload"
      description="Estimated execution time, grouped by asset format."
      table={{ columns: ['Format', 'Assets', 'Hours'], rows: data.map((row) => [row.kind, row.count, `${row.hours}h`]) }}
      height={Math.max(200, data.length * 42)}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 4 }}>
          <CartesianGrid horizontal={false} stroke={theme.grid} />
          <XAxis type="number" allowDecimals={false} tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} unit="h" />
          <YAxis type="category" dataKey="kind" width={90} tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip content={<ChartTooltip format={(value) => `${value} hours`} />} />
          <Bar dataKey="hours" name="Estimated hours" radius={[0, 4, 4, 0]} barSize={16}>
            {data.map((row, index) => <Cell key={row.kind} fill={theme.categorical[index % theme.categorical.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
