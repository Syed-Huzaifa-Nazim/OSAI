import { useEffect, useRef, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useIsMutating, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ArrowUpRight, Database, Heart, MessageCircle, Play, RotateCcw, ScanSearch, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PageHeader } from '@/components/shared/page-header'
import { AnalysisJourney } from '@/components/shared/analysis-journey'
import { EvidenceVisuals } from '@/components/shared/visual-intelligence'
import { ProjectStatusBadge } from '@/components/shared/project-status-badge'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { ScrapeLoader } from '@/components/shared/scrape-loader'
import { SafeImage } from '@/components/shared/safe-image'
import { PostDetailDialog, isVideo } from '@/components/sources/post-detail-dialog'
import { ParameterGrid } from '@/components/comparison/parameter-grid'
import { ParameterResults } from '@/components/comparison/parameter-results'
import { CollectionCoverageChart } from '@/components/charts/collection-coverage-chart'
import { usePipeline } from '@/hooks/use-pipeline'
import {
  START_SCRAPE_KEY,
  useEcommerceComparison,
  useParameterComparison,
  useSourceDocuments,
  useStartAnalysis,
  useStartScrape,
} from '@/hooks/use-platforms'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { mediaSrc } from '@/lib/media'
import { projectHomePath } from '@/lib/project-routes'
import { queryKeys } from '@/lib/query-client'
import { phaseOf } from '@/lib/scrape-phase'
import { formatDate } from '@/lib/utils'
import { spring, staggerContainer, staggerItem } from '@/lib/motion'
import type { ScrapedPage, ScrapedPost } from '@/types/domain'

/**
 * A website or social comparison: scrape both sides, then show what was read.
 *
 * The counterpart of the product comparison page, for the two comparison types
 * whose unit is a page or a post rather than a listing. No agent runs from
 * here either: the same two stages run, and the run stops.
 */

/** Rotating progress copy, so a scrape that takes a minute does not look frozen. */
const WEBSITE_STEPS = [
  'Opening both sites…',
  'Reading the important pages…',
  'Organising what we found…',
]
const SOCIAL_STEPS = [
  'Opening both profiles…',
  'Reading posts and reactions…',
  'Collecting public comments…',
]
const EMBED_STEP = 'Preparing your side-by-side comparison…'

/** How many of a site's images the card shows before the rest are left out. */
const SITE_IMAGE_COUNT = 6

