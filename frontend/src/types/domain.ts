/**
 * Domain entities. Mirrors the Supabase schema in docs/database.md and the
 * Pydantic models in backend/app/models/: keep the three in sync.
 */

import type { StageId } from './pipeline'

/* ------------------------------------------------------------------ auth: */

export interface AuthUser {
  id: string
  email: string
  fullName: string | null
  avatarUrl: string | null
  createdAt: string
}

/* --------------------------------------------------------------- project: */

export type ProjectStatus =
  | 'draft'
  | 'running'
  | 'awaiting_review'
  | 'complete'
  | 'failed'
  | 'archived'

export type Industry =
  | 'saas'
  | 'ecommerce'
  | 'fintech'
  | 'healthcare'
  | 'education'
  | 'hospitality'
  | 'agency'
  | 'manufacturing'
  | 'other'

/** What the user is comparing themselves against. Stage 2 branches on this to
 *  pick a data-acquisition strategy. */
export type ComparisonType = 'website' | 'social_media' | 'ecommerce_product'

/** An e-commerce marketplace a comparison can run against. Not a closed union:
 *  the list of platforms is served by the backend's scraper registry, so a new
 *  one appears in the picker without a frontend release. */
export type EcommercePlatform = string

/** The social platforms a social-media comparison can run against. A closed
 *  union, unlike EcommercePlatform: there is no social scraper registry yet. */
export type SocialComparisonPlatform = 'facebook' | 'instagram'

export interface PlatformOption {
  platform: EcommercePlatform
  label: string
  urlHint: string
  urlExample: string
}

export interface Project {
  id: string
  ownerId: string
  /** The user's own brand: the subject of the analysis. */
  brandName: string
  /** The user's own link: their website, their social page, or their product
   *  listing, depending on comparisonType. Required on new projects. */
  brandWebsite: string | null
  /** Up to 120 characters. */
  brandDescription: string
  industry: Industry
  /** Optional, up to 120 characters. */
  targetAudience: string | null
  /** Free-text goals from the stage-1 intake form. */
  objectives: string[]
  comparisonType: ComparisonType
  /** Set only when comparisonType is 'ecommerce_product'. */
  ecommercePlatform: EcommercePlatform | null
  /** Set only when comparisonType is 'social_media'. */
  socialPlatform: SocialComparisonPlatform | null
  status: ProjectStatus
  currentStage: StageId
  competitorCount: number
  gapCount: number
  /** True for the seeded demo project, the UI badges it so a defence audience
   *  knows it is not live-scraped data. */
  isDemo: boolean
  createdAt: string
  updatedAt: string
}

export interface Competitor {
  id: string
  projectId: string
  name: string
  landingPageUrl: string
  socialHandles: SocialHandle[]
  notes: string | null
  createdAt: string
}

export type SocialPlatform =
  | 'instagram'
  | 'linkedin'
  | 'x'
  | 'facebook'
  | 'tiktok'
  | 'youtube'

export interface SocialHandle {
  platform: SocialPlatform
  handle: string
}

/* --------------------------------------------------- stage 2/3: sources --- */

export type SourceKind =
  | 'landing_page'
  | 'social_post'
  | 'review'
  | 'forum_thread'
  | 'news_article'
  /** One scraped marketplace listing. Its structured fields live in
   *  EcommerceProduct; this row is its entry in the sources list. */
  | 'ecommerce_product'

export type SourceStatus = 'pending' | 'scraped' | 'embedded' | 'failed'

export interface ScrapedSource {
  id: string
  projectId: string
  competitorId: string | null
  kind: SourceKind
  url: string
  title: string
  /** Trimmed for list views; the full text lives in the vector store. */
  excerpt: string
  status: SourceStatus
  /** Chunks written to the project's ChromaDB collection. */
  chunkCount: number
  scrapedAt: string
}

/* ------------------------------------ stage 2: scraped product listings --- */

export type ProductRole = 'own' | 'competitor'

/** How the page was actually read. Worth surfacing: a Playwright-only scrape is
 *  slower and more fragile than a plain fetch, which matters when a result
 *  looks thin. */
export type ScrapeMethod = 'bs4' | 'playwright' | 'bs4+playwright' | 'unknown'

/** Where on the page a photo was found, most trustworthy first. */
export type ImageSource = 'gallery' | 'structured_data' | 'page' | 'og_image'

