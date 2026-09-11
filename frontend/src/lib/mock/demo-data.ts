/**
 * Seeded demo dataset: "Verdant Roast", a fictional speciality coffee brand.
 *
 * PLACEHOLDER CONTENT. Every string here is written, not scraped or generated.
 * It exists so the full 9-stage pipeline can be walked end-to-end in a defence
 * with no live scraping and no LLM cost. Anything rendered from this file is
 * badged "Demo data" in the UI so an audience is never misled.
 *
 * The competitor names and URLs are invented; they are not real businesses.
 */

import type {
  Competitor,
  ContentSuggestion,
  Gap,
  HitlReview,
  Project,
  RunCost,
  ScrapedSource,
  Strategy,
  StrategyDocument,
} from '@/types/domain'
import type { PipelineState, StageId, StageState } from '@/types/pipeline'

export const DEMO_PROJECT_ID = 'demo-verdant-roast'
export const DEMO_USER_ID = 'demo-user-0001'

const now = new Date()
const daysAgo = (n: number): string =>
  new Date(now.getTime() - n * 86_400_000).toISOString()
const minutesAgo = (n: number): string =>
  new Date(now.getTime() - n * 60_000).toISOString()

/* ------------------------------------------------------------- project ---- */

export const demoProject: Project = {
  id: DEMO_PROJECT_ID,
  ownerId: DEMO_USER_ID,
  brandName: 'Verdant Roast',
  brandWebsite: 'https://verdantroast.example',
  brandDescription:
    'Small-batch speciality coffee roaster selling direct to consumers and to independent cafés, with a subscription tier and a single flagship storefront.',
  industry: 'ecommerce',
  targetAudience:
    'Urban home-brewing enthusiasts aged 25-40 who buy whole bean monthly, plus independent café owners sourcing wholesale.',
  objectives: [
    'Grow direct subscription revenue',
    'Win share of voice against larger regional roasters',
    'Convert café wholesale enquiries faster',
  ],
  comparisonType: 'website',
  ecommercePlatform: null,
  socialPlatform: null,
  status: 'awaiting_review',
  currentStage: 5,
  competitorCount: 3,
  gapCount: 7,
  isDemo: true,
  createdAt: daysAgo(6),
  updatedAt: minutesAgo(12),
}

export const demoCompetitors: Competitor[] = [
  {
    id: 'demo-comp-1',
    projectId: DEMO_PROJECT_ID,
    name: 'Northbrew Coffee Co.',
    landingPageUrl: 'https://northbrew.example',
    socialHandles: [
      { platform: 'instagram', handle: '@northbrewco' },
      { platform: 'tiktok', handle: '@northbrew' },
    ],
    notes: 'Largest regional player. Heavy paid social spend.',
    createdAt: daysAgo(6),
  },
  {
    id: 'demo-comp-2',
    projectId: DEMO_PROJECT_ID,
    name: 'Meridian Beans',
    landingPageUrl: 'https://meridianbeans.example',
    socialHandles: [
      { platform: 'instagram', handle: '@meridianbeans' },
      { platform: 'linkedin', handle: 'meridian-beans' },
    ],
    notes: 'Strong wholesale/B2B motion, weak consumer brand.',
    createdAt: daysAgo(6),
  },
  {
    id: 'demo-comp-3',
    projectId: DEMO_PROJECT_ID,
    name: 'Ottoline Roasters',
    landingPageUrl: 'https://ottoline.example',
    socialHandles: [
      { platform: 'instagram', handle: '@ottolineroasters' },
      { platform: 'youtube', handle: '@ottoline' },
    ],
    notes: 'Editorial content leader. Publishes brew guides weekly.',
    createdAt: daysAgo(6),
  },
]

/* ---------------------------------------------------- stage 2/3: sources, */

