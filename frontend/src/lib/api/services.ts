/**
 * The data layer. Every component and hook goes through these functions;
 * nothing calls `api` or `mockApi` directly.
 *
 * Each function branches on `isDemoMode`: when demo mode is on (or Supabase is
 * unconfigured) it serves the seeded sample project from lib/mock, otherwise it
 * hits the FastAPI backend. The signatures are identical either way, so the
 * rest of the app cannot tell the difference.
 */

import { api } from '../api-client'
import { isDemoMode } from '../config'
import { mockApi } from '../mock/mock-api'
import type {
  ComparisonGroup,
  Competitor,
  ContentSuggestion,
  ContactSubmission,
  EcommerceProduct,
  Gap,
  ParameterComparison,
  GapDecision,
  GapPriority,
  HitlReview,
  Integration,
  PlatformOption,
  Project,
  ReviewDecision,
  RunCost,
  ScrapedDocuments,
  ScrapedSource,
  Strategy,
  StrategyDocument,
} from '@/types/domain'
import type { PipelineState } from '@/types/pipeline'

export interface CreateProjectInput {
  brandName: string
  brandWebsite: string | null
  brandDescription: string
  industry: Project['industry']
  targetAudience: string | null
  objectives: string[]
  competitors: Omit<Competitor, 'id' | 'projectId' | 'createdAt'>[]
  comparisonType: Project['comparisonType']
  /** Null unless comparisonType is 'ecommerce_product'. */
  ecommercePlatform: string | null
  /** Null unless comparisonType is 'social_media'. */
  socialPlatform: Project['socialPlatform']
}

/* ------------------------------------------------------------ projects --- */

export const projectsApi = {
  list: (): Promise<Project[]> =>
    isDemoMode ? mockApi.listProjects() : api.get<Project[]>('/projects'),

  get: (id: string): Promise<Project> =>
    isDemoMode ? mockApi.getProject(id) : api.get<Project>(`/projects/${id}`),

  create: (input: CreateProjectInput): Promise<Project> =>
    isDemoMode ? mockApi.createProject(input) : api.post<Project>('/projects', input),

  remove: (id: string): Promise<void> =>
    isDemoMode ? mockApi.deleteProject(id) : api.delete<void>(`/projects/${id}`),

  competitors: (id: string): Promise<Competitor[]> =>
    isDemoMode
      ? mockApi.listCompetitors(id)
      : api.get<Competitor[]>(`/projects/${id}/competitors`),
}

/* ------------------------------------------------------------ pipeline --- */

export const pipelineApi = {
  get: (projectId: string): Promise<PipelineState> =>
    isDemoMode
      ? mockApi.getPipeline(projectId)
      : api.get<PipelineState>(`/projects/${projectId}/pipeline`),

  /** Kicks off stage 2; the backend chains stages 3 and 4 automatically. */
  start: (projectId: string): Promise<PipelineState> =>
    isDemoMode
      ? mockApi.startPipeline(projectId)
      : api.post<PipelineState>(`/projects/${projectId}/scout/run`),

  reset: (projectId: string): Promise<PipelineState> =>
    isDemoMode
      ? mockApi.resetPipeline(projectId)
      : api.post<PipelineState>(`/projects/${projectId}/pipeline/reset`),

  sources: (projectId: string): Promise<ScrapedSource[]> =>
    isDemoMode
      ? mockApi.listSources(projectId)
      : api.get<ScrapedSource[]>(`/projects/${projectId}/sources`),
}

/* ----------------------------------------------- gaps / insights (4, 5) --- */

export interface GapPatch {
  decision?: GapDecision
  userPriority?: GapPriority | null
  reviewerNote?: string | null
}

export const gapsApi = {
  list: (projectId: string): Promise<Gap[]> =>
    isDemoMode ? mockApi.listGaps(projectId) : api.get<Gap[]>(`/projects/${projectId}/gaps`),

  update: (projectId: string, gapId: string, patch: GapPatch): Promise<Gap> =>
    isDemoMode
      ? mockApi.updateGap(projectId, gapId, patch)
      : api.patch<Gap>(`/projects/${projectId}/gaps/${gapId}`, patch),

  /** HITL checkpoint #1: closes stage 5 and releases stage 6. */
  submitReview: (
    projectId: string,
    input: { notes: string | null; acceptedGapIds: string[] },
  ): Promise<HitlReview> =>
    isDemoMode
      ? mockApi.submitGapReview(projectId, input)
      : api.post<HitlReview>(`/projects/${projectId}/gaps/review`, input),
}

/* ---------------------------------------------- strategy + critic (6,7) --- */

export const strategyApi = {
  get: (projectId: string): Promise<Strategy | null> =>
    isDemoMode
      ? mockApi.getStrategy(projectId)
      : api.get<Strategy | null>(`/projects/${projectId}/strategy`),

  generate: (projectId: string): Promise<Strategy> =>
    isDemoMode
      ? (mockApi.getStrategy(projectId) as Promise<Strategy>)
      : api.post<Strategy>(`/projects/${projectId}/strategy/generate`),

  /** HITL checkpoint #2: approve releases stage 8; revise loops back to 6. */
  submitReview: (
    projectId: string,
    input: { decision: ReviewDecision; notes: string | null; flaggedIds: string[] },
  ): Promise<HitlReview> =>
    isDemoMode
      ? mockApi.submitStrategyReview(projectId, input)
      : api.post<HitlReview>(
          `/projects/${projectId}/strategy/${input.decision === 'approved' ? 'approve' : 'revise'}`,
          input,
        ),

  reviews: (projectId: string): Promise<HitlReview[]> =>
    isDemoMode
      ? mockApi.listReviews(projectId)
      : api.get<HitlReview[]>(`/projects/${projectId}/reviews`),
}

