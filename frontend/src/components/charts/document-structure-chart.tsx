import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DocumentSection } from '@/types/domain'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/** Section-level word distribution for the generated strategy document. */
export function DocumentStructureChart({ sections }: { sections: DocumentSection[] }) {
  const theme = useChartTheme()
  const data = sections
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((section) => ({ section: String(section.order).padStart(2, '0'), heading: section.heading, words: section.body.trim().split(/\s+/).filter(Boolean).length }))

  return (
    <ChartFrame
      title="Document structure"
      description="How the generated strategy is distributed across its sections."
      table={{ columns: ['Section', 'Words'], rows: data.map((row) => [row.heading, row.words]) }}
      height={240}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid vertical={false} stroke={theme.grid} />
          <XAxis dataKey="section" tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: theme.axis }} />
          <YAxis allowDecimals={false} tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} width={36} />
          <Tooltip content={<ChartTooltip format={(value) => `${value} words`} />} />
          <Bar dataKey="words" name="Words" fill={theme.categorical[1]} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
