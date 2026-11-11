import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Initiative } from '@/types/domain'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/** A delivery-focused view of the strategy's actual initiative timings. */
export function InitiativeTimelineChart({ initiatives }: { initiatives: Initiative[] }) {
  const theme = useChartTheme()
  const data = initiatives
    .map((initiative, index) => ({
      name: `#${index + 1}`,
      title: initiative.title,
      weeks: initiative.timelineWeeks,
      effort: initiative.effort,
    }))
    .sort((a, b) => a.weeks - b.weeks)

  return (
    <ChartFrame
      title="Implementation runway"
      description="Estimated delivery time for each proposed initiative."
      table={{ columns: ['Initiative', 'Timeline', 'Effort'], rows: data.map((row) => [row.title, `${row.weeks} weeks`, row.effort]) }}
      height={Math.max(210, data.length * 48)}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 4 }}>
          <CartesianGrid horizontal={false} stroke={theme.grid} />
          <XAxis type="number" allowDecimals={false} tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} unit="w" />
          <YAxis type="category" dataKey="name" width={30} tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip content={<ChartTooltip format={(value) => `${value} weeks`} />} />
          <Bar dataKey="weeks" name="Timeline" radius={[0, 4, 4, 0]} barSize={18}>
            {data.map((row) => (
              <Cell key={row.title} fill={row.effort === 'high' ? theme.status.warning : row.effort === 'medium' ? theme.categorical[1] : theme.status.good} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