export const demoSources: ScrapedSource[] = [
  {
    id: 'demo-src-1',
    projectId: DEMO_PROJECT_ID,
    competitorId: 'demo-comp-1',
    kind: 'landing_page',
    url: 'https://northbrew.example/subscribe',
    title: 'Northbrew. Subscription landing page',
    excerpt:
      'Choose your grind, choose your cadence. Skip, pause or cancel any time. Free shipping over $35. 14,000 subscribers and counting.',
    status: 'embedded',
    chunkCount: 24,
    scrapedAt: daysAgo(5),
  },
  {
    id: 'demo-src-2',
    projectId: DEMO_PROJECT_ID,
    competitorId: 'demo-comp-3',
    kind: 'landing_page',
    url: 'https://ottoline.example/guides/v60',
    title: 'Ottoline. The V60 brew guide',
    excerpt:
      'A 1,900-word illustrated guide covering grind size, bloom timing, and water temperature, with an embedded four-minute video walkthrough.',
    status: 'embedded',
    chunkCount: 41,
    scrapedAt: daysAgo(5),
  },
  {
    id: 'demo-src-3',
    projectId: DEMO_PROJECT_ID,
    competitorId: 'demo-comp-1',
    kind: 'social_post',
    url: 'https://instagram.example/p/northbrew-harvest',
    title: 'Northbrew. Harvest origin reel (Instagram)',
    excerpt:
      'Reel showing the Huila harvest with farmer interviews. 42k views, 3.1k likes, 180 comments. Their best-performing post of the quarter.',
    status: 'embedded',
    chunkCount: 6,
    scrapedAt: daysAgo(5),
  },
  {
    id: 'demo-src-4',
    projectId: DEMO_PROJECT_ID,
    competitorId: 'demo-comp-2',
    kind: 'landing_page',
    url: 'https://meridianbeans.example/wholesale',
    title: 'Meridian. Wholesale enquiry page',
    excerpt:
      'Wholesale pricing tiers published openly, with a downloadable spec sheet and a 24-hour response guarantee on enquiries.',
    status: 'embedded',
    chunkCount: 18,
    scrapedAt: daysAgo(5),
  },
  {
    id: 'demo-src-5',
    projectId: DEMO_PROJECT_ID,
    competitorId: null,
    kind: 'review',
    url: 'https://reviews.example/verdant-roast',
    title: 'Customer reviews. Verdant Roast',
    excerpt:
      'Recurring theme across 62 reviews: customers love the roast but repeatedly ask "which one should I buy?" and mention the site is hard to navigate.',
    status: 'embedded',
    chunkCount: 62,
    scrapedAt: daysAgo(5),
  },
  {
    id: 'demo-src-6',
    projectId: DEMO_PROJECT_ID,
    competitorId: null,
    kind: 'forum_thread',
    url: 'https://forum.example/r/coffee/thread/regional-roasters',
    title: 'Forum thread. Best regional roasters?',
    excerpt:
      'Thread with 240 replies. Northbrew and Ottoline named 31 and 27 times respectively; Verdant Roast mentioned twice, both times favourably.',
    status: 'embedded',
    chunkCount: 33,
    scrapedAt: daysAgo(5),
  },
  {
    id: 'demo-src-7',
    projectId: DEMO_PROJECT_ID,
    competitorId: 'demo-comp-3',
    kind: 'news_article',
    url: 'https://trade-news.example/ottoline-series-a',
    title: 'Trade press. Ottoline raises to expand content studio',
    excerpt:
      'Ottoline is doubling its editorial team, citing organic search as its lowest-cost acquisition channel at roughly a third of paid social.',
    status: 'embedded',
    chunkCount: 12,
    scrapedAt: daysAgo(5),
  },
]

/* ----------------------------------------------------- stage 4/5: gaps ---- */