export default function ProjectSourcesPage() {
  const projectId = useProjectId()
  const project = useProject(projectId)
  // Stage 2 finishing and stage 3 starting are two separate saves; keep
  // polling through that gap, when neither stage is marked running.
  const pipeline = usePipeline(projectId, (state) => phaseOf(state).phase === 'embedding')
  const startScrape = useStartScrape()
  const startAnalysis = useStartAnalysis()
  const client = useQueryClient()
  // The intake form starts the scrape and navigates here in the same tick, so
  // the first pipeline read can land before the start has registered.
  const starting = useIsMutating({ mutationKey: START_SCRAPE_KEY }) > 0

  const rawPhase = pipeline.data ? phaseOf(pipeline.data) : null
  const phase =
    rawPhase && starting && rawPhase.phase === 'idle'
      ? { phase: 'scraping' as const, error: null }
      : rawPhase
  const done = phase?.phase === 'done'

  // When a run ends, the project's status and what it collected have changed.
  const settled = phase?.phase === 'done' || phase?.phase === 'failed'
  useEffect(() => {
    if (!settled) return
    void client.invalidateQueries({ queryKey: queryKeys.projects.detail(projectId) })
    void client.invalidateQueries({ queryKey: queryKeys.projects.documents(projectId) })
  }, [settled, client, projectId])

  const documents = useSourceDocuments(projectId, done)
  // The same endpoints the product comparison reads: a website is scored
  // against its competitor exactly the way a listing is.
  const comparison = useEcommerceComparison(projectId, undefined, done)
  const [selected, setSelected] = useState<string | null>(null)
  const detail = useParameterComparison(projectId, selected, undefined)

  const resultsRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (detail.data && selected) {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [detail.data, selected])

  useDocumentTitle(project.data ? `${project.data.brandName} · Evidence` : 'Evidence')

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

  // A product comparison has its own page, and the demo project its pipeline.
  if (project.data.comparisonType === 'ecommerce_product' || project.data.isDemo) {
    return <Navigate to={projectHomePath(project.data)} replace />
  }

  const isSocial = project.data.comparisonType === 'social_media'
  // Gap analysis (stage 4): Instagram only, once both profiles are scraped.
  const canAnalyse = isSocial && project.data.socialPlatform === 'instagram' && phase.phase === 'done'
  const analysis = pipeline.data.stages[4] ?? null
  const analysing = analysis?.status === 'running' || startAnalysis.isPending
  const analysed = analysis?.status === 'complete'
  const reviewGapsPath = `/app/projects/${projectId}/review-gaps`
  const subject = isSocial ? 'Instagram' : 'Website'
  const rescrape = () => {
    startScrape.mutate(projectId)
  }

  const pages = documents.data?.pages ?? []
  const posts = documents.data?.posts ?? []
  const collected = isSocial ? posts.length : pages.length
  const groups = comparison.data ?? []
  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow={`Evidence · ${subject}`}
        title="Evidence"
        description={`${project.data.brandName} · Created ${formatDate(project.data.createdAt)}. ${analysed ? 'Your evidence is ready to support findings.' : 'Review what we collected, then find the opportunities worth acting on.'}`}
        actions={
          <div className="flex items-center gap-2">
            <ProjectStatusBadge status={project.data.status} />
            {phase.phase === 'done' || phase.phase === 'failed' ? (
              <Button variant="outline" size="sm" onClick={rescrape} loading={startScrape.isPending}>
                <RotateCcw />
                Refresh evidence
              </Button>
            ) : null}
            {canAnalyse && analysed && !analysing ? (
              <Button asChild size="sm">
                <Link to={reviewGapsPath}>
                  <Sparkles />
                  Review opportunities
                </Link>
              </Button>
            ) : null}
            {canAnalyse ? (
              <Button
                size="sm"
                variant={analysed ? 'outline' : 'default'}
                onClick={() => startAnalysis.mutate(projectId)}
                loading={analysing}
                disabled={analysing}
              >
                <Sparkles />
                {analysing ? 'Finding opportunities…' : analysed ? 'Look again' : 'Find opportunities'}
              </Button>
            ) : null}
          </div>
        }
      />

      {phase.phase === 'idle' ? (
        <EmptyState
          icon={<ScanSearch className="size-5" />}
          title="Ready to read both sides"
          description={
            isSocial
              ? 'We will read the recent public posts on both profiles. It usually takes a minute or two.'
              : 'We will read both sites and the important pages inside them. It usually takes a minute or two.'
          }
          action={
            <Button onClick={rescrape} loading={startScrape.isPending}>
              Start reading
            </Button>
          }
        />
      ) : null}

      {phase.phase === 'scraping' || phase.phase === 'embedding' ? (
        <ScrapeLoader
          phase={phase.phase}
          steps={isSocial ? SOCIAL_STEPS : WEBSITE_STEPS}
          embedStep={EMBED_STEP}
              description={
                isSocial
                  ? 'We are reading both profiles and their public posts. You can leave this page and come back when it is ready.'
                  : 'We are reading both sites and their important pages. You can leave this page and come back when it is ready.'
              }
        />
      ) : null}

      {phase.phase === 'failed' ? (
        <ErrorState
          title="Reading stopped before it finished"
          message={phase.error ?? 'We could not finish reading the pages. Please try again.'}
          onRetry={rescrape}
        />
      ) : null}

      {canAnalyse && analysis?.status === 'error' ? (
        <ErrorState
          title="Finding opportunities did not finish"
          message={analysis?.error ?? 'The analysis stopped without saying why.'}
          onRetry={() => startAnalysis.mutate(projectId)}
        />
      ) : null}

      {done ? (
        documents.isError ? (
          <ErrorState
            message={errorMessage(documents.error)}
            onRetry={() => {
              void documents.refetch()
            }}
          />
        ) : !documents.data ? (
          <LoadingState rows={3} />
        ) : collected === 0 ? (
          <EmptyState
            icon={<ScanSearch className="size-5" />}
            title="Nothing was collected"
            description="We could not find anything to compare. Try reading again, or check that both links are public."
            action={
              <Button onClick={rescrape} loading={startScrape.isPending}>
                Try again
              </Button>
            }
          />
        ) : (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="space-y-4"
          >
            <AnalysisJourney active={2} compact />
            <EvidenceSummary
              isSocial={isSocial}
              ownCount={isSocial ? posts.filter((post) => post.role === 'own').length : pages.filter((page) => page.role === 'own').length}
              competitorCount={isSocial ? posts.filter((post) => post.role === 'competitor').length : pages.filter((page) => page.role === 'competitor').length}
              visualCount={isSocial ? posts.filter((post) => Boolean(post.mediaUrl || post.media?.length)).length : pages.flatMap((page) => page.images ?? []).length}
            />
            <EvidenceVisuals documents={documents.data} />
            {canAnalyse && !analysed ? (
              <Card className="flex flex-wrap items-center justify-between gap-4 border-primary/25 bg-primary/5 p-5">
                <div>
                  <p className="text-sm font-semibold">Ready for the useful part?</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    We have read both profiles. Now let OptiStratixAI point out the biggest opportunities.
                  </p>
                </div>
                <Button onClick={() => startAnalysis.mutate(projectId)} loading={analysing}>
                  <Sparkles />
                  Find opportunities
                </Button>
              </Card>
            ) : null}
            <div>
              <h2 className="font-display text-base font-semibold">Source library</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {isSocial
                  ? 'Every public post we read, with its reactions and comments.'
                  : 'Every page we read, with its headings, links and useful text.'}
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {(['own', 'competitor'] as const).map((role) =>
                isSocial ? (
                  <ProfileCard
                    key={role}
                    role={role}
                    posts={posts.filter((post) => post.role === role)}
                  />
                ) : (
                  <SiteCard
                    key={role}
                    role={role}
                    pages={pages.filter((page) => page.role === role)}
                  />
                ),
              )}
            </div>
            <CollectionCoverageChart documents={documents.data} />
          </motion.section>
        )
      ) : null}

      {done && groups.length > 0 ? (
        <>
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...spring, delay: 0.05 }}
            className="space-y-4"
          >
            <div>
                <h2 className="font-display text-base font-semibold">Compare the details</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Choose a detail to see how your side compares with the competitor.
              </p>
            </div>
            <ParameterGrid
              groups={groups}
              selected={selected}
              loadingKey={detail.isFetching ? selected : null}
              onSelect={setSelected}
            />
          </motion.section>

          <div ref={resultsRef} className="scroll-mt-20">
            {selected === null ? (
              <Card className="p-6 text-center text-sm text-muted-foreground">
                Choose a detail above to see the side-by-side comparison.
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
              <ParameterResults result={detail.data} />
            )}
          </div>
        </>
      ) : null}
    </div>
  )
}

