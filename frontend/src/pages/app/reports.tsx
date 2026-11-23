import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  ArrowRight,
  Download,
  FileText,
  FolderOpen,
  ListChecks,
  MoreVertical,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { SafeImage } from '@/components/shared/safe-image'
import { PlatformSection } from '@/components/shared/platform-section'
import { PlatformPicker, type PlatformChoice } from '@/components/shared/platform-picker'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { useCompetitors, useProjects } from '@/hooks/use-projects'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { gapsApi, projectsApi } from '@/lib/api/services'
import { mediaSrc } from '@/lib/media'
import { projectHomePath } from '@/lib/project-routes'
import { groupByPlatform, platformInfo, platformOf } from '@/lib/platform-groups'
import { projectStatus } from '@/lib/project-status'
import { staggerContainer, staggerItem } from '@/lib/motion'
import { cn } from '@/lib/utils'
import type { Project } from '@/types/domain'

/** A project has a downloadable gap report once an Instagram or Daraz analysis has found gaps. */
function hasGapReport(project: Project): boolean {
  const analysed = project.socialPlatform === 'instagram' || project.ecommercePlatform === 'daraz'
  return !project.isDemo && analysed && project.gapCount > 0
}

function comparedOn(iso: string): string {
  const d = new Date(iso)
  return `${d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })} · ${d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`
}

function ReportRow({ project, cover }: { project: Project; cover?: string }) {
  const competitors = useCompetitors(project.id)
  const [busy, setBusy] = useState<'all' | 'kept' | null>(null)
  const type = platformInfo(platformOf(project))
  const status = projectStatus(project.status)
  const rival = competitors.data?.[0]?.name
  const [opening, setOpening] = useState(false)
  // The PDF opens in a new tab; the tab is opened by the click itself so the browser does not block it.
  const view = () => {
    const tab = window.open('', '_blank')
    setOpening(true)
    gapsApi
      .openReport(project.id, tab)
      .catch((err: unknown) => toast.error(errorMessage(err)))
      .finally(() => {
        setOpening(false)
      })
  }
  const download = async (which: 'all' | 'kept') => {
    setBusy(which)
    try {
      await gapsApi.downloadReport(project.id, which)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  return (
    <motion.li
      variants={staggerItem}
      className="flex items-center gap-3 rounded-2xl border border-border/15 bg-card p-3 transition-colors hover:border-primary/35 sm:gap-4 sm:p-4"
    >
      <span
        className={cn(
          'flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-xl sm:size-14',
          type.logo && !cover ? 'border border-border/20 bg-white p-2' : type.tone,
        )}
      >
        {cover ? (
          <SafeImage
            src={mediaSrc(cover)}
            alt=""
            className="size-full border-0"
            fit="cover"
            compact
          />
        ) : (
          type.logo ? (
            <img src={type.logo} alt="" className="size-full object-contain" />
          ) : (
            <type.icon className="size-6" aria-hidden="true" />
          )
        )}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-display font-bold">
          {project.brandName}
          <span className="font-medium text-muted-foreground"> vs </span>
          {rival ?? (competitors.isLoading ? '…' : 'Competitor')}
        </p>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          Compared on: {comparedOn(project.createdAt)}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] font-semibold">
          <span className={cn('rounded-full px-2 py-0.5', type.tone)}>{type.label}</span>
          <span className={cn('rounded-full px-2 py-0.5', status.tone)}>{status.label}</span>
          {project.gapCount > 0 ? (
            <span className="rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
              {project.gapCount} gap{project.gapCount === 1 ? '' : 's'}
            </span>
          ) : null}
        </div>
      </div>
      {hasGapReport(project) ? (
        <Button className="hidden shrink-0 sm:inline-flex" onClick={view} loading={opening}>
          View report
        </Button>
      ) : (
        <Button asChild className="hidden shrink-0 sm:inline-flex">
          <Link to={projectHomePath(project)}>View report</Link>
        </Button>
      )}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`More for ${project.brandName}`}
            loading={busy !== null}
          >
            <MoreVertical />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {hasGapReport(project) ? (
            <DropdownMenuItem className="sm:hidden" onSelect={view}>
              <FileText /> View report
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem asChild className="sm:hidden">
              <Link to={projectHomePath(project)}>
                <FileText /> View report
              </Link>
            </DropdownMenuItem>
          )}
          {hasGapReport(project) ? (
            <DropdownMenuItem asChild>
              <Link to={`/app/projects/${project.id}/review-gaps`}>
                <ListChecks /> Review gaps
              </Link>
            </DropdownMenuItem>
          ) : null}
          <DropdownMenuItem asChild>
            <Link to={projectHomePath(project)}>
              <FolderOpen /> Open project
            </Link>
          </DropdownMenuItem>
          {hasGapReport(project) ? (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={() => {
                  void download('all')
                }}
              >
                <Download /> Download PDF: all gaps
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={() => {
                  void download('kept')
                }}
              >
                <Download /> Download PDF: kept gaps
              </DropdownMenuItem>
            </>
          ) : null}
        </DropdownMenuContent>
      </DropdownMenu>
    </motion.li>
  )
}

