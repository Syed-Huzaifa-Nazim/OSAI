import { RadialBar, RadialBarChart, ResponsiveContainer } from 'recharts'
import type { PipelineState } from '@/types/pipeline'
import { ChartFrame } from './chart-frame'
import { useChartTheme } from './chart-theme'

/** Compact completion gauge for the nine-stage run. */
export function PipelineProgressChart({ pipeline }: { pipeline: PipelineState }) {
  const theme = useChartTheme()
  const complete = Object.values(pipeline.stages).filter((stage) => stage.status === 'complete' || stage.status === 'skipped').length
  const percent = Math.round((complete / 9) * 100)
  const data = [{ name: 'Complete', value: percent, fill: theme.categorical[1] }]

  return (
    <ChartFrame
      title="Pipeline completion"
      description={`${complete} of 9 stages are complete.`}
      table={{ columns: ['Complete stages', 'Progress'], rows: [[`${complete} of 9`, `${percent}%`]] }}
      height={220}
    >
      <div className="relative h-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart cx="50%" cy="50%" innerRadius="68%" outerRadius="94%" startAngle={90} endAngle={-270} data={data}>
            <RadialBar background={{ fill: theme.grid }} dataKey="value" cornerRadius={8} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-3xl font-semibold tabular-nums">{percent}%</span>
          <span className="mt-1 text-xs text-muted-foreground">complete</span>
        </div>
      </div>
    </ChartFrame>
  )
}
