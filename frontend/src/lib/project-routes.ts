import type { Project } from '@/types/domain'

/**
 * Where a project opens.
 *
 * An e-commerce comparison scrapes and displays; it has no agent pipeline to
 * show, so it opens on its comparison page. Everything else opens on the
 * pipeline. Every link into a project goes through this, so the two can never
 * disagree.
 */
export function projectHomePath(project: Pick<Project, 'id' | 'comparisonType'>): string {
  const base = `/app/projects/${project.id}`
  return project.comparisonType === 'ecommerce_product' ? `${base}/comparison` : `${base}/pipeline`
}

export function isScrapeOnly(project: Pick<Project, 'comparisonType'> | undefined): boolean {
  return project?.comparisonType === 'ecommerce_product'
}