export const demoGaps: Gap[] = [
  {
    id: 'demo-gap-1',
    projectId: DEMO_PROJECT_ID,
    title: 'No educational brew content, while the category leader publishes weekly',
    description:
      'Ottoline runs a weekly long-form brew guide series that ranks on the highest-intent informational queries in the category. Verdant Roast publishes no educational content at all, so it is absent from the search results where buyers first form a preference.',
    category: 'content',
    priority: 'critical',
    userPriority: null,
    confidence: 0.91,
    evidence: [
      {
        sourceId: 'demo-src-2',
        sourceUrl: 'https://ottoline.example/guides/v60',
        sourceTitle: 'Ottoline. The V60 brew guide',
        quote:
          'A 1,900-word illustrated guide covering grind size, bloom timing, and water temperature, with an embedded four-minute video walkthrough.',
        relevance: 0.94,
      },
      {
        sourceId: 'demo-src-7',
        sourceUrl: 'https://trade-news.example/ottoline-series-a',
        sourceTitle: 'Trade press. Ottoline raises to expand content studio',
        quote:
          'citing organic search as its lowest-cost acquisition channel at roughly a third of paid social',
        relevance: 0.88,
      },
    ],
    opportunity:
      'A focused brew-guide series targeting the same query cluster, differentiated by tying each guide to a specific Verdant Roast bean.',
    decision: 'pending',
    reviewerNote: null,
    createdAt: daysAgo(1),
  },
  {
    id: 'demo-gap-2',
    projectId: DEMO_PROJECT_ID,
    title: 'Subscription value proposition is not stated on the landing page',
    description:
      'Northbrew leads with flexibility (skip, pause, cancel), and social proof in the form of subscriber count. Verdant Roast mentions its subscription only in the footer navigation, with no terms, cadence options or reassurance stated anywhere above the fold.',
    category: 'conversion',
    priority: 'critical',
    userPriority: null,
    confidence: 0.88,
    evidence: [
      {
        sourceId: 'demo-src-1',
        sourceUrl: 'https://northbrew.example/subscribe',
        sourceTitle: 'Northbrew. Subscription landing page',
        quote:
          'Choose your grind, choose your cadence. Skip, pause or cancel any time. Free shipping over $35. 14,000 subscribers and counting.',
        relevance: 0.93,
      },
    ],
    opportunity:
      'A dedicated subscription page carrying cadence options, the cancellation policy, and review-sourced social proof.',
    decision: 'pending',
    reviewerNote: null,
    createdAt: daysAgo(1),
  },
  {
    id: 'demo-gap-3',
    projectId: DEMO_PROJECT_ID,
    title: 'Buyers cannot tell which roast to choose',
    description:
      'The single most repeated theme across 62 customer reviews is uncertainty about which product to buy. No comparison table, flavour axis, or guided finder exists on the site, so the decision is left entirely to the customer.',
    category: 'conversion',
    priority: 'high',
    userPriority: null,
    confidence: 0.86,
    evidence: [
      {
        sourceId: 'demo-src-5',
        sourceUrl: 'https://reviews.example/verdant-roast',
        sourceTitle: 'Customer reviews. Verdant Roast',
        quote:
          'customers love the roast but repeatedly ask "which one should I buy?" and mention the site is hard to navigate',
        relevance: 0.9,
      },
    ],
    opportunity:
      'A three-question roast finder plus a flavour comparison table on every product page.',
    decision: 'pending',
    reviewerNote: null,
    createdAt: daysAgo(1),
  },
  {
    id: 'demo-gap-4',
    projectId: DEMO_PROJECT_ID,
    title: 'Origin storytelling is absent from social',
    description:
      "Northbrew's best-performing content of the quarter was a farm-origin reel with farmer interviews. Verdant Roast sources from comparable single-origin farms but publishes only product photography, forfeiting the highest-engagement format in the category.",
    category: 'social_engagement',
    priority: 'high',
    userPriority: null,
    confidence: 0.82,
    evidence: [
      {
        sourceId: 'demo-src-3',
        sourceUrl: 'https://instagram.example/p/northbrew-harvest',
        sourceTitle: 'Northbrew. Harvest origin reel (Instagram)',
        quote:
          'Reel showing the Huila harvest with farmer interviews. 42k views, 3.1k likes, 180 comments. Their best-performing post of the quarter.',
        relevance: 0.89,
      },
    ],
    opportunity:
      'A recurring origin series built from existing supplier relationships, at low production cost.',
    decision: 'pending',
    reviewerNote: null,
    createdAt: daysAgo(1),
  },
  {
    id: 'demo-gap-5',
    projectId: DEMO_PROJECT_ID,
    title: 'Wholesale pricing is gated while a competitor publishes it openly',
    description:
      'Meridian publishes wholesale tiers and a downloadable spec sheet, and commits publicly to a 24-hour response. Verdant Roast requires a contact form with no pricing indication, which filters out café buyers comparing options before making contact.',
    category: 'pricing',
    priority: 'high',
    userPriority: null,
    confidence: 0.79,
    evidence: [
      {
        sourceId: 'demo-src-4',
        sourceUrl: 'https://meridianbeans.example/wholesale',
        sourceTitle: 'Meridian. Wholesale enquiry page',
        quote:
          'Wholesale pricing tiers published openly, with a downloadable spec sheet and a 24-hour response guarantee on enquiries.',
        relevance: 0.87,
      },
    ],
    opportunity:
      'Publish indicative tier pricing and a spec sheet; keep the enquiry form for volume negotiation only.',
    decision: 'pending',
    reviewerNote: null,
    createdAt: daysAgo(1),
  },
  {
    id: 'demo-gap-6',
    projectId: DEMO_PROJECT_ID,
    title: 'Negligible share of voice in category discussion',
    description:
      'In the largest regional discussion thread, Northbrew and Ottoline are named 31 and 27 times; Verdant Roast twice. Both mentions are positive, which suggests the constraint is awareness rather than sentiment.',
    category: 'positioning',
    priority: 'medium',
    userPriority: null,
    confidence: 0.74,
    evidence: [
      {
        sourceId: 'demo-src-6',
        sourceUrl: 'https://forum.example/r/coffee/thread/regional-roasters',
        sourceTitle: 'Forum thread. Best regional roasters?',
        quote:
          'Northbrew and Ottoline named 31 and 27 times respectively; Verdant Roast mentioned twice, both times favourably',
        relevance: 0.85,
      },
    ],
    opportunity:
      'Community seeding through genuine participation, supported by the brew-guide content from gap 1.',
    decision: 'pending',
    reviewerNote: null,
    createdAt: daysAgo(1),
  },
  {
    id: 'demo-gap-7',
    projectId: DEMO_PROJECT_ID,
    title: 'No email capture beyond checkout',
    description:
      'Every competitor analysed runs a newsletter with a first-order incentive. Verdant Roast captures an address only at the point of purchase, so non-converting traffic is lost entirely.',
    category: 'audience',
    priority: 'medium',
    userPriority: null,
    confidence: 0.71,
    evidence: [
      {
        sourceId: 'demo-src-1',
        sourceUrl: 'https://northbrew.example/subscribe',
        sourceTitle: 'Northbrew. Subscription landing page',
        quote: 'Free shipping over $35. 14,000 subscribers and counting.',
        relevance: 0.72,
      },
    ],
    opportunity: 'A brew-guide-gated email capture, reusing the content from gap 1.',
    decision: 'pending',
    reviewerNote: null,
    createdAt: daysAgo(1),
  },
]

