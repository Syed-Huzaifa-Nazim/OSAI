import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Project } from '@/types/domain'
import { PIPELINE_STAGES } from '@/lib/pipeline-stages'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { sequentialStep, useChartTheme } from './chart-theme'

/**
 * How far each project has travelled through the pipeline. Stage is ordinal,
 * so it takes the single-hue ramp rather than nine identity colours.
 */
export function ProjectStageChart({ projects }: { projects: Project[] }) {
  const theme = useChartTheme()

  const data = PIPELINE_STAGES.map((stage, index) => ({
    stage: `${stage.id}`,
    label: stage.title,
    count: projects.filter((project) => project.currentStage === stage.id).length,
    color: sequentialStep(theme, index, PIPELINE_STAGES.length),
  }))

  return (
    <ChartFrame
      title="Projects by pipeline stage"
      description="Where your analyses are currently parked."
      table={{
        columns: ['Stage', 'Name', 'Projects'],
        rows: data.map((row) => [row.stage, row.label, row.count]),
      }}
      height={220}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 8, bottom: 4, left: 4 }} barGap={2}>
          <CartesianGrid vertical={false} stroke={theme.grid} />
          <XAxis
            dataKey="stage"
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
          <Tooltip
            cursor={{ fill: theme.grid }}
            content={<ChartTooltip />}
            labelFormatter={(value) => {
              const match = data.find((row) => row.stage === String(value))
              return match ? `Stage ${match.stage}: ${match.label}` : String(value)
            }}
          />
          <Bar dataKey="count" name="Projects" radius={[4, 4, 0, 0]} barSize={22}>
            {data.map((row) => (
              <Cell key={row.stage} fill={row.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
