import { motion } from 'framer-motion'
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BarChart3, Eye, Sparkles } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { ChartFrame } from '@/components/charts/chart-frame'
import { ChartTooltip } from '@/components/charts/chart-tooltip'
import { useChartTheme } from '@/components/charts/chart-theme'
import { formatCompactNumber } from '@/lib/utils'
import type { Project, ScrapedDocuments, ScrapedPage, ScrapedPost } from '@/types/domain'

interface EvidenceVisualsProps {
  documents: ScrapedDocuments
}

/**
 * A compact, evidence-only alternative to a marketing analytics dashboard.
 * Every mark comes from collected posts/pages; no spend, traffic, or growth
 * estimate is invented just to make the screen look busy.
 */
export function EvidenceVisuals({ documents }: EvidenceVisualsProps) {
  const theme = useChartTheme()
  const social = documents.kind === 'instagram'
  const own = social ? documents.posts.filter((item) => item.role === 'own') : documents.pages.filter((item) => item.role === 'own')
  const competitor = social ? documents.posts.filter((item) => item.role === 'competitor') : documents.pages.filter((item) => item.role === 'competitor')
  const ownVisuals = social ? visualPosts(own as ScrapedPost[]) : imageCount(own as ScrapedPage[])
  const competitorVisuals = social ? visualPosts(competitor as ScrapedPost[]) : imageCount(competitor as ScrapedPage[])
  const ownSignals = social ? reactions(own as ScrapedPost[]) : links(own as ScrapedPage[])
  const competitorSignals = social ? reactions(competitor as ScrapedPost[]) : links(competitor as ScrapedPage[])
  const ownSeries = social ? postSeries(own as ScrapedPost[]) : pageSeries(own as ScrapedPage[])
  const competitorSeries = social ? postSeries(competitor as ScrapedPost[]) : pageSeries(competitor as ScrapedPage[])
  const label = social ? 'post' : 'page'
  const measure = social ? 'reactions' : 'words read'
  const trendData = pairedSeries(ownSeries, competitorSeries, label)
  const metricData = [
    { label: social ? 'Posts read' : 'Pages read', yours: own.length, competitor: competitor.length },
    { label: 'Visuals', yours: ownVisuals, competitor: competitorVisuals },
    { label: social ? 'Reactions' : 'Links', yours: ownSignals, competitor: competitorSignals },
  ]
  const share = [
    { name: 'Your side', value: own.length, color: theme.categorical[1] },
    { name: 'Their side', value: competitor.length, color: theme.categorical[0] },
  ]

  return (
    <section className="space-y-4" aria-label="Visual comparison">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Visual comparison</p>
          <h2 className="mt-1 font-display text-xl font-semibold">See both sides in a few seconds</h2>
          <p className="mt-1 text-sm text-muted-foreground">The movement is based on the posts or pages we actually read.</p>
        </div>
        <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">Live from collected evidence</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <motion.div initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.2 }} transition={{ duration: 0.4 }} className="grid gap-4 sm:grid-cols-2 lg:col-span-8">
          <EvidenceSideCard
            label="Your side"
            count={own.length}
            series={ownSeries}
            color={theme.categorical[1]}
            supporting={`${formatCompactNumber(ownSignals)} ${social ? 'reactions' : 'links found'}`}
          />
          <EvidenceSideCard
            label="Competitor side"
            count={competitor.length}
            series={competitorSeries}
            color={theme.categorical[0]}
            supporting={`${formatCompactNumber(competitorSignals)} ${social ? 'reactions' : 'links found'}`}
          />
        </motion.div>

        <ChartFrame
          className="lg:col-span-4"
          title="Reading split"
          description="How much material was collected from each side."
          series={share.map(({ name, color }) => ({ label: name, color }))}
          table={{ columns: ['Side', social ? 'Posts' : 'Pages'], rows: share.map((part) => [part.name, part.value]) }}
          height={180}
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={share} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius="55%" outerRadius="80%" paddingAngle={4} stroke={theme.surface} strokeWidth={2} isAnimationActive animationDuration={850}>
                {share.map((part) => <Cell key={part.name} fill={part.color} />)}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame
          className="lg:col-span-8"
          title={social ? 'Reaction across collected posts' : 'Useful text across collected pages'}
          description={social ? 'Each point is one public post, ordered by publish date when available.' : 'Each point is a page we read, ordered by distance from the submitted page.'}
          series={[{ label: 'Your side', color: theme.categorical[1] }, { label: 'Their side', color: theme.categorical[0] }]}
          table={{ columns: [social ? 'Post' : 'Page', 'Your side', 'Their side'], rows: trendData.map((row) => [row.label, row.yours, row.competitor]) }}
          height={235}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendData} margin={{ top: 12, right: 14, bottom: 4, left: 4 }}>
              <CartesianGrid vertical={false} stroke={theme.grid} />
              <XAxis dataKey="label" tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: theme.axis }} />
              <YAxis allowDecimals={false} tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} width={36} />
              <Tooltip content={<ChartTooltip format={(value) => `${formatCompactNumber(value)} ${measure}`} />} />
              <Line type="monotone" dataKey="yours" name="Your side" stroke={theme.categorical[1]} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} isAnimationActive animationDuration={950} />
              <Line type="monotone" dataKey="competitor" name="Their side" stroke={theme.categorical[0]} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} isAnimationActive animationDuration={1100} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame
          className="lg:col-span-4"
          title="What we found"
          description="A direct side-by-side count, without a made-up score."
          series={[{ label: 'Your side', color: theme.categorical[1] }, { label: 'Their side', color: theme.categorical[0] }]}
          table={{ columns: ['What we found', 'Your side', 'Their side'], rows: metricData.map((row) => [row.label, row.yours, row.competitor]) }}
          height={235}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={metricData} layout="vertical" margin={{ top: 5, right: 14, bottom: 2, left: 8 }} barGap={3}>
              <CartesianGrid horizontal={false} stroke={theme.grid} />
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="label" tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} width={76} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="yours" name="Your side" fill={theme.categorical[1]} radius={[0, 4, 4, 0]} animationDuration={850} />
              <Bar dataKey="competitor" name="Their side" fill={theme.categorical[0]} radius={[0, 4, 4, 0]} animationDuration={1050} />
            </BarChart>
          </ResponsiveContainer>
        </ChartFrame>
      </div>
    </section>
  )
}

