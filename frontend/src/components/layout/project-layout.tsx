import { Outlet } from 'react-router-dom'
import { ProjectHero } from '@/components/shared/project-hero'
import { useCompetitors, useProject } from '@/hooks/use-projects'
import { usePipeline } from '@/hooks/use-pipeline'
import { useProjectId } from '@/hooks/use-project-id'
import { userSteps } from '@/lib/user-steps'

/** "@shop" from an Instagram profile link, or null. */
function instagramHandle(url: string | null | undefined): string | null {
  const match = /instagram\.com\/([^/?#]+)/i.exec(url ?? '')
  return match ? `@${match[1]}` : null
}

/**
 * Every project page: the project's name, who is compared with whom, and the six steps with where the project
 * is now (updated from its pipeline state), above the page itself.
 */
export function ProjectLayout() {
  const projectId = useProjectId()
  const project = useProject(projectId)
  const competitors = useCompetitors(projectId)
  const pipeline = usePipeline(projectId)

  const data = project.data
  const isReal = data ? !data.isDemo : false
  const own = instagramHandle(data?.brandWebsite)
  const rivals = (competitors.data ?? []).map((c) => instagramHandle(c.landingPageUrl) ?? c.name)
  const compare =
    own && rivals.length > 0
      ? `${own} vs ${rivals.join(', ')}`
      : rivals.length > 0
        ? `Compared with ${rivals.join(', ')}`
        : undefined

  return (
    <div className="space-y-6">
      {data ? <ProjectHero name={data.brandName} compare={compare} steps={userSteps(pipeline.data, isReal)} /> : null}
      <Outlet />
    </div>
  )
}