function EvidenceSummary({
  isSocial,
  ownCount,
  competitorCount,
  visualCount,
}: {
  isSocial: boolean
  ownCount: number
  competitorCount: number
  visualCount: number
}) {
  return (
    <Card className="border-primary/20 bg-primary/5 p-5">
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Database className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-base font-semibold">Evidence coverage</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            This is the material behind the comparison. Check both sides before deciding what matters.
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label={isSocial ? 'Your posts' : 'Your pages'} value={ownCount.toLocaleString()} />
            <Stat label={isSocial ? 'Competitor posts' : 'Competitor pages'} value={competitorCount.toLocaleString()} />
            <Stat label={isSocial ? 'Posts with media' : 'Images found'} value={visualCount.toLocaleString()} />
            <Stat label="Source status" value="Collected" />
          </dl>
        </div>
      </div>
    </Card>
  )
}

/* ------------------------------------------------------------- website --- */

function SiteCard({ role, pages }: { role: 'own' | 'competitor'; pages: ScrapedPage[] }) {
  const isOwn = role === 'own'
  const submitted = pages[0]?.submittedUrl ?? ''
  const total = (pick: (page: ScrapedPage) => number) =>
    pages.reduce((sum, page) => sum + pick(page), 0)
  // Already ordered page by page, best image of each first, so the opening
  // few are the ones the site chose to lead with.
  // `?? []` is not defensive noise: an API that predates page images omits the
  // field, and flatMap would then fold `undefined` in as an element.
  const siteImages = pages.flatMap((page) => page.images ?? []).slice(0, SITE_IMAGE_COUNT)

  return (
    <Card className="flex h-full flex-col p-5">
      <div className="flex items-center justify-between gap-3">
        <Badge variant={isOwn ? 'default' : 'secondary'}>{isOwn ? 'Your site' : 'Competitor'}</Badge>
        {submitted ? (
          <a
            href={submitted}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary"
          >
            Open site
            <ArrowUpRight className="size-3" />
          </a>
        ) : null}
      </div>

      <h3 className="mt-3 truncate font-display text-base font-semibold" title={submitted}>
        {hostOf(submitted)}
      </h3>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
        <Stat label="Pages read" value={pages.length.toLocaleString()} />
        <Stat label="Words" value={total((page) => page.wordCount).toLocaleString()} />
        <Stat label="Headings" value={total((page) => page.headingCount).toLocaleString()} />
        <Stat label="Links found" value={total((page) => page.linkCount).toLocaleString()} />
      </dl>

      {/* What the site shows, not only what it says. Same handling as a
          listing's photos: the site's own URL, nothing re-hosted. */}
      {siteImages.length > 0 ? (
        <ul className="mt-4 grid grid-cols-3 gap-2 border-t border-border/15 pt-4">
          {siteImages.map((image) => (
            <li key={image.id}>
              <a
                href={image.imageUrl}
                target="_blank"
                rel="noreferrer"
                className="block rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={image.altText ?? `Open image ${image.position}`}
              >
                <SafeImage
                  src={image.imageUrl}
                  alt={image.altText ?? ''}
                  className="aspect-video w-full"
                  fit="cover"
                />
              </a>
            </li>
          ))}
        </ul>
      ) : null}

      {pages.length === 0 ? (
        <p className="mt-4 border-t border-border/15 pt-4 text-sm text-muted-foreground">
          Nothing could be read from this site.
        </p>
      ) : (
        <ul className="mt-4 space-y-2 border-t border-border/15 pt-4">
          {pages.map((page) => (
            <li key={page.id} className="rounded-md border border-border/15 bg-card p-3">
              <div className="flex items-start justify-between gap-2">
                <a
                  href={page.pageUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="line-clamp-1 text-sm font-medium transition-colors hover:text-primary"
                  title={page.title ?? page.pageUrl}
                >
                  {page.title || page.pageUrl}
                </a>
                <Badge variant={page.isRoot ? 'outline' : 'muted'}>
                  {page.isRoot ? 'Entry page' : `${page.depth} click${page.depth === 1 ? '' : 's'} in`}
                </Badge>
              </div>
              <p className="mt-1 truncate text-xs text-muted-foreground" title={page.pageUrl}>
                {page.pageUrl}
              </p>
              {page.textPreview ? (
                <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{page.textPreview}</p>
              ) : null}
              <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                <span>{plural(page.wordCount, 'word')}</span>
                <span aria-hidden="true">·</span>
                <span>{plural(page.headingCount, 'heading')}</span>
                <span aria-hidden="true">·</span>
                <span>{plural(page.linkCount, 'link')}</span>
                <span aria-hidden="true">·</span>
                <span className="font-mono">{page.renderer}</span>
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

/* ----------------------------------------------------------- instagram --- */

function ProfileCard({ role, posts }: { role: 'own' | 'competitor'; posts: ScrapedPost[] }) {
  const isOwn = role === 'own'
  const [opened, setOpened] = useState<ScrapedPost | null>(null)
  const submitted = posts[0]?.submittedUrl ?? ''
  // The profile's own handle. Never a post's ownerUsername: on a collaboration
  // post that is the other account, which is how this card once labelled a
  // profile with a stranger's name.
  const username = posts[0]?.profileUsername ?? usernameFromUrl(submitted)
  const total = (pick: (post: ScrapedPost) => number | null) =>
    posts.reduce((sum, post) => sum + (pick(post) ?? 0), 0)

  return (
    <Card className="flex h-full flex-col p-5">
      <div className="flex items-center justify-between gap-3">
        <Badge variant={isOwn ? 'default' : 'secondary'}>
          {isOwn ? 'Your profile' : 'Competitor'}
        </Badge>
        {submitted ? (
          <a
            href={submitted}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary"
          >
            Open profile
            <ArrowUpRight className="size-3" />
          </a>
        ) : null}
      </div>

      <h3 className="mt-3 truncate font-display text-base font-semibold" title={submitted}>
        {username ? `@${username}` : hostOf(submitted)}
      </h3>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
        <Stat label="Posts read" value={posts.length.toLocaleString()} />
        <Stat label="Likes" value={total((post) => post.likeCount).toLocaleString()} />
        <Stat label="Comments" value={total((post) => post.commentCount).toLocaleString()} />
        <Stat label="Hashtags" value={total((post) => post.hashtagCount).toLocaleString()} />
      </dl>

      {posts.length === 0 ? (
        <p className="mt-4 border-t border-border/15 pt-4 text-sm text-muted-foreground">
          No public posts could be read for this profile.
        </p>
      ) : (
        <>
          <motion.ul
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="mt-4 grid grid-cols-3 gap-2 border-t border-border/15 pt-4"
          >
            {posts.map((post) => (
              <motion.li key={post.id} variants={staggerItem}>
                <PostTile
                  post={post}
                  onOpen={() => {
                    setOpened(post)
                  }}
                />
              </motion.li>
            ))}
          </motion.ul>
          <p className="mt-3 text-xs text-muted-foreground">
            Open a post to read its caption, hashtags and the comments collected for it.
          </p>
        </>
      )}

      <PostDetailDialog
        post={opened}
        username={username}
        open={opened !== null}
        onOpenChange={(next) => {
          if (!next) setOpened(null)
        }}
      />
    </Card>
  )
}

/**
 * One post in the profile grid: its picture, with the engagement that matters
 * revealed over it. The whole tile is the button, so the target is the image
 * rather than a link buried in a row of text.
 */
function PostTile({ post, onOpen }: { post: ScrapedPost; onOpen: () => void }) {
  const first = post.media?.[0]
  const thumbnail = first?.mediaUrl ?? post.mediaUrl
  const video = thumbnail ? isVideo(thumbnail, first?.mediaType ?? post.mediaType) : false

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group relative block w-full overflow-hidden rounded-md border border-border/15 transition-colors hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={`Open post from ${post.postedAt ? formatDate(post.postedAt) : 'this profile'}`}
    >
      {thumbnail && !video ? (
        <SafeImage
          src={mediaSrc(thumbnail)}
          alt=""
          className="aspect-square w-full border-0"
          fit="cover"
        />
      ) : (
        <span className="flex aspect-square w-full items-center justify-center bg-muted/30 text-muted-foreground">
          {video ? (
            <Play className="size-5" aria-hidden="true" />
          ) : (
            <span className="px-2 text-center text-[0.65rem] leading-tight">No image</span>
          )}
        </span>
      )}

      {/* Counts sit over the picture, which is where a social grid reads them. */}
      <span className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center gap-2 bg-gradient-to-t from-brand-ink-black/85 to-transparent px-2 pb-1.5 pt-5 text-[0.7rem] font-medium text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
        <span className="flex items-center gap-1">
          <Heart className="size-3" aria-hidden="true" />
          {(post.likeCount ?? 0).toLocaleString()}
        </span>
        <span className="flex items-center gap-1">
          <MessageCircle className="size-3" aria-hidden="true" />
          {(post.commentCount ?? 0).toLocaleString()}
        </span>
      </span>

      {post.mediaCount > 1 ? (
        <span className="absolute right-1.5 top-1.5 rounded bg-brand-ink-black/70 px-1.5 py-0.5 text-[0.65rem] font-medium text-white">
          {post.mediaCount}
        </span>
      ) : null}
    </button>
  )
}

/* --------------------------------------------------------------- shared --- */

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="truncate text-sm font-medium tabular-nums" title={value}>
        {value}
      </dd>
    </div>
  )
}

/** "1 heading", "54 headings". */
function plural(count: number, noun: string): string {
  return `${count.toLocaleString()} ${noun}${count === 1 ? '' : 's'}`
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url || 'Not scraped'
  }
}

/** The handle in a profile link, for rows scraped before it was stored. */
function usernameFromUrl(url: string): string {
  try {
    return new URL(url).pathname.split('/').filter(Boolean)[0] ?? ''
  } catch {
    return ''
  }
}