export default function ReportsPage() {
  useDocumentTitle('My reports')
  const { data: projects, isLoading, isError, error, refetch } = useProjects()
  const covers = useQuery({
    queryKey: ['project-covers'],
    queryFn: projectsApi.covers,
    staleTime: 5 * 60_000,
  })
  // The platform card picked (All, Instagram, Daraz...), kept in the link.
  const [params, setParams] = useSearchParams()
  const platform = (params.get('platform') as PlatformChoice | null) ?? 'all'

  const all = [...(projects ?? [])].sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  const shown = platform === 'all' ? all : all.filter((p) => platformOf(p) === platform)
  const platforms = groupByPlatform(all).map((g) => ({
    ...g,
    count: g.projects.length,
    note: g.projects.some(hasGapReport)
      ? `${g.projects.filter(hasGapReport).length} gap report${g.projects.filter(hasGapReport).length === 1 ? '' : 's'}`
      : undefined,
  }))

  if (isError) {
    return (
      <ErrorState
        message={errorMessage(error)}
        onRetry={() => {
          void refetch()
        }}
      />
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-2xl font-bold sm:text-3xl">My reports</h1>
        <p className="mt-1 text-muted-foreground">
          Every comparison you have run, with its report.
        </p>
      </div>

      <section className="card-soft border border-border/15 p-4 sm:p-6">
        <h2 className="mb-4 font-display text-lg font-bold">My comparisons</h2>
        {platforms.length > 1 ? (
          <div className="mb-5">
            <PlatformPicker
              groups={platforms}
              value={platform}
              onChange={(value) => {
                setParams(value === 'all' ? {} : { platform: value }, { replace: true })
              }}
            />
          </div>
        ) : null}

        {isLoading ? (
          <LoadingState rows={3} />
        ) : all.length === 0 ? (
          <EmptyState
            title="No reports yet"
            description="Run your first comparison and its report will appear here."
            icon={<FileText className="size-5" />}
            action={
              <Button asChild>
                <Link to="/app/projects/new">
                  Start an analysis <ArrowRight />
                </Link>
              </Button>
            }
          />
        ) : (
          <div className="space-y-6">
            {groupByPlatform(shown).map((group) => (
              <PlatformSection
                key={group.key}
                platform={group}
                count={group.projects.length}
                className={platform === 'all' ? undefined : '[&>div:first-child]:hidden'}
              >
                <motion.ul
                  variants={staggerContainer}
                  initial="initial"
                  animate="animate"
                  className="space-y-3"
                >
                  {group.projects.map((project) => (
                    <ReportRow key={project.id} project={project} cover={covers.data?.[project.id]} />
                  ))}
                </motion.ul>
              </PlatformSection>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
