import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Gap } from '@/types/domain'
import { titleCase } from '@/lib/utils'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/**
 * Gaps by category. The categories are nominal, reordering them changes
 * nothing, so every bar takes the same slot-1 hue and bar length does the
 * work. Colouring these by value would spend the identity channel re-encoding
 * what the bar already shows.
 */
export function GapCategoryChart({ gaps }: { gaps: Gap[] }) {
  const theme = useChartTheme()

  const counts = new Map<string, number>()
  for (const gap of gaps) {
    counts.set(gap.category, (counts.get(gap.category) ?? 0) + 1)
  }
  const data = [...counts.entries()]
    .map(([category, count]) => ({ category: titleCase(category), count }))
    .sort((a, b) => b.count - a.count)

  return (
    <ChartFrame
      title="Gaps by category"
      description="Where the analysis found the most ground to make up."
      table={{
        columns: ['Category', 'Gaps'],
        rows: data.map((row) => [row.category, row.count]),
      }}
      height={Math.max(180, data.length * 38)}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 4 }}>
          <CartesianGrid horizontal={false} stroke={theme.grid} />
          <XAxis
            type="number"
            allowDecimals={false}
            tick={{ fill: theme.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="category"
            width={130}
            tick={{ fill: theme.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: theme.grid }}
            content={<ChartTooltip />}
          />
          <Bar dataKey="count" name="Gaps" radius={[0, 4, 4, 0]} barSize={14} label={{
            position: 'right',
            fill: theme.textMuted,
            fontSize: 11,
          }}>
            {data.map((row) => (
              <Cell key={row.category} fill={theme.categorical[0]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
