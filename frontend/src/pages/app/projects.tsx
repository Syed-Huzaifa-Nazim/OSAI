import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FolderKanban, Plus, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/shared/page-header'
import { ProjectCard } from '@/components/shared/project-card'
import { PlatformSection } from '@/components/shared/platform-section'
import { PlatformPicker, type PlatformChoice } from '@/components/shared/platform-picker'
import { EmptyState, ErrorState, LoadingCards } from '@/components/shared/state-views'
import { useDeleteProject, useProjects } from '@/hooks/use-projects'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { staggerContainer } from '@/lib/motion'
import { groupByPlatform, platformOf } from '@/lib/platform-groups'
import type { Project, ProjectStatus } from '@/types/domain'

type Filter = 'all' | ProjectStatus

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'running', label: 'Running' },
  { value: 'awaiting_review', label: 'Awaiting you' },
  { value: 'complete', label: 'Complete' },
  { value: 'draft', label: 'Draft' },
]

export default function ProjectsPage() {
  useDocumentTitle('Projects')
  const { data: projects, isLoading, isError, error, refetch } = useProjects()
  const deleteProject = useDeleteProject()
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null)
  // The platform card picked (All, Instagram, Daraz...), kept in the link so the dashboard can open one directly.
  const [params, setParams] = useSearchParams()
  const platform = (params.get('platform') as PlatformChoice | null) ?? 'all'
  const choose = (value: PlatformChoice) => {
    setParams(value === 'all' ? {} : { platform: value }, { replace: true })
  }
  const platforms = groupByPlatform(projects ?? []).map((g) => ({
    ...g,
    count: g.projects.length,
    note: g.projects.some((p) => p.status === 'awaiting_review')
      ? `${g.projects.filter((p) => p.status === 'awaiting_review').length} awaiting you`
      : undefined,
  }))

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase()
    return (projects ?? []).filter((project) => {
      if (platform !== 'all' && platformOf(project) !== platform) return false
      if (filter !== 'all' && project.status !== filter) return false
      if (!term) return true
      return (
        project.brandName.toLowerCase().includes(term) ||
        project.brandDescription.toLowerCase().includes(term)
      )
    })
  }, [projects, query, filter, platform])

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Analyses"
        title="Projects"
        description="Every brand analysis you have run, and the stage each one has reached."
        actions={
          <Button asChild>
            <Link to="/app/projects/new">
              <Plus />
              New analysis
            </Link>
          </Button>
        }
      />

      {platforms.length > 0 ? (
        <PlatformPicker groups={platforms} value={platform} onChange={choose} />
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
            }}
            placeholder="Search projects"
            className="pl-9"
            aria-label="Search projects"
          />
        </div>
        <Tabs
          value={filter}
          onValueChange={(value) => {
            setFilter(value as Filter)
          }}
        >
          <TabsList>
            {FILTERS.map((item) => (
              <TabsTrigger key={item.value} value={item.value}>
                {item.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {isError ? (
        <ErrorState
          message={errorMessage(error)}
          onRetry={() => {
            void refetch()
          }}
        />
      ) : isLoading ? (
        <LoadingCards count={6} />
      ) : visible.length === 0 ? (
        <EmptyState
          title={projects?.length ? 'Nothing matches that' : 'No analyses yet'}
          description={
            projects?.length
              ? 'Try a different search term or clear the status filter.'
              : 'Add your brand and the competitors you want to measure against, and the Scout Engine will start collecting.'
          }
          icon={<FolderKanban className="size-5" />}
          action={
            projects?.length ? (
              <Button
                variant="outline"
                onClick={() => {
                  setQuery('')
                  setFilter('all')
                  choose('all')
                }}
              >
                Clear filters
              </Button>
            ) : (
              <Button asChild>
                <Link to="/app/projects/new">
                  <Plus />
                  Start your first analysis
                </Link>
              </Button>
            )
          }
        />
      ) : (
        <div className="space-y-8">
          {groupByPlatform(visible).map((group) => {
            const grid = (
              <motion.div
                variants={staggerContainer}
                initial="initial"
                animate="animate"
                className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
              >
                {group.projects.map((project) => (
                  <ProjectCard key={project.id} project={project} onDelete={setPendingDelete} />
                ))}
              </motion.div>
            )
            // All platforms: one section each. One platform picked: its cards alone (the picked card names it).
            return platform === 'all' ? (
              <PlatformSection key={group.key} platform={group} count={group.projects.length}>
                {grid}
              </PlatformSection>
            ) : (
              <div key={group.key}>{grid}</div>
            )
          })}
        </div>
      )}

      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this analysis?</DialogTitle>
            <DialogDescription>
              {pendingDelete
                ? `"${pendingDelete.brandName}" and everything the pipeline produced for it (sources, gaps, strategy and documents), will be removed. This cannot be undone.`
                : ''}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => {
                setPendingDelete(null)
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              loading={deleteProject.isPending}
              onClick={() => {
                if (!pendingDelete) return
                deleteProject.mutate(pendingDelete.id, {
                  onSuccess: () => {
                    setPendingDelete(null)
                  },
                })
              }}
            >
              Delete permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
