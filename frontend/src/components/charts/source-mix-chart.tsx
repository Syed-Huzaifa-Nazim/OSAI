import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ScrapedSource } from '@/types/domain'
import { titleCase } from '@/lib/utils'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/** What the Scout Agent actually collected, by source kind. */
export function SourceMixChart({ sources }: { sources: ScrapedSource[] }) {
  const theme = useChartTheme()

  const counts = new Map<string, number>()
  for (const source of sources) {
    counts.set(source.kind, (counts.get(source.kind) ?? 0) + 1)
  }
  const data = [...counts.entries()]
    .map(([kind, count]) => ({ kind: titleCase(kind), count }))
    .sort((a, b) => b.count - a.count)

  return (
    <ChartFrame
      title="Sources collected"
      description="The corpus the Insight Agent reasoned over."
      table={{ columns: ['Source type', 'Count'], rows: data.map((row) => [row.kind, row.count]) }}
      height={Math.max(160, data.length * 36)}
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
            dataKey="kind"
            width={110}
            tick={{ fill: theme.textMuted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip cursor={{ fill: theme.grid }} content={<ChartTooltip />} />
          <Bar
            dataKey="count"
            name="Sources"
            radius={[0, 4, 4, 0]}
            barSize={14}
            label={{ position: 'right', fill: theme.textMuted, fontSize: 11 }}
          >
            {data.map((row) => (
              <Cell key={row.kind} fill={theme.categorical[0]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
