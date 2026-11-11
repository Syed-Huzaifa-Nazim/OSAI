import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Lightbulb, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PageHeader } from '@/components/shared/page-header'
import { GapCard } from '@/components/shared/gap-card'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { GapCategoryChart } from '@/components/charts/gap-category-chart'
import { GapPriorityChart } from '@/components/charts/gap-priority-chart'
import { GapConfidenceChart } from '@/components/charts/gap-confidence-chart'
import { useGaps } from '@/hooks/use-insights'
import { usePipeline } from '@/hooks/use-pipeline'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { titleCase } from '@/lib/utils'
import { staggerContainer } from '@/lib/motion'
import type { GapCategory, GapPriority } from '@/types/domain'

type SortKey = 'priority' | 'confidence' | 'category'

const PRIORITY_RANK: Record<GapPriority, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

/** Stage 4 output: read-only view of everything the Insight Agent found. */
export default function InsightsPage() {
  const projectId = useProjectId()
  const project = useProject(projectId)
  const pipeline = usePipeline(projectId)
  const { data: gaps, isLoading, isError, error, refetch } = useGaps(projectId)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<GapCategory | 'all'>('all')
  const [sort, setSort] = useState<SortKey>('priority')

  useDocumentTitle(project.data ? `${project.data.brandName} · Insights` : 'Insights')

  const categories = useMemo(
    () => [...new Set((gaps ?? []).map((gap) => gap.category))],
    [gaps],
  )

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase()
    const filtered = (gaps ?? []).filter((gap) => {
      if (category !== 'all' && gap.category !== category) return false
      if (!term) return true
      return (
        gap.title.toLowerCase().includes(term) || gap.description.toLowerCase().includes(term)
      )
    })

    return filtered.sort((a, b) => {
      if (sort === 'confidence') return b.confidence - a.confidence
      if (sort === 'category') return a.category.localeCompare(b.category)
      return (
        PRIORITY_RANK[a.userPriority ?? a.priority] - PRIORITY_RANK[b.userPriority ?? b.priority]
      )
    })
  }, [gaps, query, category, sort])

  const stageComplete = pipeline.data?.stages[4].status === 'complete'

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Stage 4 · Insight Agent"
        title="Gaps and opportunities"
        description="What the analysis found between your brand and the competitors you named. Every claim carries the passage it came from."
        actions={
          pipeline.data?.blockedOn === 5 ? (
            <Button asChild>
              <Link to={`/app/projects/${projectId}/review-gaps`}>
                Review these gaps
                <ArrowRight />
              </Link>
            </Button>
          ) : undefined
        }
      />

      {isError ? (
        <ErrorState
          message={errorMessage(error)}
          onRetry={() => {
            void refetch()
          }}
        />
      ) : isLoading ? (
        <LoadingState rows={4} />
      ) : (gaps ?? []).length === 0 ? (
        <EmptyState
          title={stageComplete ? 'No gaps were identified' : 'The Insight Agent has not run yet'}
          description={
            stageComplete
              ? 'The analysis completed without finding a gap it could support with evidence. That is a real result. It usually means the competitor set was too similar to your brand to be informative.'
              : 'Start the pipeline and let the Scout and Insight agents work through your competitor set. Findings appear here as soon as stage 4 completes.'
          }
          icon={<Lightbulb className="size-5" />}
          action={
            <Button asChild variant="outline">
              <Link to={`/app/projects/${projectId}/pipeline`}>Go to the pipeline</Link>
            </Button>
          }
        />
      ) : (
        <>
          <div className="grid gap-5 xl:grid-cols-3">
            <GapCategoryChart gaps={gaps ?? []} />
            <GapPriorityChart gaps={gaps ?? []} />
            <GapConfidenceChart gaps={gaps ?? []} />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-[200px] flex-1 sm:max-w-xs">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value)
                }}
                placeholder="Search gaps"
                className="pl-9"
                aria-label="Search gaps"
              />
            </div>

            <Select
              value={category}
              onValueChange={(value) => {
                setCategory(value as GapCategory | 'all')
              }}
            >
              <SelectTrigger className="w-[170px]" aria-label="Filter by category">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {categories.map((value) => (
                  <SelectItem key={value} value={value}>
                    {titleCase(value)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={sort}
              onValueChange={(value) => {
                setSort(value as SortKey)
              }}
            >
              <SelectTrigger className="w-[170px]" aria-label="Sort gaps">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="priority">Sort by priority</SelectItem>
                <SelectItem value="confidence">Sort by confidence</SelectItem>
                <SelectItem value="category">Sort by category</SelectItem>
              </SelectContent>
            </Select>

            <p className="ml-auto text-sm text-muted-foreground">
              {visible.length} of {gaps?.length} gaps
            </p>
          </div>

          {visible.length === 0 ? (
            <EmptyState
              title="Nothing matches those filters"
              description="Try a broader category or clear the search term."
              action={
                <Button
                  variant="outline"
                  onClick={() => {
                    setQuery('')
                    setCategory('all')
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            <motion.div
              variants={staggerContainer}
              initial="initial"
              animate="animate"
              className="space-y-4"
            >
              {visible.map((gap) => (
                <GapCard key={gap.id} gap={gap} />
              ))}
            </motion.div>
          )}
        </>
      )}
    </div>
  )
}
