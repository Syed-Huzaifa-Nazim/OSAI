import { useEffect, useRef, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useIsMutating, useQueryClient } from '@tanstack/react-query'
import { FindGapsDialog } from '@/components/shared/find-gaps-dialog'
import { motion } from 'framer-motion'
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Heart,
  MessageCircle,
  Play,
  RotateCcw,
  ScanSearch,
  Sparkles,
  TriangleAlert,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PageHeader } from '@/components/shared/page-header'
import { ProjectStatusBadge } from '@/components/shared/project-status-badge'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { ScrapeLoader } from '@/components/shared/scrape-loader'
import { SafeImage } from '@/components/shared/safe-image'
import { PostDetailDialog, isVideo } from '@/components/sources/post-detail-dialog'
import { ParameterGrid } from '@/components/comparison/parameter-grid'
import { ParameterResults } from '@/components/comparison/parameter-results'
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
import { spring } from '@/lib/motion'
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
  'Fetching both sites…',
  'Following links within each site…',
  'Cleaning page text, headings and links…',
]
const SOCIAL_STEPS = [
  'Asking Apify for both profiles…',
  'Reading captions, hashtags and engagement…',
  'Collecting the public comments on each post…',
]
const EMBED_STEP = 'Embedding what was collected for retrieval…'

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
  // The Find gaps dialog: open while the analysis runs, then a green check and the way to the gaps.
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

  useDocumentTitle(project.data ? `${project.data.brandName} · Scraped data` : 'Scraped data')

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
  // Problems met while reading the profiles (for example: fewer posts than asked for), kept with the scraping stage.
  const scrapeNotes = pipeline.data.stages[2]?.metrics?.notes ?? []
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
        eyebrow={`Scraped data · ${subject}`}
        title={project.data.brandName}
        description={`Created ${formatDate(project.data.createdAt)}. ${analysed ? 'Both links are read, stored and analysed; the gaps are ready to review.' : 'Both links are read and stored; nothing is analysed yet.'}`}
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

      <FindGapsDialog
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
      />

      {phase.phase === 'idle' ? (
        <EmptyState
          icon={<ScanSearch className="size-5" />}
          title="Not scraped yet"
          description={
            isSocial
              ? 'Scraping reads the recent public posts on both profiles. It usually takes a minute or two.'
              : 'Scraping reads both sites, following links within each. It usually takes a minute or two.'
          }
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
          steps={isSocial ? SOCIAL_STEPS : WEBSITE_STEPS}
          embedStep={EMBED_STEP}
          description={
            isSocial
              ? 'Both profiles are read through Apify, one run for the posts and one for the comments on the busiest of them. You can leave this page and come back.'
              : 'Both sites are read in parallel. A page that needs JavaScript is opened in a headless browser, which can take longer. You can leave this page and come back.'
          }
        />
      ) : null}

      {phase.phase === 'failed' ? (
        <ErrorState
          title="Scraping did not finish"
          message={phase.error ?? 'The scraper stopped without saying why.'}
          onRetry={rescrape}
        />
      ) : null}

      {canAnalyse && analysis?.status === 'error' ? (
        <ErrorState
          title="The gap analysis did not finish"
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
            description="The scrape finished without storing anything. Try scraping again, or check that both links are public."
            action={
              <Button onClick={rescrape} loading={startScrape.isPending}>
                Scrape again
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
            {scrapeNotes.length > 0 ? (
              <Card className="flex gap-3 border-warning/40 bg-warning/10 p-4">
                <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning-ink" aria-hidden="true" />
                <div className="min-w-0 space-y-1">
                  <p className="text-sm font-semibold">Notes from reading the profiles</p>
                  <ul className="list-disc space-y-0.5 pl-4 text-sm text-muted-foreground">
                    {scrapeNotes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </div>
              </Card>
            ) : null}
            {isSocial ? null : (
              <div>
                <h2 className="font-display text-base font-semibold">What was collected</h2>
                <p className="mt-1 text-sm text-muted-foreground">Every page the crawler read, with its headings, links and text.</p>
              </div>
            )}
            <div className="relative grid gap-4 md:grid-cols-2 md:gap-8">
              {isSocial ? (
                <span
                  className="absolute left-1/2 top-1/2 z-10 hidden size-14 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-card font-display text-base font-extrabold text-primary shadow-lg ring-[6px] ring-primary/10 md:flex"
                  aria-hidden="true"
                >
                  VS
                </span>
              ) : null}
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
              <h2 className="font-display text-base font-semibold">Comparison parameters</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Pick a lens. Every figure is measured from what was scraped; where a parameter
                needs a judgement, the checks behind it are listed in its row.
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
              <ParameterResults result={detail.data} />
            )}
          </div>
        </>
      ) : null}
    </div>
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
  // The profile's follower count, read from its profile stats when it was scraped.
  const followers = posts.find((post) => post.followersCount != null)?.followersCount ?? null
  const total = (pick: (post: ScrapedPost) => number | null) =>
    posts.reduce((sum, post) => sum + (pick(post) ?? 0), 0)
  const reels = posts.filter((post) => (post.mediaType ?? '').toLowerCase() === 'video').length

  return (
    <Card className="relative flex h-full flex-col overflow-hidden p-0">
      <div className={isOwn ? 'h-1.5 bg-gradient-to-r from-primary to-primary/40' : 'h-1.5 bg-gradient-to-r from-warning to-warning/40'} />
      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-center gap-3">
          <ProfileAvatar
            picture={posts.find((post) => post.profilePicture)?.profilePicture ?? null}
            letter={(username || '?').slice(0, 1)}
            isOwn={isOwn}
          />
          <div className="min-w-0 flex-1">
            <p className={isOwn ? 'text-xs font-semibold text-primary' : 'text-xs font-semibold text-warning-ink'}>
              {isOwn ? 'Your page' : 'Competitor'}
            </p>
            <h3 className="truncate font-display text-lg font-bold" title={submitted}>
              {username ? `@${username}` : hostOf(submitted)}
            </h3>
          </div>
          {submitted ? (
            <a
              href={submitted}
              target="_blank"
              rel="noreferrer"
              className="flex size-9 shrink-0 items-center justify-center rounded-full border border-border/30 text-muted-foreground transition hover:border-primary/40 hover:text-primary"
              aria-label="Open profile on Instagram"
              title="Open profile on Instagram"
            >
              <ArrowUpRight className="size-4" />
            </a>
          ) : null}
        </div>

        <div className="mt-4 flex items-end justify-between gap-3 rounded-2xl bg-muted/40 px-4 py-3">
          <div>
            <p className="text-xs text-muted-foreground">Followers</p>
            <p className="font-display text-2xl font-extrabold tabular-nums">
              {followers === null ? '—' : followers.toLocaleString()}
            </p>
          </div>
          <div className="flex gap-4 text-right">
            <MiniStat label="Posts" value={posts.length} />
            <MiniStat label="Reels" value={reels} />
            <MiniStat label="Likes" value={total((post) => post.likeCount)} />
          </div>
        </div>

        {posts.length === 0 ? (
          <p className="mt-4 text-sm text-muted-foreground">No public posts could be read for this profile.</p>
        ) : (
          <PostSlider
            posts={posts}
            onOpen={(post) => {
              setOpened(post)
            }}
          />
        )}
      </div>

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
  // A video's own file cannot be shown as a picture; its cover frame can (scraped since migration 0013).
  const cover = video ? (first?.thumbnailUrl ?? null) : null

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
      ) : cover ? (
        <span className="relative block">
          <SafeImage src={mediaSrc(cover)} alt="" className="aspect-square w-full border-0" fit="cover" />
          <span className="pointer-events-none absolute right-1.5 bottom-1.5 rounded-full bg-brand-ink-black/70 p-1 text-white">
            <Play className="size-3" aria-hidden="true" />
          </span>
        </span>
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

/** A profile's posts, three at a time, with buttons to move through the rest. */
function PostSlider({ posts, onOpen }: { posts: ScrapedPost[]; onOpen: (post: ScrapedPost) => void }) {
  const PAGE = 3
  const [start, setStart] = useState(0)
  const last = Math.max(0, posts.length - PAGE)
  const shown = posts.slice(start, start + PAGE)
  const move = (step: number) => {
    setStart((current) => Math.min(last, Math.max(0, current + step * PAGE)))
  }
  return (
    <div className="mt-4">
      <div className="relative">
        <motion.ul
          key={start}
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={spring}
          className="grid grid-cols-3 gap-2"
        >
          {shown.map((post) => (
            <li key={post.id}>
              <PostTile
                post={post}
                onOpen={() => {
                  onOpen(post)
                }}
              />
            </li>
          ))}
        </motion.ul>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <button
          type="button"
          onClick={() => {
            move(-1)
          }}
          disabled={start === 0}
          className="flex size-9 items-center justify-center rounded-full border border-border/30 bg-card text-primary shadow-sm transition hover:bg-primary hover:text-primary-foreground disabled:pointer-events-none disabled:opacity-30"
          aria-label="Previous posts"
        >
          <ChevronLeft className="size-4" />
        </button>
        <span className="text-xs text-muted-foreground">
          {start + 1}–{Math.min(start + PAGE, posts.length)} of {posts.length} posts
        </span>
        <button
          type="button"
          onClick={() => {
            move(1)
          }}
          disabled={start >= last}
          className="flex size-9 items-center justify-center rounded-full border border-border/30 bg-card text-primary shadow-sm transition hover:bg-primary hover:text-primary-foreground disabled:pointer-events-none disabled:opacity-30"
          aria-label="Next posts"
        >
          <ChevronRight className="size-4" />
        </button>
      </div>
    </div>
  )
}

/**
 * The profile's own picture, with a ring in its side's colour. Instagram's picture links expire after a while, and
 * older scrapes have none, so the first letter of the handle is shown instead when there is no picture to load.
 */
function ProfileAvatar({ picture, letter, isOwn }: { picture: string | null; letter: string; isOwn: boolean }) {
  const [failed, setFailed] = useState(false)
  const ring = isOwn ? 'ring-primary/40' : 'ring-warning/60'
  if (picture && !failed) {
    return (
      <img
        src={mediaSrc(picture)}
        alt=""
        onError={() => {
          setFailed(true)
        }}
        className={`size-12 shrink-0 rounded-full object-cover shadow-md ring-2 ring-offset-2 ring-offset-card ${ring}`}
      />
    )
  }
  return (
    <span
      className={
        isOwn
          ? 'flex size-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-blush font-display text-lg font-extrabold uppercase text-primary-foreground shadow-md'
          : 'flex size-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-warning to-blush font-display text-lg font-extrabold uppercase text-warning-foreground shadow-md'
      }
      aria-hidden="true"
    >
      {letter}
    </span>
  )
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="text-sm font-bold tabular-nums">{value.toLocaleString()}</p>
    </div>
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