/* ------------------------------------------------------- documents (8) --- */

export const documentsApi = {
  get: (projectId: string): Promise<StrategyDocument | null> =>
    isDemoMode
      ? mockApi.getDocument(projectId)
      : api.get<StrategyDocument | null>(`/projects/${projectId}/document`),

  generate: (projectId: string): Promise<StrategyDocument> =>
    isDemoMode
      ? (mockApi.getDocument(projectId) as Promise<StrategyDocument>)
      : api.post<StrategyDocument>(`/projects/${projectId}/document/generate`),

  /**
   * Export URL for PDF/DOCX. The backend streams the file; in demo mode there
   * is no server to stream it, so callers fall back to a client-side download
   * of the markdown (see pages/app/document).
   */
  exportUrl: (projectId: string, format: 'pdf' | 'docx'): string =>
    `/api/v1/projects/${projectId}/document/export?format=${format}`,
}

/* ------------------------------------------------------ automation (9) --- */

export const automationApi = {
  list: (projectId: string): Promise<ContentSuggestion[]> =>
    isDemoMode
      ? mockApi.listSuggestions(projectId)
      : api.get<ContentSuggestion[]>(`/projects/${projectId}/automation`),

  generate: (projectId: string): Promise<ContentSuggestion[]> =>
    isDemoMode
      ? mockApi.generateSuggestions(projectId)
      : api.post<ContentSuggestion[]>(`/projects/${projectId}/automation/suggest`),

  update: (
    projectId: string,
    suggestionId: string,
    patch: { status?: ContentSuggestion['status']; body?: string | null },
  ): Promise<ContentSuggestion> =>
    isDemoMode
      ? mockApi.updateSuggestion(projectId, suggestionId, patch)
      : api.patch<ContentSuggestion>(
          `/projects/${projectId}/automation/${suggestionId}`,
          patch,
        ),

  /** Generates the actual asset body for one suggestion. */
  draft: (projectId: string, suggestionId: string): Promise<ContentSuggestion> =>
    isDemoMode
      ? mockApi.draftSuggestion(projectId, suggestionId)
      : api.post<ContentSuggestion>(
          `/projects/${projectId}/automation/${suggestionId}/draft`,
        ),
}

/* ----------------------------------------------------------- ancillary --- */

export const costApi = {
  get: (projectId: string): Promise<RunCost> =>
    isDemoMode ? mockApi.getRunCost(projectId) : api.get<RunCost>(`/projects/${projectId}/cost`),
}

export const integrationsApi = {
  list: (): Promise<Integration[]> =>
    isDemoMode ? mockApi.listIntegrations() : api.get<Integration[]>('/integrations'),

  toggle: (id: string): Promise<Integration> =>
    isDemoMode
      ? mockApi.toggleIntegration(id)
      : api.post<Integration>(`/integrations/${id}/toggle`),
}

export const contactApi = {
  submit: (input: ContactSubmission): Promise<void> =>
    isDemoMode
      ? mockApi.submitContact()
      : api.post<void>('/contact', input, { anonymous: true }),
}

/* ------------------------------------------------------------ scrapers --- */

export const scrapersApi = {
  /**
   * The e-commerce platforms a comparison can run against.
   *
   * Served by the backend's scraper registry rather than hardcoded here, so
   * registering a scraper makes it selectable in the UI with no frontend
   * change. In demo mode the mock returns the same shape.
   */
  platforms: (): Promise<PlatformOption[]> =>
    isDemoMode ? mockApi.listPlatforms() : api.get<PlatformOption[]>('/scrapers/platforms'),

  /**
   * Scrapes both listings and embeds their text, in the background. Progress
   * is reported as pipeline stages 2 and 3; nothing after that runs.
   */
  start: (projectId: string): Promise<PipelineState> =>
    isDemoMode
      ? mockApi.startScrape(projectId)
      : api.post<PipelineState>(`/scrapers/projects/${projectId}/scrape`),

  /** The scraped listings behind an e-commerce project. */
  products: (projectId: string): Promise<EcommerceProduct[]> =>
    isDemoMode
      ? mockApi.listEcommerceProducts(projectId)
      : api.get<EcommerceProduct[]>(`/scrapers/projects/${projectId}/products`),

  /**
   * The crawled pages or scraped posts behind a website or social project.
   * The counterpart of `products` for the two comparison types whose unit is a
   * page or a post rather than a listing.
   */
  documents: (projectId: string): Promise<ScrapedDocuments> =>
    isDemoMode
      ? mockApi.listScrapedDocuments(projectId)
      : api.get<ScrapedDocuments>(`/scrapers/projects/${projectId}/documents`),

  /** Every parameter group, with who leads each, against one competitor. */
  comparison: (projectId: string, competitorId?: string): Promise<ComparisonGroup[]> =>
    isDemoMode
      ? mockApi.getEcommerceComparison(projectId)
      : api.get<ComparisonGroup[]>(
          `/scrapers/projects/${projectId}/comparison${competitorQuery(competitorId)}`,
        ),

  /** One parameter in full: metrics, read-out and retrieved passages. */
  parameter: (
    projectId: string,
    parameterKey: string,
    competitorId?: string,
  ): Promise<ParameterComparison> =>
    isDemoMode
      ? mockApi.getEcommerceParameter(projectId, parameterKey)
      : api.get<ParameterComparison>(
          `/scrapers/projects/${projectId}/comparison/${encodeURIComponent(parameterKey)}${competitorQuery(competitorId)}`,
        ),
}

function competitorQuery(competitorId: string | undefined): string {
  return competitorId ? `?competitor=${encodeURIComponent(competitorId)}` : ''
}