/* ------------------------------------- stage 6: strategy + critic pass ---- */

export const demoStrategy: Strategy = {
  id: 'demo-strategy-1',
  projectId: DEMO_PROJECT_ID,
  version: 1,
  title: 'Verdant Roast. Q3 Competitive Recovery Strategy',
  executiveSummary:
    'Verdant Roast competes on product quality but loses on discoverability and decision support. The three highest-leverage moves are an educational content engine to enter the search results where preference forms, a subscription page that states its own value, and guided product selection that answers the question customers are already asking in reviews. Together these address the four gaps the reviewer marked critical or high, and they compound: the content engine feeds both email capture and community presence.',
  status: 'awaiting_approval',
  addressedGapIds: ['demo-gap-1', 'demo-gap-2', 'demo-gap-3', 'demo-gap-4'],
  generatedAt: minutesAgo(40),
  approvedAt: null,
  initiatives: [
    {
      id: 'demo-init-1',
      title: 'Launch a weekly brew-guide series tied to specific beans',
      rationale:
        'Ottoline has proven the format converts in this category and has stated organic search costs it roughly a third of paid social. Entering the same query cluster with guides tied to specific Verdant Roast beans differentiates on the one axis Ottoline cannot copy, the product itself.',
      actions: [
        'Pull the 20 highest-volume informational brew queries for the region and cluster them by method.',
        'Publish one 1,200-1,800 word guide per week, each anchored to one Verdant Roast bean with brew parameters for it.',
        'Embed a short video walkthrough in the top four guides; phone-shot is sufficient.',
        'Add an inline email capture offering the full guide set as a PDF.',
        'Review ranking movement at week 8 and reallocate to the winning method cluster.',
      ],
      channel: 'Organic search / owned content',
      effort: 'high',
      expectedImpact:
        'Entry into the informational query cluster that currently sends zero traffic; compounding rather than paid-dependent.',
      timelineWeeks: 12,
      linkedGapIds: ['demo-gap-1', 'demo-gap-7'],
      revisedFromDraft: true,
    },
    {
      id: 'demo-init-2',
      title: 'Build a dedicated subscription page that states the offer',
      rationale:
        'The subscription is currently discoverable only from the footer. Northbrew leads with flexibility and subscriber-count social proof, and its subscription page is its primary conversion surface.',
      actions: [
        'Create /subscribe with cadence options, grind selection, and the cancellation policy stated plainly.',
        'Pull three review quotes about roast quality as social proof.',
        'Add the subscription entry point to primary navigation and to every product page.',
        'Instrument the funnel so drop-off between page view and first order is measurable.',
      ],
      channel: 'Website / conversion',
      effort: 'medium',
      expectedImpact:
        'Removes the discoverability barrier on the highest-value revenue line.',
      timelineWeeks: 4,
      linkedGapIds: ['demo-gap-2'],
      revisedFromDraft: false,
    },
    {
      id: 'demo-init-3',
      title: 'Ship a guided roast finder and flavour comparison',
      rationale:
        'Sixty-two reviews name the same problem: buyers cannot tell which roast to choose. This is the cheapest gap to close because the answer already exists internally. It has simply never been published.',
      actions: [
        'Define a three-question finder: brew method, roast preference, caffeine.',
        'Publish a flavour comparison table across the full range on one page.',
        'Add "best for" copy to every product card.',
        'Re-run a review sentiment scan at week 10 to confirm the theme recedes.',
      ],
      channel: 'Website / conversion',
      effort: 'low',
      expectedImpact:
        'Directly addresses the most-repeated customer complaint on record.',
      timelineWeeks: 3,
      linkedGapIds: ['demo-gap-3'],
      revisedFromDraft: false,
    },
    {
      id: 'demo-init-4',
      title: 'Run a monthly origin story series on Instagram and TikTok',
      rationale:
        "Origin content was Northbrew's highest-engagement post of the quarter, and Verdant Roast already holds the supplier relationships needed to produce it.",
      actions: [
        'Identify two supplier farms willing to be filmed this quarter.',
        'Produce one reel per month: harvest footage plus a short farmer interview.',
        'Cross-post to TikTok; link each reel to the matching single-origin product.',
        'Track saves and shares rather than likes. They predict purchase intent better here.',
      ],
      channel: 'Organic social',
      effort: 'medium',
      expectedImpact:
        'Enters the highest-engagement format in the category using assets already available.',
      timelineWeeks: 8,
      linkedGapIds: ['demo-gap-4'],
      revisedFromDraft: true,
    },
  ],
  criticFeedback: [
    {
      id: 'demo-crit-1',
      targetInitiativeId: 'demo-init-1',
      verdict: 'challenged',
      dimension: 'feasibility',
      comment:
        'The draft proposed three guides per week. For a team of this size that cadence is not sustainable past a month, and abandoning a published series damages credibility more than never starting one. Reduced to weekly and added an explicit week-8 review point.',
      before: 'Publish three long-form brew guides per week across all brew methods.',
      after:
        'Publish one 1,200-1,800 word guide per week, each anchored to one Verdant Roast bean with brew parameters for it.',
      severity: 'major',
    },
    {
      id: 'demo-crit-2',
      targetInitiativeId: 'demo-init-1',
      verdict: 'strengthened',
      dimension: 'evidence',
      comment:
        'The draft asserted content would reduce acquisition cost without support. Anchored the claim to the trade-press source where the competitor states the ratio directly, rather than leaving it as an assumption.',
      before: 'Content marketing will lower customer acquisition cost.',
      after:
        'Ottoline has stated organic search costs it roughly a third of paid social (trade press, cited).',
      severity: 'minor',
    },
    {
      id: 'demo-crit-3',
      targetInitiativeId: 'demo-init-4',
      verdict: 'challenged',
      dimension: 'clarity',
      comment:
        'The draft measured success by follower growth, which does not distinguish reach from intent. Changed the metric to saves and shares, which correlate with purchase intent in this category.',
      before: 'Measure success by follower growth month over month.',
      after:
        'Track saves and shares rather than likes. They predict purchase intent better here.',
      severity: 'minor',
    },
    {
      id: 'demo-crit-4',
      targetInitiativeId: null,
      verdict: 'rejected',
      dimension: 'feasibility',
      comment:
        'The draft included a paid-social retargeting initiative with a $4,000 monthly budget. Nothing in the intake indicates that budget exists, and the brand has no owned audience to retarget yet. Removed as premature, revisit once the content engine is generating traffic.',
      before:
        'Launch a $4,000/month paid retargeting programme across Meta and TikTok.',
      after: null,
      severity: 'major',
    },
    {
      id: 'demo-crit-5',
      targetInitiativeId: 'demo-init-3',
      verdict: 'approved',
      dimension: 'strength',
      comment:
        'Well-evidenced and correctly sized. The gap is documented in 62 reviews and the fix requires no new information, only publication of what the team already knows.',
      before: null,
      after: null,
      severity: 'info',
    },
  ],
}

