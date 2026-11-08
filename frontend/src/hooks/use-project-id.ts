import { useParams } from 'react-router-dom'

/**
 * Reads :projectId from the route. Every project page needs it, and none of
 * them should have to re-derive the "missing param" case.
 */
export function useProjectId(): string {
  const { projectId } = useParams<{ projectId: string }>()
  if (!projectId) throw new Error('This route requires a :projectId param')
  return projectId
}
