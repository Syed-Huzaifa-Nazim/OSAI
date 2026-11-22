import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { pipelineApi, scrapersApi } from '@/lib/api/services'
import { errorMessage } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-client'

/**
 * The e-commerce platforms a comparison can run against.
 *
 * The list comes from the backend's scraper registry rather than a constant in
 * this repo, so registering a new scraper makes it selectable here without a
 * frontend release. It is a capability list, not user data, so it is cached for
 * the whole session.
 */
export function usePlatforms() {
  return useQuery({
    queryKey: queryKeys.platforms,
    queryFn: scrapersApi.platforms,
    staleTime: Infinity,
  })
}

/** The scraped listings behind an e-commerce project. */
export function useEcommerceProducts(projectId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: queryKeys.projects.products(projectId ?? ''),
    queryFn: () => scrapersApi.products(projectId as string),
    enabled: Boolean(projectId) && enabled,
  })
}

/** The crawled pages or scraped posts behind a website or social project. */
export function useSourceDocuments(projectId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: queryKeys.projects.documents(projectId ?? ''),
    queryFn: () => scrapersApi.documents(projectId as string),
    enabled: Boolean(projectId) && enabled,
  })
}

/** Every parameter group, with who leads each, against one competitor. */
export function useEcommerceComparison(
  projectId: string | undefined,
  competitorId: string | undefined,
  enabled = true,
) {
  return useQuery({
    queryKey: queryKeys.projects.comparison(projectId ?? '', competitorId),
    queryFn: () => scrapersApi.comparison(projectId as string, competitorId),
    enabled: Boolean(projectId) && enabled,
    placeholderData: keepPreviousData,
  })
}

/** One parameter in full. Only fetched once a parameter is picked. */
export function useParameterComparison(
  projectId: string | undefined,
  parameterKey: string | null,
  competitorId: string | undefined,
) {
  return useQuery({
    queryKey: queryKeys.projects.parameter(projectId ?? '', parameterKey ?? '', competitorId),
    queryFn: () => scrapersApi.parameter(projectId as string, parameterKey as string, competitorId),
    enabled: Boolean(projectId && parameterKey),
  })
}

/** Shared by every caller, so a page can tell a scrape is being started
 *  elsewhere -- by the intake form, just before navigating to it. */
export const START_SCRAPE_KEY = ['scrapers', 'start'] as const

/**
 * Starts scraping. The response already shows stage 2 running, so it is
 * written straight into the pipeline cache and polling picks up from there.
 */
export function useStartScrape() {
  const client = useQueryClient()
  return useMutation({
    mutationKey: START_SCRAPE_KEY,
    mutationFn: (projectId: string) => scrapersApi.start(projectId),
    onSuccess: async (state, projectId) => {
      client.setQueryData(queryKeys.projects.pipeline(projectId), state)
      // A re-scrape replaces the listings, so anything derived from the old
      // ones is stale.
      await client.invalidateQueries({ queryKey: queryKeys.projects.products(projectId) })
      await client.invalidateQueries({ queryKey: queryKeys.projects.documents(projectId) })
      await client.invalidateQueries({ queryKey: queryKeys.projects.sources(projectId) })
      await client.invalidateQueries({ queryKey: ['projects', projectId, 'comparison'] })
      await client.invalidateQueries({ queryKey: queryKeys.projects.detail(projectId) })
      // the app-wide job watcher reads the project list: it must see the job start
      await client.invalidateQueries({ queryKey: queryKeys.projects.list() })
    },
    onError: (error) => {
      toast.error('Could not start scraping', { description: errorMessage(error) })
    },
  })
}

/**
 * Starts the gap analysis on a scraped Instagram comparison: the engagement
 * model, content gaps and comment mood (stage 4). The run is a background
 * task; the pipeline query polls while stage 4 is running.
 */
export function useStartAnalysis() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) => pipelineApi.analyse(projectId),
    onSuccess: async (state, projectId) => {
      client.setQueryData(queryKeys.projects.pipeline(projectId), state)
      await client.invalidateQueries({ queryKey: queryKeys.projects.detail(projectId) })
      // the app-wide job watcher reads the project list: it must see the job start
      await client.invalidateQueries({ queryKey: queryKeys.projects.list() })
    },
    onError: (error) => {
      toast.error('Could not start the analysis', { description: errorMessage(error) })
    },
  })
}