/* --------------------------------------------------- stage 8: document ---- */

export const demoDocument: StrategyDocument = {
  id: 'demo-doc-1',
  projectId: DEMO_PROJECT_ID,
  strategyId: 'demo-strategy-1',
  title: 'Verdant Roast. Q3 Competitive Recovery Strategy',
  wordCount: 1840,
  availableFormats: ['pdf', 'docx', 'markdown'],
  generatedAt: minutesAgo(8),
  sections: [
    {
      id: 'demo-sec-1',
      order: 1,
      heading: 'Executive Summary',
      body: 'Verdant Roast competes on product quality but loses on discoverability and decision support. Analysis of 3 competitors across 7 sources identified 7 strategic gaps, of which 4 were prioritised by the reviewer at the gap-refinement checkpoint. The resulting strategy consists of 4 initiatives spanning 3 to 12 weeks, weighted toward owned channels because no paid budget was declared at intake.',
    },
    {
      id: 'demo-sec-2',
      order: 2,
      heading: 'Competitive Position',
      body: 'Three competitors were analysed. Northbrew leads on paid social reach and subscription conversion. Ottoline leads on organic search through a weekly editorial series. Meridian leads on wholesale transparency. Verdant Roast holds a quality advantage that is well documented in its own reviews but is not reflected in category discussion, where it is named twice against Northbrew\'s thirty-one.',
    },
    {
      id: 'demo-sec-3',
      order: 3,
      heading: 'Prioritised Gaps',
      body: 'The reviewer accepted four gaps at the first human checkpoint: absent educational content, an unstated subscription proposition, no guided product selection, and no origin storytelling on social. Three further gaps (wholesale pricing transparency, share of voice, and email capture), were retained at lower priority and are addressed indirectly by the accepted initiatives.',
    },
    {
      id: 'demo-sec-4',
      order: 4,
      heading: 'Strategic Initiatives',
      body: 'Four initiatives were generated by the Strategist and revised by the Critic. Two were materially changed: the content cadence was reduced from three guides per week to one after a feasibility challenge, and the social success metric was changed from follower growth to saves and shares. One initiative (a $4,000/month paid retargeting programme), was rejected outright as unsupported by the intake.',
    },
    {
      id: 'demo-sec-5',
      order: 5,
      heading: 'Implementation Plan',
      body: 'Weeks 1-3: ship the roast finder and comparison table (lowest effort, addresses the most-repeated complaint). Weeks 1-4: build and launch the subscription page in parallel. Weeks 2-12: run the weekly brew-guide series, with a reallocation review at week 8. Weeks 4-12: produce one origin reel per month. Re-run review sentiment analysis at week 10.',
    },
    {
      id: 'demo-sec-6',
      order: 6,
      heading: 'Validation Trail',
      body: 'Every claim in this document traces to one of 7 scraped sources, cited inline in the insights view. Two human checkpoints were recorded: gap refinement (4 of 7 accepted) and final strategy approval. The Critic logged 5 interventions against the Strategist\'s first draft, of which 2 were major.',
    },
  ],
  content: '',
}

