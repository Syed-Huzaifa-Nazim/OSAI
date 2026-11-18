import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  FolderKanban,
  Plus,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PageHeader } from '@/components/shared/page-header'
import { ProjectCard } from '@/components/shared/project-card'
import { AnalysisJourney } from '@/components/shared/analysis-journey'
import { WorkspaceVisuals } from '@/components/shared/visual-intelligence'
import { EmptyState, ErrorState, LoadingCards } from '@/components/shared/state-views'
import { useProjects } from '@/hooks/use-projects'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { errorMessage } from '@/lib/api-client'
import { projectHomePath } from '@/lib/project-routes'
import { staggerContainer } from '@/lib/motion'

export default function DashboardPage() {
  useDocumentTitle('Dashboard')
  const { data: projects, isLoading, isError, error, refetch } = useProjects()

  const awaiting = (projects ?? []).filter((project) => project.status === 'awaiting_review')
  const recent = [...(projects ?? [])]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, 6)
  const nextProject =
    awaiting[0] ?? recent.find((project) => project.status === 'running') ?? recent[0]

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
          <Card className="border-primary/20 bg-primary/5 p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="eyebrow">Next action</p>
                <h2 className="mt-1 font-display text-lg font-semibold">
                  {nextProject
                    ? awaiting.length > 0
                      ? `Review ${nextProject.brandName}`
                      : nextProject.status === 'running'
                        ? `Check ${nextProject.brandName}`
                        : `Open ${nextProject.brandName}`
                    : 'Start your first analysis'}
                </h2>
                <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                  {nextProject
                    ? awaiting.length > 0
                      ? 'A human decision is blocking the next stage. Review the evidence before continuing.'
                      : 'Your latest analysis is ready to continue from its current workspace.'
                    : 'Add your brand and competitors to see evidence-backed opportunities in one workspace.'}
                </p>
              </div>
              <Button asChild variant={nextProject ? 'default' : 'outline'}>
                <Link to={nextProject ? projectHomePath(nextProject) : '/app/projects/new'}>
                  {nextProject ? 'Continue' : 'Create analysis'}
                  <ArrowRight />
                </Link>
              </Button>
            </div>
          </Card>

          <AnalysisJourney active={awaiting.length > 0 ? 3 : nextProject?.status === 'running' ? 1 : nextProject ? 2 : 0} />

          <WorkspaceVisuals projects={projects ?? []} />

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
        </>
      )}
    </div>
  )
}
