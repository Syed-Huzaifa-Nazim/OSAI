import { useEffect, useRef, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useIsMutating, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { RotateCcw, ScanSearch, Sparkles } from 'lucide-react'
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
import { FindGapsDialog } from '@/components/shared/find-gaps-dialog'
import { PageHeader } from '@/components/shared/page-header'
import { ProjectStatusBadge } from '@/components/shared/project-status-badge'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { ScrapeLoader } from '@/components/shared/scrape-loader'
import { ParameterGrid } from '@/components/comparison/parameter-grid'
import { ParameterResults } from '@/components/comparison/parameter-results'
import { ProductSummaryCard } from '@/components/comparison/product-summary-card'
import { DarazListingCard } from '@/components/comparison/daraz-listing-card'
import { usePipeline } from '@/hooks/use-pipeline'
import {
  useEcommerceComparison,
  useEcommerceProducts,
  useParameterComparison,
  usePlatforms,
  START_SCRAPE_KEY,
  useCancelJob,
  useStartAnalysis,
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
  const startAnalysis = useStartAnalysis()
  // Cancel: stops the scrape or the analysis; nothing from that run is saved.
  const cancelJob = useCancelJob()
  // The Find gaps dialog (Daraz): open while the analysis runs, then a green check and the way to the gaps.
  const [gapsDialog, setGapsDialog] = useState(false)
  const stage4Running = pipeline.data?.stages[4]?.status === 'running'
  // Only a run seen running counts as finished, so an earlier result never flashes the check mark.
  const sawRunning = useRef(false)
  useEffect(() => {
    if (stage4Running) {
      sawRunning.current = true
      setGapsDialog(true)
    }
  }, [stage4Running])
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

  // Gap analysis (stage 4): Daraz listings only, once both are scraped.
  const isDaraz = project.data.ecommercePlatform === 'daraz'
  const canAnalyse = isDaraz && done
  const analysis = pipeline.data.stages[4] ?? null
  const analysing = analysis?.status === 'running' || startAnalysis.isPending
  const analysed = analysis?.status === 'complete'
  const reviewGapsPath = `/app/projects/${projectId}/review-gaps`

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow={`Product comparison · ${platformLabel}`}
        title={project.data.brandName}
        description={`Created ${formatDate(project.data.createdAt)}. ${
          analysed
            ? 'Both listings are read and analysed; the gaps are ready to review.'
            : isDaraz
              ? 'Both listings are read from Daraz. Find gaps then shows what to change.'
              : 'Both listings are scraped, then compared field by field.'
        }`}
        actions={
          <div className="flex items-center gap-2">
            <ProjectStatusBadge status={project.data.status} />
            {phase.phase === 'done' || phase.phase === 'failed' ? (
              <Button variant="outline" size="sm" onClick={rescrape} loading={startScrape.isPending}>
                <RotateCcw />
                Scrape again
              </Button>
            ) : null}
            {canAnalyse && analysed && !analysing ? (
              <Button asChild size="sm">
                <Link to={reviewGapsPath}>
                  <Sparkles />
                  Review gaps
                </Link>
              </Button>
            ) : null}
            {canAnalyse ? (
              <Button
                size="sm"
                variant={analysed ? 'outline' : 'default'}
                onClick={() => {
                  sawRunning.current = false
                  setGapsDialog(true)
                  startAnalysis.mutate(projectId)
                }}
                loading={analysing}
                disabled={analysing}
              >
                <Sparkles />
                {analysing ? 'Finding gaps…' : analysed ? 'Analyse again' : 'Find gaps'}
              </Button>
            ) : null}
          </div>
        }
      />

      {canAnalyse ? (
        <FindGapsDialog
          kind="daraz"
          open={gapsDialog}
          onOpenChange={setGapsDialog}
          state={
            startAnalysis.isError || analysis?.status === 'error'
              ? 'failed'
              : analysed && !analysing && sawRunning.current
                ? 'done'
                : 'running'
          }
          message={analysis?.message}
          error={startAnalysis.isError ? errorMessage(startAnalysis.error) : analysis?.error}
          reviewPath={reviewGapsPath}
          onCancel={() => {
            cancelJob.mutate(projectId, {
              onSuccess: () => {
                sawRunning.current = false
                setGapsDialog(false)
              },
            })
          }}
          cancelling={cancelJob.isPending}
        />
      ) : null}

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
          onCancel={() => {
            cancelJob.mutate(projectId)
          }}
          cancelling={cancelJob.isPending}
        />
      ) : null}

      {phase.phase === 'failed' ? (
        <ErrorState
          title="Scraping did not finish"
          message={phase.error ?? 'The scraper stopped without saying why.'}
          onRetry={rescrape}
        />
      ) : null}

      {done && isDaraz ? (
        products.isError ? (
          <ErrorState
            message={errorMessage(products.error)}
            onRetry={() => {
              void products.refetch()
            }}
          />
        ) : !own ? (
          <LoadingState rows={3} />
        ) : (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="space-y-4"
          >
            <div>
              <h2 className="font-display text-base font-semibold">What was read</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Both listings as Daraz shows them today.
              </p>
            </div>
            <div className="relative grid gap-4 md:grid-cols-2 md:gap-8">
              <span
                className="absolute left-1/2 top-1/2 z-10 hidden size-14 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-card font-display text-base font-extrabold text-primary shadow-lg ring-[6px] ring-primary/10 md:flex"
                aria-hidden="true"
              >
                VS
              </span>
              <DarazListingCard product={own} />
              {competitors.map((product) => (
                <DarazListingCard key={product.id} product={product} />
              ))}
            </div>
            {!analysed && !analysing ? (
              <Card className="flex flex-col items-start gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-semibold">Next: find what to change</p>
                  <p className="text-sm text-muted-foreground">
                    Find gaps compares both listings with the top Daraz listings for the same search
                    and reads their reviews. It takes 1 to 3 minutes.
                  </p>
                </div>
                <Button
                  onClick={() => {
                    sawRunning.current = false
                    setGapsDialog(true)
                    startAnalysis.mutate(projectId)
                  }}
                >
                  <Sparkles />
                  Find gaps
                </Button>
              </Card>
            ) : null}
          </motion.section>
        )
      ) : null}

      {done && !isDaraz ? (
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