// The viewer renders `content`; build it from the sections so the two can never
// disagree.
demoDocument.content = demoDocument.sections
  .map((section) => `## ${section.heading}\n\n${section.body}`)
  .join('\n\n')

/* ------------------------------------------------- stage 9: automation ---- */

export const demoSuggestions: ContentSuggestion[] = [
  {
    id: 'demo-sug-1',
    projectId: DEMO_PROJECT_ID,
    kind: 'blog',
    title: 'How to brew a V60 with a medium-roast Colombian',
    angle:
      'Guide one of the weekly series. Anchors the method to a specific Verdant Roast bean rather than staying generic.',
    linkedInitiativeId: 'demo-init-1',
    targetKeywords: ['v60 brew guide', 'pour over ratio', 'medium roast colombian'],
    channel: 'Blog / organic search',
    estimatedEffortHours: 6,
    status: 'suggested',
    body: null,
    createdAt: minutesAgo(6),
  },
  {
    id: 'demo-sug-2',
    projectId: DEMO_PROJECT_ID,
    kind: 'seo_brief',
    title: 'SEO brief, "best coffee subscription" query cluster',
    angle:
      'Commercial-intent cluster feeding the new subscription page. Northbrew ranks here; the page to compete with it does not exist yet.',
    linkedInitiativeId: 'demo-init-2',
    targetKeywords: ['best coffee subscription', 'coffee subscription uk', 'whole bean subscription'],
    channel: 'Organic search',
    estimatedEffortHours: 3,
    status: 'suggested',
    body: null,
    createdAt: minutesAgo(6),
  },
  {
    id: 'demo-sug-3',
    projectId: DEMO_PROJECT_ID,
    kind: 'social_post',
    title: 'Origin reel. Huila harvest, farmer interview',
    angle:
      'First entry in the monthly origin series. Matches the format that outperformed everything else on the competitor account.',
    linkedInitiativeId: 'demo-init-4',
    targetKeywords: [],
    channel: 'Instagram / TikTok',
    estimatedEffortHours: 8,
    status: 'suggested',
    body: null,
    createdAt: minutesAgo(6),
  },
  {
    id: 'demo-sug-4',
    projectId: DEMO_PROJECT_ID,
    kind: 'email',
    title: 'Welcome sequence, brew guide PDF delivery',
    angle:
      'Three-email sequence triggered by the guide download, ending on a first-order subscription offer.',
    linkedInitiativeId: 'demo-init-1',
    targetKeywords: [],
    channel: 'Email',
    estimatedEffortHours: 4,
    status: 'suggested',
    body: null,
    createdAt: minutesAgo(6),
  },
  {
    id: 'demo-sug-5',
    projectId: DEMO_PROJECT_ID,
    kind: 'ad_copy',
    title: 'Roast finder, search ad variants',
    angle:
      'Three variants pointing at the new roast finder, for when a paid budget exists. Held back deliberately: the Critic rejected paid spend this quarter.',
    linkedInitiativeId: 'demo-init-3',
    targetKeywords: ['which coffee roast', 'coffee for espresso'],
    channel: 'Paid search',
    estimatedEffortHours: 2,
    status: 'dismissed',
    body: null,
    createdAt: minutesAgo(6),
  },
]

