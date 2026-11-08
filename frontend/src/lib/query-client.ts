import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './api-client'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Never retry auth or validation failures. The request will not
        // succeed on its own, and retrying just delays the error state.
        if (error instanceof ApiError && !error.isRetryable) return false
        return failureCount < 2
      },
    },
    mutations: {
      retry: false,
    },
  },
})

/** Central key factory: no stringly-typed keys scattered through components. */
export const queryKeys = {
  currentUser: ['currentUser'] as const,
  /** E-commerce platforms, served by the backend's scraper registry. Static
   *  for the session, so it is cached aggressively by the hook. */
  platforms: ['scrapers', 'platforms'] as const,

  projects: {
    all: ['projects'] as const,
    list: (filter?: string) => ['projects', 'list', filter ?? 'all'] as const,
    detail: (id: string) => ['projects', id] as const,
    competitors: (id: string) => ['projects', id, 'competitors'] as const,
    pipeline: (id: string) => ['projects', id, 'pipeline'] as const,
    sources: (id: string) => ['projects', id, 'sources'] as const,
    gaps: (id: string) => ['projects', id, 'gaps'] as const,
    strategy: (id: string) => ['projects', id, 'strategy'] as const,
    reviews: (id: string) => ['projects', id, 'reviews'] as const,
    document: (id: string) => ['projects', id, 'document'] as const,
    automation: (id: string) => ['projects', id, 'automation'] as const,
    cost: (id: string) => ['projects', id, 'cost'] as const,
    products: (id: string) => ['projects', id, 'products'] as const,
    /** Crawled pages or scraped posts, for a website/social comparison. */
    documents: (id: string) => ['projects', id, 'documents'] as const,
    comparison: (id: string, competitorId?: string) =>
      ['projects', id, 'comparison', competitorId ?? 'first'] as const,
    parameter: (id: string, key: string, competitorId?: string) =>
      ['projects', id, 'comparison', competitorId ?? 'first', key] as const,
  },
  dashboard: {
    stats: ['dashboard', 'stats'] as const,
    activity: ['dashboard', 'activity'] as const,
  },
  integrations: ['integrations'] as const,
} as const
