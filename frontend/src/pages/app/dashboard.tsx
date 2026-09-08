import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  CheckCircle2,
  FolderKanban,
  Lightbulb,
  Plus,
  UserRoundCheck,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PageHeader } from '@/components/shared/page-header'
import { StatCard } from '@/components/shared/stat-card'
import { ProjectCard } from '@/components/shared/project-card'
import { EmptyState, ErrorState, LoadingCards } from '@/components/shared/state-views'
import { HitlCallout } from '@/components/pipeline/hitl-callout'
import { ProjectStageChart } from '@/components/charts/project-status-chart'
import { useProjects } from '@/hooks/use-projects'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { formatRelative } from '@/lib/utils'
import { staggerContainer } from '@/lib/motion'

export default function DashboardPage() {
  useDocumentTitle('Dashboard')
  const { data: projects, isLoading, isError, error, refetch } = useProjects()

  const awaiting = (projects ?? []).filter((project) => project.status === 'awaiting_review')
  const complete = (projects ?? []).filter((project) => project.status === 'complete')
  const totalGaps = (projects ?? []).reduce((sum, project) => sum + project.gapCount, 0)
  const recent = [...(projects ?? [])]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, 6)

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Overview"
        title="Dashboard"
        description="Your analyses, and anything currently waiting on a decision from you."
        actions={
          <Button asChild>
            <Link to="/app/projects/new">
              <Plus />
              New analysis
            </Link>
          </Button>
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
        <LoadingCards count={4} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Projects"
              value={projects?.length ?? 0}
              icon={FolderKanban}
              hint="Across all statuses"
            />
            <StatCard
              label="Awaiting you"
              value={awaiting.length}
              icon={UserRoundCheck}
              accentClassName="text-brand-butter-cream"
              hint={awaiting.length === 0 ? 'Nothing blocked' : 'At a human checkpoint'}
            />
            <StatCard
              label="Gaps identified"
              value={totalGaps}
              icon={Lightbulb}
              accentClassName="text-stage-4"
              hint="Total across projects"
            />
            <StatCard
              label="Completed runs"
              value={complete.length}
              icon={CheckCircle2}
              accentClassName="text-success"
              hint="Strategy approved and documented"
            />
          </div>

          {awaiting.length > 0 ? (
            <section className="space-y-3">
              <h2 className="font-display text-lg font-semibold">Waiting on you</h2>
              {awaiting.map((project) => {
                const stage = project.currentStage
                if (stage !== 5 && stage !== 7) return null
                return (
                  <div key={project.id} className="space-y-1.5">
                    <p className="text-xs text-muted-foreground">{project.brandName}</p>
                    <HitlCallout projectId={project.id} stage={stage} />
                  </div>
                )
              })}
            </section>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold">Recent projects</h2>
                <Button asChild variant="ghost" size="sm">
                  <Link to="/app/projects">
                    View all
                    <ArrowRight />
                  </Link>
                </Button>
              </div>

              {recent.length === 0 ? (
                <EmptyState
                  title="No analyses yet"
                  description="Add your brand and the competitors you want to measure against. The pipeline takes it from there."
                  icon={<FolderKanban className="size-5" />}
                  action={
                    <Button asChild>
                      <Link to="/app/projects/new">
                        <Plus />
                        Start your first analysis
                      </Link>
                    </Button>
                  }
                />
              ) : (
                <motion.div
                  variants={staggerContainer}
                  initial="initial"
                  animate="animate"
                  className="grid gap-4 sm:grid-cols-2"
                >
                  {recent.map((project) => (
                    <ProjectCard key={project.id} project={project} />
                  ))}
                </motion.div>
              )}
            </section>

            <section className="space-y-3">
              <h2 className="font-display text-lg font-semibold">Where things stand</h2>
              {projects && projects.length > 0 ? (
                <ProjectStageChart projects={projects} />
              ) : (
                <Card className="p-6">
                  <p className="text-sm text-muted-foreground">
                    Stage distribution appears once you have a project running.
                  </p>
                </Card>
              )}

              <Card className="p-5">
                <h3 className="font-display text-sm font-semibold">Activity</h3>
                {recent.length === 0 ? (
                  <p className="mt-2 text-sm text-muted-foreground">Nothing to report yet.</p>
                ) : (
                  <ul className="mt-3 space-y-3">
                    {recent.slice(0, 5).map((project) => (
                      <li key={project.id} className="flex items-start gap-3">
                        <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" />
                        <div className="min-w-0">
                          <p className="truncate text-sm">
                            <Link
                              to={`/app/projects/${project.id}/pipeline`}
                              className="hover:text-primary"
                            >
                              {project.brandName}
                            </Link>{' '}
                            <span className="text-muted-foreground">
                              reached stage {project.currentStage}
                            </span>
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatRelative(project.updatedAt)}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </section>
          </div>
        </>
      )}
    </div>
  )
}
