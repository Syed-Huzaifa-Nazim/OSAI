import { useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useIsMutating, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { RotateCcw, ScanSearch } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { FormField } from '@/components/ui/form-field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PageHeader } from '@/components/shared/page-header'
import { ProjectStatusBadge } from '@/components/shared/project-status-badge'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { ScrapeLoader } from '@/components/shared/scrape-loader'
import { ParameterGrid } from '@/components/comparison/parameter-grid'
import { ParameterResults } from '@/components/comparison/parameter-results'
import { ProductSummaryCard } from '@/components/comparison/product-summary-card'
import { ComparisonBalanceChart } from '@/components/charts/comparison-balance-chart'
import { usePipeline } from '@/hooks/use-pipeline'
import {
  useEcommerceComparison,
  useEcommerceProducts,
  useParameterComparison,
  usePlatforms,
  START_SCRAPE_KEY,
  useStartScrape,
} from '@/hooks/use-platforms'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { projectHomePath } from '@/lib/project-routes'
import { queryKeys } from '@/lib/query-client'
import { formatDate, titleCase } from '@/lib/utils'
import { spring } from '@/lib/motion'
import { phaseOf } from '@/lib/scrape-phase'

/**
 * Rotating progress copy, so a scrape that takes a minute does not look frozen.
 * The standalone scraper's wording, kept because it describes what actually
 * happens, in order.
 */
const SCRAPE_STEPS = [
  'Fetching both product pages…',
  'Parsing titles, pricing and specifications…',
  'Collecting reviews and policy text…',
]
const EMBED_STEP = 'Embedding the listings’ text for retrieval…'

/**
 * An e-commerce comparison: scrape both listings, then read them side by side.
 *
 * No agent runs from here. The page shows what the scraper found and the
 * rule-based comparison built from it, parameter by parameter.
 */
export default function ProjectComparisonPage() {
  const projectId = useProjectId()
  const project = useProject(projectId)
  // Stage 2 finishing and stage 3 starting are two separate saves; keep
  // polling through that gap, when neither stage is marked running.
  const pipeline = usePipeline(projectId, (state) => phaseOf(state).phase === 'embedding')
  const platforms = usePlatforms()
  const startScrape = useStartScrape()
  const client = useQueryClient()
  // The intake form starts the scrape and navigates here in the same tick, so
  // the first pipeline read can land before the start has registered. Treat an
  // in-flight start as scraping rather than flashing "not scraped yet".
  const starting = useIsMutating({ mutationKey: START_SCRAPE_KEY }) > 0

  const rawPhase = pipeline.data ? phaseOf(pipeline.data) : null
  const phase =
    rawPhase && starting && rawPhase.phase === 'idle'
      ? { phase: 'scraping' as const, error: null }
      : rawPhase
  const done = phase?.phase === 'done'

  // When a run ends, the project's status and the listings have changed.
  const settled = phase?.phase === 'done' || phase?.phase === 'failed'
  useEffect(() => {
    if (!settled) return
    void client.invalidateQueries({ queryKey: queryKeys.projects.detail(projectId) })
    void client.invalidateQueries({ queryKey: queryKeys.projects.products(projectId) })
    void client.invalidateQueries({ queryKey: ['projects', projectId, 'comparison'] })
  }, [settled, client, projectId])

  const products = useEcommerceProducts(projectId, done)
  const own = products.data?.find((product) => product.role === 'own')
  const competitors = products.data?.filter((product) => product.role === 'competitor') ?? []

  const [competitorId, setCompetitorId] = useState<string | undefined>(undefined)
  const activeCompetitor =
    competitors.find((product) => product.id === competitorId) ?? competitors[0]

  const comparison = useEcommerceComparison(projectId, activeCompetitor?.id, done && Boolean(own))
  const [selected, setSelected] = useState<string | null>(null)
  const detail = useParameterComparison(projectId, selected, activeCompetitor?.id)

  const resultsRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (detail.data && selected) {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [detail.data, selected])

  useDocumentTitle(project.data ? `${project.data.brandName} · Comparison` : 'Product comparison')

  if (project.isError || pipeline.isError) {
    return (
      <ErrorState
        message={errorMessage(project.error ?? pipeline.error)}
        onRetry={() => {
          void project.refetch()
          void pipeline.refetch()
        }}
      />
    )
  }

  if (!project.data || !pipeline.data || !phase) {
    return (
      <div className="space-y-6">
        <LoadingState rows={1} />
        <LoadingState rows={2} />
      </div>
    )
  }

  // Only e-commerce comparisons have a comparison page.
  if (project.data.comparisonType !== 'ecommerce_product') {
    return <Navigate to={projectHomePath(project.data)} replace />
  }

  const platformLabel =
    platforms.data?.find((item) => item.platform === project.data.ecommercePlatform)?.label ??
    titleCase(project.data.ecommercePlatform ?? 'marketplace')

  const rescrape = () => {
    setSelected(null)
    startScrape.mutate(projectId)
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow={`Product comparison · ${platformLabel}`}
        title={project.data.brandName}
        description={`Created ${formatDate(project.data.createdAt)}. Both listings are scraped, then compared field by field.`}
        actions={
          <div className="flex items-center gap-2">
            <ProjectStatusBadge status={project.data.status} />
            {phase.phase === 'done' || phase.phase === 'failed' ? (
              <Button variant="outline" size="sm" onClick={rescrape} loading={startScrape.isPending}>
                <RotateCcw />
                Scrape again
              </Button>
            ) : null}
          </div>
        }
      />

      {phase.phase === 'idle' ? (
        <EmptyState
          icon={<ScanSearch className="size-5" />}
          title="Not scraped yet"
          description={`Scraping reads both ${platformLabel} listings. It usually takes under a minute.`}
          action={
            <Button onClick={rescrape} loading={startScrape.isPending}>
              Start scraping
            </Button>
          }
        />
      ) : null}

      {phase.phase === 'scraping' || phase.phase === 'embedding' ? (
        <ScrapeLoader
          phase={phase.phase}
          steps={SCRAPE_STEPS}
          embedStep={EMBED_STEP}
          description="Both listings are read in parallel. If a page needs JavaScript to show its price, a headless browser pass runs automatically, which can take up to a minute. You can leave this page and come back."
        />
      ) : null}

      {phase.phase === 'failed' ? (
        <ErrorState
          title="Scraping did not finish"
          message={phase.error ?? 'The scraper stopped without saying why.'}
          onRetry={rescrape}
        />
      ) : null}

      {done ? (
        products.isError || comparison.isError ? (
          <ErrorState
            message={errorMessage(products.error ?? comparison.error)}
            onRetry={() => {
              void products.refetch()
              void comparison.refetch()
            }}
          />
        ) : !own || !activeCompetitor || !comparison.data ? (
          <LoadingState rows={3} />
        ) : (
          <>
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={spring}
              className="space-y-4"
            >
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <h2 className="font-display text-base font-semibold">Products in this comparison</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    What the scraper read from each listing.
                  </p>
                </div>
                {competitors.length > 1 ? (
                  <FormField label="Comparing against" htmlFor="competitor" className="w-72">
                    <Select
                      value={activeCompetitor.id}
                      onValueChange={(value) => {
                        setCompetitorId(value)
                      }}
                    >
                      <SelectTrigger id="competitor">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {competitors.map((product) => (
                          <SelectItem key={product.id} value={product.id}>
                            {product.productName}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                ) : null}
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <ProductSummaryCard product={own} platformLabel={platformLabel} />
                <ProductSummaryCard product={activeCompetitor} platformLabel={platformLabel} />
              </div>
            </motion.section>

            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...spring, delay: 0.05 }}
              className="space-y-4"
            >
              <div>
                <h2 className="font-display text-base font-semibold">Comparison parameters</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Pick a lens. Metadata is compared directly; text fields are retrieved from the
                  stored listings.
                </p>
              </div>
              <ParameterGrid
                groups={comparison.data}
                selected={selected}
                loadingKey={detail.isFetching ? selected : null}
                onSelect={setSelected}
              />
            </motion.section>

            <ComparisonBalanceChart groups={comparison.data} />

            <div ref={resultsRef} className="scroll-mt-20">
              {selected === null ? (
                <Card className="p-6 text-center text-sm text-muted-foreground">
                  Select a parameter above to see the side-by-side read-out.
                </Card>
              ) : detail.isError ? (
                <ErrorState
                  message={errorMessage(detail.error)}
                  onRetry={() => {
                    void detail.refetch()
                  }}
                />
              ) : !detail.data ? (
                <LoadingState rows={3} />
              ) : (
                <ParameterResults
                  result={detail.data}
                  images={{ own: own.images, competitor: activeCompetitor.images }}
                />
              )}
            </div>
          </>
        )
      ) : null}
    </div>
  )
}

