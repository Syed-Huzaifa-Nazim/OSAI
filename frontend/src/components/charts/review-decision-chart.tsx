import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { Gap } from '@/types/domain'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/** Human checkpoint decisions, always derived from the current gap list. */
export function ReviewDecisionChart({ gaps }: { gaps: Gap[] }) {
  const theme = useChartTheme()
  const data = [
    { name: 'Keep', value: gaps.filter((gap) => gap.decision === 'accepted').length, color: theme.status.good },
    { name: 'Drop', value: gaps.filter((gap) => gap.decision === 'rejected').length, color: theme.status.critical },
    { name: 'To triage', value: gaps.filter((gap) => gap.decision === 'pending').length, color: theme.status.warning },
  ].filter((row) => row.value > 0)

  return (
    <ChartFrame
      title="Decision map"
      description="How your review is shaping the strategy brief."
      series={data.map(({ name, color }) => ({ label: name, color }))}
      table={{ columns: ['Decision', 'Gaps'], rows: data.map((row) => [row.name, row.value]) }}
      height={220}
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip content={<ChartTooltip />} />
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius="52%" outerRadius="78%" paddingAngle={3} stroke={theme.surface} strokeWidth={2}>
            {data.map((row) => <Cell key={row.name} fill={row.color} />)}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