function EvidenceSideCard({ label, count, series, color, supporting }: { label: string; count: number; series: number[]; color: string; supporting: string }) {
  return (
    <motion.div whileHover={{ y: -4 }} transition={{ type: 'spring', stiffness: 360, damping: 24 }}>
      <Card className="relative overflow-hidden border-border/30 bg-card p-5">
        <div className="absolute inset-x-0 top-0 h-1" style={{ background: color }} />
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium">{label}</p>
            <p className="mt-3 font-display text-3xl font-semibold tabular-nums">{count.toLocaleString()}</p>
            <p className="mt-1 text-xs text-muted-foreground">items read</p>
          </div>
          <MiniSparkline values={series} color={color} label={`${label} activity`} />
        </div>
        <div className="mt-5 flex items-center gap-2 text-xs text-muted-foreground">
          <Sparkles className="size-3.5" style={{ color }} />
          {supporting}
        </div>
      </Card>
    </motion.div>
  )
}

function MiniSparkline({ values, color, label }: { values: number[]; color: string; label: string }) {
  const points = values.length > 1 ? values : [values[0] ?? 0, values[0] ?? 0]
  const high = Math.max(...points, 1)
  const low = Math.min(...points)
  const range = Math.max(high - low, 1)
  const path = points.map((value, index) => `${index === 0 ? 'M' : 'L'} ${4 + (index / (points.length - 1)) * 104} ${40 - ((value - low) / range) * 32}`).join(' ')

  return (
    <svg viewBox="0 0 112 48" className="h-14 w-28 shrink-0" role="img" aria-label={label}>
      <motion.path d={path} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" initial={{ pathLength: 0, opacity: 0 }} whileInView={{ pathLength: 1, opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.8, ease: 'easeOut' }} />
      <motion.circle cx={108} cy={Number(path.split(' ').at(-1)) || 40} r="3" fill={color} initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ delay: 0.65, type: 'spring' }} />
    </svg>
  )
}