/* ------------------------------------------------------ HITL audit trail: */

export const demoReviews: HitlReview[] = [
  {
    id: 'demo-review-1',
    projectId: DEMO_PROJECT_ID,
    stage: 5,
    reviewerId: DEMO_USER_ID,
    reviewerName: 'Demo Reviewer',
    decision: 'approved',
    notes:
      'Accepted the four gaps with direct evidence. Deprioritised wholesale pricing. That is a commercial decision above this analysis.',
    affectedIds: ['demo-gap-1', 'demo-gap-2', 'demo-gap-3', 'demo-gap-4'],
    createdAt: minutesAgo(45),
  },
]

/* ---------------------------------------------------------- run cost ------ */

export const demoRunCost: RunCost = {
  projectId: DEMO_PROJECT_ID,
  totalTokens: 184_260,
  totalCostUsd: 1.842,
  byStage: [
    { stage: 2, tokens: 42_100, costUsd: 0.421 },
    { stage: 3, tokens: 61_400, costUsd: 0.184 },
    { stage: 4, tokens: 38_900, costUsd: 0.583 },
    { stage: 6, tokens: 34_600, costUsd: 0.519 },
    { stage: 8, tokens: 7_260, costUsd: 0.135 },
  ],
}

/* ------------------------------------------------------ pipeline state ---- */