/** One product photo. The URL is the platform's own CDN; nothing is re-hosted. */
export interface ProductImage {
  id: string
  productId: string
  projectId: string
  /** 1-based gallery order. Position 1 is the main image. */
  position: number
  url: string
  isPrimary: boolean
  source: ImageSource
}

export interface EcommerceProduct {
  id: string
  projectId: string
  competitorId: string | null
  /** The ScrapedSource this listing produced, for citation lookups. */
  sourceId: string | null
  platform: EcommercePlatform
  role: ProductRole
  url: string
  productName: string

  brand: string | null
  price: number | null
  originalPrice: number | null
  discountPercent: number | null
  currency: string
  rating: number | null
  reviewCount: number
  imageCount: number
  sellerName: string | null
  sellerRating: number | null
  stockStatus: string | null
  category: string | null
  contentCompletenessScore: number | null

  /** Chunkable content, keyed by field type. */
  textFields: Record<string, string>
  /** The full scraper output, including platform-specific fields. */
  rawMetadata: Record<string, unknown>

  scrapeMethod: ScrapeMethod
  warnings: string[]
  chunkCount: number
  scrapedAt: string
  /** Main image first. Empty when the listing had none, or was scraped before
   *  images were collected. */
  images: ProductImage[]
}

/** One directly comparable field, rendered as a row in the comparison table. */
export interface MetricRow {
  field: string
  label: string
  own: string | number | boolean | null
  competitor: string | number | boolean | null
  unit: string | null
  kind: 'currency' | 'percent' | 'number' | 'rating' | 'bool' | 'text'
  higherIsBetter: boolean | null
  /** Null when the field is descriptive or one side is missing. Never
   *  defaulted: an unmeasured field has no winner. */
  winner: 'own' | 'competitor' | 'tie' | null
  delta: number | null
  deltaLabel: string | null
}

/** One comparison parameter group (A-H for Daraz) with its rows and findings. */
export interface ComparisonGroup {
  key: string
  letter: string
  label: string
  description: string
  gapCategory: GapCategory
  metrics: MetricRow[]
  ownDerived: Record<string, unknown>
  competitorDerived: Record<string, unknown>
  insights: string[]
  ownWins: number
  competitorWins: number
  /** The text fields this group searches. Empty for a metadata-only group
   *  (pricing, variants), which is compared from numbers alone. */
  semanticFieldTypes: string[]
  /** The query used to retrieve passages, if any. */
  query: string | null
}

/** A passage retrieved from one listing's embedded text. */
export interface SemanticSnippet {
  fieldType: string
  text: string
  /** Cosine similarity to the group's query, 0-1. */
  score: number | null
  chunkIndex: number
}

/** One listing's half of a parameter comparison. */
export interface ProductSide {
  productId: string
  role: ProductRole
  productName: string
  url: string
  snippets: SemanticSnippet[]
  derived: Record<string, unknown>
}

/** Everything the comparison page shows for one selected parameter. */
export interface ParameterComparison {
  parameter: ComparisonGroup
  metadataOnly: boolean
  own: ProductSide
  competitor: ProductSide
}

/* ------------------------------------------ stage 4/5: gaps & HITL #1 ----- */

export type GapCategory =
  | 'content'
  | 'seo'
  | 'social_engagement'
  | 'positioning'
  | 'audience'
  | 'conversion'
  | 'pricing'

export type GapPriority = 'critical' | 'high' | 'medium' | 'low'

/** Set by the human at HITL #1. `pending` means not yet triaged. */
export type GapDecision = 'pending' | 'accepted' | 'rejected'

export interface Gap {
  id: string
  projectId: string
  title: string
  description: string
  category: GapCategory
  /** Agent's own priority call; the human can override via `userPriority`. */
  priority: GapPriority
  userPriority: GapPriority | null
  /** 0-1. Surfaced in the UI as a percentage. */
  confidence: number
  /** Why the agent believes this. The evidence trail is the trust feature. */
  evidence: Evidence[]
  opportunity: string
  decision: GapDecision
  /** Free-text annotation the reviewer leaves at HITL #1. */
  reviewerNote: string | null
  createdAt: string
}

