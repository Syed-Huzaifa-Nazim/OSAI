import { Navigate } from 'react-router-dom'
import { RouteFallback } from '@/components/shared/route-fallback'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { projectHomePath } from '@/lib/project-routes'

/**
 * `/app/projects/:id` with no sub-page: open the project where it lives. An
 * e-commerce comparison has no pipeline to land on, so the target depends on
 * the project and cannot be a static redirect.
 */
export default function ProjectIndexRedirect() {
  const projectId = useProjectId()
  const project = useProject(projectId)

  if (project.data) return <Navigate to={projectHomePath(project.data)} replace />
  // On an error, fall back to the pipeline page, which reports it properly.
  if (project.isError) return <Navigate to={`/app/projects/${projectId}/overview`} replace />
  return <RouteFallback />
}