function stage(
  id: StageId,
  status: StageState['status'],
  overrides: Partial<StageState> = {},
): StageState {
  return {
    id,
    status,
    progress: status === 'complete' ? 100 : 0,
    startedAt: status === 'idle' ? null : daysAgo(1),
    completedAt: status === 'complete' ? daysAgo(1) : null,
    message: null,
    error: null,
    metrics: null,
    ...overrides,
  }
}

/** The demo project sits parked at HITL #1: the state worth showing first. */
export const demoPipeline: PipelineState = {
  projectId: DEMO_PROJECT_ID,
  currentStage: 5,
  blockedOn: 5,
  updatedAt: minutesAgo(12),
  stages: {
    1: stage(1, 'complete', {
      metrics: { itemsProcessed: 3, durationMs: 0, tokensUsed: null, costUsd: null },
    }),
    2: stage(2, 'complete', {
      message: '7 sources collected across 3 competitors',
      metrics: { itemsProcessed: 7, durationMs: 184_000, tokensUsed: 42_100, costUsd: 0.421 },
    }),
    3: stage(3, 'complete', {
      message: '196 chunks embedded into the project collection',
      metrics: { itemsProcessed: 196, durationMs: 96_000, tokensUsed: 61_400, costUsd: 0.184 },
    }),
    4: stage(4, 'complete', {
      message: '7 gaps identified',
      metrics: { itemsProcessed: 7, durationMs: 71_000, tokensUsed: 38_900, costUsd: 0.583 },
    }),
    5: stage(5, 'awaiting_human', {
      message: 'Waiting for you to prioritise the identified gaps',
      completedAt: null,
    }),
    6: stage(6, 'idle'),
    7: stage(7, 'idle'),
    8: stage(8, 'idle'),
    9: stage(9, 'idle'),
  },
}
