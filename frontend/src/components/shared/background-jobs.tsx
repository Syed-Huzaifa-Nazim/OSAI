import { useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { projectsApi } from '@/lib/api/services'
import { queryKeys } from '@/lib/query-client'
import { isDemoMode } from '@/lib/config'
import { projectHomePath } from '@/lib/project-routes'
import { takeCancelled } from '@/lib/cancelled-jobs'
import type { Project } from '@/types/domain'

const POLL_MS = 5000

/** What a running project is doing, from its stage: 2-3 collecting posts, 4 finding gaps. */
function jobOf(project: Project): 'scrape' | 'analysis' {
  return project.currentStage === 4 ? 'analysis' : 'scrape'
}

/** A product comparison reads listings; Instagram and websites collect posts and pages. */
function isListings(project: Project): boolean {
  return project.comparisonType === 'ecommerce_product'
}

/**
 * Scraping and gap analysis run on the server as background jobs, so moving to another page never stops them.
 * This watches them from every page of the app: a small pill shows what is running, and when a job ends a
 * notification says so, with a button to the result.
 */
export function BackgroundJobs() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const seen = useRef(new Map<string, Project>())
  const { data } = useQuery({
    queryKey: queryKeys.projects.list(),
    queryFn: projectsApi.list,
    enabled: !isDemoMode,
    refetchInterval: (query) => {
      const list = query.state.data as Project[] | undefined
      return list?.some((p) => p.status === 'running') ? POLL_MS : false
    },
  })
  const running = (data ?? []).filter((p) => p.status === 'running')

  useEffect(() => {
    if (!data) return
    const before = seen.current
    for (const project of data) {
      const was = before.get(project.id)
      if (was?.status !== 'running' || project.status === 'running') continue
      if (takeCancelled(project.id)) continue // the user cancelled it: the Cancel toast already said so
      const job = jobOf(was)
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.detail(project.id) })
      if (project.status === 'failed') {
        toast.error(
          `${project.brandName}: ${job === 'analysis' ? 'finding gaps' : isListings(project) ? 'reading listings' : 'collecting posts'} stopped`,
          {
            description: 'Open the project to see why and try again.',
            duration: 15000,
            action: {
              label: 'Open',
              onClick: () => navigate(projectHomePath(project)),
            },
          },
        )
      } else if (job === 'analysis') {
        toast.success(`${project.brandName}: your gaps are ready`, {
          description: `${project.gapCount} gap${project.gapCount === 1 ? '' : 's'} found. Keep or drop each one.`,
          duration: 20000,
          action: {
            label: 'Review gaps',
            onClick: () => navigate(`/app/projects/${project.id}/review-gaps`),
          },
        })
      } else {
        toast.success(`${project.brandName}: ${isListings(project) ? 'listings read' : 'posts collected'}`, {
          description: isListings(project)
            ? 'Both listings are read. You can now compare them and find the gaps.'
            : 'Both profiles are read. You can now find the gaps.',
          duration: 15000,
          action: { label: 'Open', onClick: () => navigate(projectHomePath(project)) },
        })
      }
    }
    seen.current = new Map(data.map((p) => [p.id, p]))
  }, [data, navigate, queryClient])

  return (
    <AnimatePresence>
      {running.length > 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 16 }}
          className="fixed bottom-4 right-4 z-40 max-w-xs space-y-2"
          role="status"
          aria-live="polite"
        >
          {running.map((project) => (
            <Link
              key={project.id}
              to={projectHomePath(project)}
              className="flex items-center gap-3 rounded-full border border-primary/25 bg-card/95 py-2 pl-3 pr-4 text-sm shadow-glow backdrop-blur transition-colors hover:border-primary/50"
            >
              <Loader2 className="size-4 shrink-0 animate-spin text-primary" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block truncate font-semibold">{project.brandName}</span>
                <span className="block text-xs text-muted-foreground">
                  {jobOf(project) === 'analysis'
                    ? 'Finding gaps…'
                    : isListings(project)
                      ? 'Reading listings…'
                      : 'Collecting posts…'}{' '}
                  keeps
                  going in the background
                </span>
              </span>
            </Link>
          ))}
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}
