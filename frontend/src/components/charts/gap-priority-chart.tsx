import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { Gap, GapPriority } from '@/types/domain'
import { titleCase } from '@/lib/utils'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { sequentialStep, useChartTheme } from './chart-theme'

const ORDER: GapPriority[] = ['critical', 'high', 'medium', 'low']

/**
 * Priority is ordinal, critical outranks low, so it takes a single-hue ramp
 * and the reader sees the order in the colour itself.
 */
export function GapPriorityChart({ gaps }: { gaps: Gap[] }) {
  const theme = useChartTheme()

  const data = ORDER.map((priority, index) => ({
    priority: titleCase(priority),
    count: gaps.filter((gap) => (gap.userPriority ?? gap.priority) === priority).length,
    // Reversed so critical takes the darkest step.
    color: sequentialStep(theme, ORDER.length - 1 - index, ORDER.length),
  })).filter((row) => row.count > 0)

  return (
    <ChartFrame
      title="Gaps by priority"
      description="Agent priority, overridden by yours where you set one."
      series={data.map((row) => ({ label: row.priority, color: row.color }))}
      table={{
        columns: ['Priority', 'Gaps'],
        rows: data.map((row) => [row.priority, row.count]),
      }}
      height={220}
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip content={<ChartTooltip />} />
          <Pie
            data={data}
            dataKey="count"
            nameKey="priority"
            innerRadius={52}
            outerRadius={82}
            paddingAngle={2}
            strokeWidth={2}
            stroke={theme.surface}
            label={({ name, value }) => `${name}: ${value}`}
            labelLine={false}
          >
            {data.map((row) => (
              <Cell key={row.priority} fill={row.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