/** A citation back to a scraped source. Never render a claim without one. */
export interface Evidence {
  sourceId: string
  sourceUrl: string
  sourceTitle: string
  quote: string
  /** 0-1 similarity from the vector search that retrieved this chunk. */
  relevance: number
}

/* --------------------------------- stage 6/7: strategy, critic & HITL #2: */

export type StrategyStatus =
  | 'generating'
  | 'draft'
  | 'critiqued'
  | 'awaiting_approval'
  | 'approved'
  | 'revision_requested'

export interface Strategy {
  id: string
  projectId: string
  version: number
  title: string
  executiveSummary: string
  status: StrategyStatus
  initiatives: Initiative[]
  /** The Critic's pass over the Strategist's draft. Shown, never hidden. */
  criticFeedback: CriticFeedback[]
  /** Which gaps this strategy answers. */
  addressedGapIds: string[]
  generatedAt: string
  approvedAt: string | null
}

export type InitiativeEffort = 'low' | 'medium' | 'high'

export interface Initiative {
  id: string
  title: string
  rationale: string
  /** Ordered, concrete steps. This is what makes stage 8 exportable. */
  actions: string[]
  channel: string
  effort: InitiativeEffort
  expectedImpact: string
  timelineWeeks: number
  linkedGapIds: string[]
  /** Present when the Critic rewrote this initiative. */
  revisedFromDraft: boolean
}

export type CriticVerdict = 'strengthened' | 'challenged' | 'rejected' | 'approved'

/**
 * One Critic intervention. `before`/`after` power the transparency panel that
 * shows exactly what the Critic changed about the Strategist's first draft.
 */
export interface CriticFeedback {
  id: string
  targetInitiativeId: string | null
  verdict: CriticVerdict
  dimension: 'strength' | 'clarity' | 'feasibility' | 'evidence'
  comment: string
  before: string | null
  after: string | null
  severity: 'info' | 'minor' | 'major'
}

/* -------------------------------------------------------- HITL reviews ---- */

export type ReviewDecision = 'approved' | 'rejected' | 'revision_requested'

/** One row per human decision at either checkpoint. The audit trail. */
export interface HitlReview {
  id: string
  projectId: string
  /** 5 for gap refinement, 7 for final strategy approval. */
  stage: Extract<StageId, 5 | 7>
  reviewerId: string
  reviewerName: string
  decision: ReviewDecision
  notes: string | null
  /** Gap ids kept / initiative ids flagged, depending on the checkpoint. */
  affectedIds: string[]
  createdAt: string
}

/* ------------------------------------------------- stage 8: documents ----- */

export type DocumentFormat = 'pdf' | 'docx' | 'markdown'

export interface StrategyDocument {
  id: string
  projectId: string
  strategyId: string
  title: string
  /** Rendered markdown body used by the in-app viewer. */
  content: string
  sections: DocumentSection[]
  availableFormats: DocumentFormat[]
  wordCount: number
  generatedAt: string
}

export interface DocumentSection {
  id: string
  heading: string
  body: string
  order: number
}

/* ----------------------------------------------- stage 9: automation ------ */

export type AssetKind = 'blog' | 'social_post' | 'ad_copy' | 'seo_brief' | 'email'

export type AssetStatus = 'suggested' | 'queued' | 'generated' | 'dismissed'

export interface ContentSuggestion {
  id: string
  projectId: string
  kind: AssetKind
  title: string
  angle: string
  /** Which initiative this asset would execute. */
  linkedInitiativeId: string | null
  targetKeywords: string[]
  channel: string
  estimatedEffortHours: number
  status: AssetStatus
  /** Populated once generated. */
  body: string | null
  createdAt: string
}

/* ------------------------------------------------------- integrations ----- */

export type IntegrationStatus = 'available' | 'connected' | 'coming_soon' | 'error'

/** Registry row for a teammate's separately-built feature repo. See Section 8. */
export interface Integration {
  id: string
  featureKey: string
  name: string
  description: string
  status: IntegrationStatus
  connectedAt: string | null
  config: Record<string, string> | null
}

/* ------------------------------------------------------------- misc ------- */

export interface ContactSubmission {
  name: string
  email: string
  organisation: string | null
  message: string
}

export interface RunCost {
  projectId: string
  totalTokens: number
  totalCostUsd: number
  byStage: { stage: StageId; tokens: number; costUsd: number }[]
}
