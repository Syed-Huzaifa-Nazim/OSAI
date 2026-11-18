import type { Project } from '@/types/domain'

/**
 * Where a project opens.
 *
 * Every real comparison scrapes and displays, and none of them runs the agent
 * pipeline, so none of them opens on the pipeline screen: a product comparison
 * opens on its comparison page, and a website or social one on its scraped-data
 * page. The seeded demo project is the exception, because walking the nine
 * stages is the whole reason it exists. Every link into a project goes through
 * this, so they can never disagree.
 */
export function projectHomePath(
  project: Pick<Project, 'id' | 'comparisonType' | 'isDemo'>,
): string {
  const base = `/app/projects/${project.id}`
  if (project.isDemo) return `${base}/overview`
  return project.comparisonType === 'ecommerce_product' ? `${base}/comparison` : `${base}/sources`
}

/**
 * True when a project scrapes and displays rather than running the agents.
 *
 * That is every real comparison now: each of the three types has a scraper
 * behind it, and none of them runs the nine stages. The seeded demo project is
 * the exception, and the only thing left that walks the whole pipeline.
 */
export function isScrapeOnly(
  project: Pick<Project, 'comparisonType' | 'isDemo'> | undefined,
): boolean {
  return Boolean(project) && !project?.isDemo
}