export function WorkspaceVisuals({ projects }: { projects: Project[] }) {
  const theme = useChartTheme()
  const statuses = [
    { name: 'Ready', value: projects.filter((project) => project.status === 'complete').length, color: theme.status.good },
    { name: 'Needs you', value: projects.filter((project) => project.status === 'awaiting_review').length, color: theme.categorical[0] },
    { name: 'In progress', value: projects.filter((project) => project.status === 'running').length, color: theme.categorical[1] },
  ].filter((item) => item.value > 0)
  const displayStatuses = statuses.length > 0 ? statuses : [{ name: 'No analyses yet', value: 1, color: theme.grid }]
  const stageData = [
    { label: 'Ready', value: projects.filter((project) => project.status === 'complete').length },
    { label: 'Needs you', value: projects.filter((project) => project.status === 'awaiting_review').length },
    { label: 'Working', value: projects.filter((project) => project.status === 'running').length },
  ]

  return (
    <section className="grid gap-4 lg:grid-cols-12" aria-label="Workspace overview">
      <Card className="relative overflow-hidden border-primary/15 bg-card p-5 lg:col-span-4">
        <div className="absolute -right-8 -top-8 size-28 rounded-full bg-primary/10 blur-2xl" />
        <p className="eyebrow">Your workspace</p>
        <h2 className="mt-1 font-display text-lg font-semibold">A clear view of what needs attention</h2>
        <div className="mt-5 grid grid-cols-3 gap-3">
          <SmallCount label="All" value={projects.length} icon={<BarChart3 className="size-3.5" />} />
          <SmallCount label="Ready" value={stageData[0]?.value ?? 0} icon={<Sparkles className="size-3.5" />} />
          <SmallCount label="Waiting" value={stageData[1]?.value ?? 0} icon={<Eye className="size-3.5" />} />
        </div>
      </Card>

      <ChartFrame
        className="lg:col-span-4"
        title="Where your analyses are"
        description="A simple picture of your workspace right now."
        series={displayStatuses.map(({ name, color }) => ({ label: name, color }))}
        table={{ columns: ['Status', 'Analyses'], rows: displayStatuses.map((item) => [item.name, item.value]) }}
        height={185}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={displayStatuses} dataKey="value" nameKey="name" innerRadius="56%" outerRadius="82%" paddingAngle={4} stroke={theme.surface} strokeWidth={2} isAnimationActive animationDuration={850}>
              {displayStatuses.map((item) => <Cell key={item.name} fill={item.color} />)}
            </Pie>
            <Tooltip content={<ChartTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </ChartFrame>

      <ChartFrame
        className="lg:col-span-4"
        title="What happens next"
        description="A small guide, not a technical status report."
        table={{ columns: ['Next step', 'Analyses'], rows: stageData.map((item) => [item.label, item.value]) }}
        height={185}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={stageData} margin={{ top: 12, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid vertical={false} stroke={theme.grid} />
            <XAxis dataKey="label" tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: theme.axis }} />
            <YAxis allowDecimals={false} tick={{ fill: theme.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} width={22} />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="value" name="Analyses" fill={theme.categorical[1]} radius={[4, 4, 0, 0]} animationDuration={900} />
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
    </section>
  )
}

function SmallCount({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <motion.div whileHover={{ y: -2 }} className="rounded-lg bg-muted/45 p-3">
      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">{icon}{label}</span>
      <p className="mt-2 font-display text-xl font-semibold tabular-nums">{value}</p>
    </motion.div>
  )
}

function reactions(posts: ScrapedPost[]) {
  return posts.reduce((sum, post) => sum + (post.likeCount ?? 0) + (post.commentCount ?? 0), 0)
}

function links(pages: ScrapedPage[]) {
  return pages.reduce((sum, page) => sum + page.linkCount, 0)
}

function visualPosts(posts: ScrapedPost[]) {
  return posts.filter((post) => Boolean(post.mediaUrl || post.media?.length)).length
}

function imageCount(pages: ScrapedPage[]) {
  return pages.reduce((sum, page) => sum + (page.images?.length ?? 0), 0)
}

function postSeries(posts: ScrapedPost[]) {
  return [...posts]
    .sort((a, b) => (a.postedAt ?? '').localeCompare(b.postedAt ?? ''))
    .slice(-6)
    .map((post) => (post.likeCount ?? 0) + (post.commentCount ?? 0))
}

function pageSeries(pages: ScrapedPage[]) {
  return [...pages]
    .sort((a, b) => a.depth - b.depth || a.pageUrl.localeCompare(b.pageUrl))
    .slice(0, 6)
    .map((page) => page.wordCount)
}

function pairedSeries(yours: number[], competitor: number[], label: string) {
  const count = Math.max(yours.length, competitor.length, 2)
  return Array.from({ length: count }, (_, index) => ({
    label: `${label[0]?.toUpperCase()}${label.slice(1)} ${index + 1}`,
    yours: yours[index] ?? 0,
    competitor: competitor[index] ?? 0,
  }))
}
