import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ScrapedDocuments } from '@/types/domain'
import { ChartFrame } from './chart-frame'
import { ChartTooltip } from './chart-tooltip'
import { useChartTheme } from './chart-theme'

/** Coverage map for a website crawl or social-profile collection. */
export function CollectionCoverageChart({ documents }: { documents: ScrapedDocuments }) {
  const theme = useChartTheme()
  const social = documents.kind === 'instagram'
  const own = social ? documents.posts.filter((item) => item.role === 'own') : documents.pages.filter((item) => item.role === 'own')
  const competitor = social ? documents.posts.filter((item) => item.role === 'competitor') : documents.pages.filter((item) => item.role === 'competitor')
  const media = social
    ? (items: typeof documents.posts) => items.reduce((sum, item) => sum + item.mediaCount, 0)
    : (items: typeof documents.pages) => items.reduce((sum, item) => sum + (item.images?.length ?? 0), 0)
  const data = [
    { label: social ? 'Posts' : 'Pages', yours: own.length, competitor: competitor.length },
    { label: social ? 'Media' : 'Images', yours: media(own as never), competitor: media(competitor as never) },
  ]

  return (
    <ChartFrame
      title="Collection coverage"
      description={social ? 'Public posts and media collected from each profile.' : 'Pages and representative images collected from each site.'}
      series={[{ label: 'Your brand', color: theme.categorical[1] }, { label: 'Competitor', color: theme.categorical[0] }]}
      table={{ columns: ['Collected', 'Your brand', 'Competitor'], rows: data.map((row) => [row.label, row.yours, row.competitor]) }}
      height={220}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid vertical={false} stroke={theme.grid} />
          <XAxis dataKey="label" tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: theme.axis }} />
          <YAxis allowDecimals={false} tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} width={28} />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey="yours" name="Your brand" fill={theme.categorical[1]} radius={[4, 4, 0, 0]} />
          <Bar dataKey="competitor" name="Competitor" fill={theme.categorical[0]} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  )
}
