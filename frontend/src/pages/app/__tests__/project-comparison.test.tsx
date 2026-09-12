import { render, screen, fireEvent, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProjectComparisonPage from '../project-comparison'
import type {
  ComparisonGroup,
  EcommerceProduct,
  ParameterComparison,
  PriceTier,
  ProductImage,
  Project,
} from '@/types/domain'
import type { PipelineState, StageState } from '@/types/pipeline'

/**
 * The comparison page's states -- not scraped, scraping, failed, done -- and
 * the read-out it renders once a parameter is picked. Data hooks are mocked;
 * the page's own logic and components are real.
 */

const hooks = vi.hoisted(() => ({
  project: null as unknown,
  pipeline: null as unknown,
  products: [] as unknown[],
  groups: [] as unknown[],
  detail: undefined as unknown,
  startScrape: vi.fn(),
}))

vi.mock('@/hooks/use-projects', () => ({
  useProject: () => ({ data: hooks.project, isError: false, refetch: vi.fn() }),
}))
vi.mock('@/hooks/use-pipeline', () => ({
  usePipeline: () => ({ data: hooks.pipeline, isError: false, refetch: vi.fn() }),
}))
vi.mock('@/hooks/use-platforms', () => ({
  START_SCRAPE_KEY: ['scrapers', 'start'],
  usePlatforms: () => ({ data: [{ platform: 'daraz', label: 'Daraz', urlHint: '', urlExample: '' }] }),
  useStartScrape: () => ({ mutate: hooks.startScrape, isPending: false }),
  useEcommerceProducts: (_id: string, enabled: boolean) => ({
    data: enabled ? hooks.products : undefined,
    isError: false,
  }),
  useEcommerceComparison: (_id: string, _competitor: string, enabled: boolean) => ({
    data: enabled ? hooks.groups : undefined,
    isError: false,
  }),
  useParameterComparison: (_id: string, key: string | null) => ({
    data: key ? hooks.detail : undefined,
    isError: false,
    isFetching: false,
  }),
}))

const PROJECT: Project = {
  id: 'proj_1',
  ownerId: 'user_1',
  brandName: 'Dell wireless optical mouse',
  brandWebsite: 'https://www.daraz.pk/products/dell-i1-s1.html',
  brandDescription: 'Wireless accessories.',
  industry: 'ecommerce',
  targetAudience: null,
  objectives: ['Win the category'],
  comparisonType: 'ecommerce_product',
  ecommercePlatform: 'daraz',
  socialPlatform: null,
  status: 'complete',
  currentStage: 3,
  competitorCount: 1,
  gapCount: 0,
  isDemo: false,
  createdAt: '2026-09-11T10:00:00Z',
  updatedAt: '2026-09-11T10:00:00Z',
}

function stage(id: number, status: StageState['status'], error: string | null = null): StageState {
  return {
    id: id as StageState['id'],
    status,
    progress: status === 'complete' ? 100 : 0,
    startedAt: null,
    completedAt: null,
    message: null,
    error,
    metrics: null,
  }
}

function pipeline(scrape: StageState['status'], embed: StageState['status'], error: string | null = null) {
  const stages = Object.fromEntries(
    Array.from({ length: 9 }, (_, index) => [index + 1, stage(index + 1, index === 0 ? 'complete' : 'idle')]),
  ) as PipelineState['stages']
  stages[2] = stage(2, scrape, error)
  stages[3] = stage(3, embed)
  return { projectId: 'proj_1', currentStage: 2, stages, blockedOn: null, updatedAt: '' } as PipelineState
}

function images(role: 'own' | 'competitor', count: number): ProductImage[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `img_${role}_${index + 1}`,
    productId: `prod_${role}`,
    projectId: 'proj_1',
    position: index + 1,
    url: `https://static-01.daraz.pk/p/${role}-${index + 1}.jpg`,
    isPrimary: index === 0,
    source: 'gallery' as const,
  }))
}

function product(
  role: 'own' | 'competitor',
  name: string,
  price: number,
  imageCount = role === 'own' ? 1 : 3,
): EcommerceProduct {
  return {
    id: `prod_${role}`,
    projectId: 'proj_1',
    competitorId: role === 'own' ? null : 'comp_1',
    sourceId: `src_${role}`,
    platform: 'daraz',
    role,
    url: `https://www.daraz.pk/products/${role}.html`,
    productName: name,
    brand: 'Dell',
    price,
    originalPrice: null,
    discountPercent: null,
    currency: 'PKR',
    rating: 4.3,
    reviewCount: 23,
    imageCount: 6,
    sellerName: null,
    sellerRating: null,
    stockStatus: 'in_stock',
    category: null,
    contentCompletenessScore: 50,
    maxPrice: null,
    moq: null,
    moqUnit: null,
    leadTimeDays: null,
    textFields: {},
    rawMetadata: {},
    scrapeMethod: 'bs4+playwright',
    warnings: ['Review endpoint returned HTML rather than JSON.'],
    chunkCount: 12,
    scrapedAt: '2026-09-11T10:01:00Z',
    images: images(role, imageCount),
    priceTiers: [],
    supplier: null,
  }
}

const TIER: PriceTier = {
  id: '',
  productId: '',
  projectId: 'proj_1',
  position: 1,
  minQuantity: 1,
  maxQuantity: null,
  price: 0,
  currency: 'USD',
  unit: null,
}

/** An Alibaba listing: US-dollar tiers, a minimum order and a supplier profile. */
function alibabaProduct(
  role: 'own' | 'competitor',
  name: string,
  price: number,
  maxPrice: number,
  moq: number,
  moqUnit: string,
  supplierName: string,
): EcommerceProduct {
  const id = `prod_${role}`
  return {
    ...product(role, name, price),
    platform: 'alibaba',
    url: `https://www.alibaba.com/product-detail/${role}_1601364965690.html`,
    brand: 'No Brand',
    currency: 'USD',
    maxPrice,
    moq,
    moqUnit,
    leadTimeDays: 5,
    priceTiers: [
      { ...TIER, id: `tier_${role}_1`, productId: id, position: 1, minQuantity: moq, maxQuantity: 499, price: maxPrice, unit: moqUnit },
      { ...TIER, id: `tier_${role}_2`, productId: id, position: 2, minQuantity: 500, maxQuantity: null, price, unit: moqUnit },
    ],
    supplier: {
      id: `sup_${role}`,
      productId: id,
      projectId: 'proj_1',
      name: supplierName,
      countryCode: 'CN',
      countryName: 'China',
      yearsOnPlatform: 2,
      goldSupplier: true,
      verified: false,
      tradeAssurance: true,
      transactionLevel: 5,
      responseRate: 98.2,
      historicOrderCount: 207,
      historicGmvLabel: '$70,000+',
      mainProducts: null,
    },
  }
}

const PRICING: ComparisonGroup = {
  key: 'pricing',
  letter: 'A',
  label: 'Pricing Intelligence',
  description: 'Listed vs discounted price.',
  gapCategory: 'pricing',
  metrics: [],
  ownDerived: {},
  competitorDerived: {},
  insights: [],
  ownWins: 1,
  competitorWins: 2,
  semanticFieldTypes: [],
  query: null,
}

const CONTENT: ComparisonGroup = {
  ...PRICING,
  key: 'content_quality',
  letter: 'C',
  label: 'Content Quality',
  description: 'Description depth.',
  gapCategory: 'content',
  ownWins: 4,
  competitorWins: 1,
  semanticFieldTypes: ['description', 'specs'],
  query: 'detailed product description',
}

const DETAIL: ParameterComparison = {
  parameter: {
    ...CONTENT,
    insights: ['The competitor shows more product images.'],
    metrics: [
      {
        field: 'image_count',
        label: 'Images',
        own: 6,
        competitor: 9,
        unit: null,
        kind: 'number',
        higherIsBetter: true,
        winner: 'competitor',
        delta: -3,
        deltaLabel: 'You are 3.00 (33%) behind',
      },
    ],
  },
  metadataOnly: false,
  own: {
    productId: 'prod_own',
    role: 'own',
    productName: 'Dell wireless optical mouse',
    url: '',
    snippets: [{ fieldType: 'specs', text: 'DPI: 1000', score: 0.8123, chunkIndex: 0 }],
    derived: { media_assets: 6 },
  },
  competitor: {
    productId: 'prod_competitor',
    role: 'competitor',
    productName: 'HP W10',
    url: '',
    snippets: [],
    derived: { media_assets: 9 },
  },
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/app/projects/proj_1/comparison']}>
        <Routes>
          <Route path="/app/projects/:projectId/comparison" element={<ProjectComparisonPage />} />
          <Route path="/app/projects/:projectId/pipeline" element={<p>pipeline page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  hooks.project = PROJECT
  hooks.products = [product('own', 'Dell wireless optical mouse', 626), product('competitor', 'HP W10', 689)]
  hooks.groups = [PRICING, CONTENT]
  hooks.detail = DETAIL
  hooks.startScrape.mockReset()
})

describe('Product comparison page', () => {
  it('offers to start when nothing has been scraped', () => {
    hooks.pipeline = pipeline('idle', 'idle')
    renderPage()
    expect(screen.getByText('Not scraped yet')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /start scraping/i }))
    expect(hooks.startScrape).toHaveBeenCalledWith('proj_1')
  })

  it('shows progress while scraping', () => {
    hooks.pipeline = pipeline('running', 'idle')
    renderPage()
    expect(screen.getByRole('status')).toHaveTextContent(/fetching both product pages/i)
  })

  it('keeps showing progress between the scrape and embedding stages', () => {
    hooks.pipeline = pipeline('complete', 'idle')
    renderPage()
    expect(screen.getByRole('status')).toHaveTextContent(/embedding/i)
  })

  it("shows the scraper's error and offers a retry", () => {
    hooks.pipeline = pipeline('error', 'idle', "'amazon.com' is not a Daraz domain.")
    renderPage()
    expect(screen.getByText("'amazon.com' is not a Daraz domain.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(hooks.startScrape).toHaveBeenCalledWith('proj_1')
  })

  it('shows both listings and every parameter once scraped', () => {
    hooks.pipeline = pipeline('complete', 'complete')
    renderPage()

    expect(screen.getByText('Your product')).toBeInTheDocument()
    expect(screen.getByText('Competitor')).toBeInTheDocument()
    expect(screen.getByText('Rs. 626')).toBeInTheDocument()
    expect(screen.getByText('Rs. 689')).toBeInTheDocument()
    expect(screen.getAllByText(/view on daraz/i)).toHaveLength(2)

    const pricing = screen.getByRole('button', { name: /pricing intelligence/i })
    expect(within(pricing).getByText('Behind 1–2')).toBeInTheDocument()
    expect(within(pricing).getByText('Metadata only')).toBeInTheDocument()
    const content = screen.getByRole('button', { name: /content quality/i })
    expect(within(content).getByText('You lead 4–1')).toBeInTheDocument()

    expect(screen.getByText(/select a parameter above/i)).toBeInTheDocument()
  })

  it('renders the read-out, metric table and retrieved passages for a parameter', () => {
    hooks.pipeline = pipeline('complete', 'complete')
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /content quality/i }))

    expect(screen.getByText('Read-out')).toBeInTheDocument()
    expect(screen.getByText('The competitor shows more product images.')).toBeInTheDocument()

    const table = screen.getByRole('table')
    expect(within(table).getByText('Images')).toBeInTheDocument()
    expect(within(table).getByText('You are 3.00 (33%) behind')).toBeInTheDocument()
    expect(within(table).getByText('lead')).toBeInTheDocument()

    expect(screen.getByText('Retrieved content')).toBeInTheDocument()
    expect(screen.getByText('DPI: 1000')).toBeInTheDocument()
    expect(screen.getByText('81% match')).toBeInTheDocument()
    // The competitor had no matching passage; say so rather than show nothing.
    expect(screen.getByText(/no matching text was stored/i)).toBeInTheDocument()
  })

  it("shows each listing's main image, with the gallery as thumbnails", () => {
    hooks.pipeline = pipeline('complete', 'complete')
    renderPage()

    // Own listing has one photo: a main image and no thumbnail row.
    const ownMain = screen.getByAltText('Dell wireless optical mouse, image 1')
    expect(ownMain).toHaveAttribute('src', 'https://static-01.daraz.pk/p/own-1.jpg')
    expect(ownMain).toHaveAttribute('loading', 'eager')
    expect(ownMain).toHaveAttribute('referrerpolicy', 'no-referrer')

    // Competitor has three: main image plus three thumbnails.
    expect(screen.getByAltText('HP W10, image 1')).toBeInTheDocument()
    const thumbnails = screen.getAllByRole('button', { name: /show image \d of 3/i })
    expect(thumbnails).toHaveLength(3)
    expect(thumbnails[0]).toHaveAttribute('aria-pressed', 'true')

    const third = screen.getByRole('button', { name: 'Show image 3 of 3' })
    fireEvent.click(third)
    expect(screen.getByAltText('HP W10, image 3')).toHaveAttribute(
      'src',
      'https://static-01.daraz.pk/p/competitor-3.jpg',
    )
    expect(third).toHaveAttribute('aria-pressed', 'true')
  })

  it('replaces a broken image with a placeholder instead of breaking the card', () => {
    hooks.pipeline = pipeline('complete', 'complete')
    renderPage()

    fireEvent.error(screen.getByAltText('Dell wireless optical mouse, image 1'))
    expect(screen.queryByAltText('Dell wireless optical mouse, image 1')).not.toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Image unavailable' })).toBeInTheDocument()
    // The rest of the card is unaffected.
    expect(screen.getByText('Rs. 626')).toBeInTheDocument()
  })

  it('says so when a listing has no images', () => {
    hooks.pipeline = pipeline('complete', 'complete')
    hooks.products = [product('own', 'Dell wireless optical mouse', 626, 0), product('competitor', 'HP W10', 689)]
    renderPage()
    expect(
      screen.getByRole('img', { name: 'No product images were found on this listing' }),
    ).toBeInTheDocument()
  })

  it('shows both galleries beside the image metrics', () => {
    hooks.pipeline = pipeline('complete', 'complete')
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: /content quality/i }))

    expect(screen.getByText('Product images')).toBeInTheDocument()
    expect(screen.getByText('1 image')).toBeInTheDocument()
    expect(screen.getByText('3 images')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open image 2 of HP W10' })).toHaveAttribute(
      'href',
      'https://static-01.daraz.pk/p/competitor-2.jpg',
    )
  })

  it('does not show galleries for parameters that do not compare images', () => {
    hooks.pipeline = pipeline('complete', 'complete')
    hooks.detail = { ...DETAIL, parameter: { ...DETAIL.parameter, metrics: [] } }
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: /content quality/i }))
    expect(screen.queryByText('Product images')).not.toBeInTheDocument()
  })

  it("shows an Alibaba listing's price range in dollars, its minimum order and supplier", () => {
    hooks.project = { ...PROJECT, ecommercePlatform: 'alibaba' }
    hooks.pipeline = pipeline('complete', 'complete')
    hooks.products = [
      alibabaProduct('own', 'Mini Wireless Mouse', 0.75, 0.77, 100, 'pieces', 'Guangzhou Kingmega Electronic Firm'),
      alibabaProduct('competitor', 'MLOONG MX302', 9.5, 12.99, 1, 'piece', 'Dongguan Couso Technology Co., Ltd.'),
    ]
    renderPage()

    expect(screen.getByText('US$0.75 – US$0.77')).toBeInTheDocument()
    expect(screen.getByText('US$9.50 – US$12.99')).toBeInTheDocument()
    expect(screen.queryByText(/^Rs\./)).not.toBeInTheDocument()
    expect(screen.getByText('100 pieces')).toBeInTheDocument()
    expect(screen.getByText('1 piece')).toBeInTheDocument()
    expect(screen.getByText('Guangzhou Kingmega Electronic Firm')).toBeInTheDocument()
    expect(screen.getAllByText(/view on alibaba/i)).toHaveLength(2)
  })

  it('does not show wholesale fields on a Daraz card', () => {
    hooks.pipeline = pipeline('complete', 'complete')
    renderPage()
    expect(screen.queryByText('Min. order')).not.toBeInTheDocument()
    expect(screen.queryByText('Supplier')).not.toBeInTheDocument()
  })

  it('formats an Alibaba metric row per side, in its own units', () => {
    hooks.project = { ...PROJECT, ecommercePlatform: 'alibaba' }
    hooks.pipeline = pipeline('complete', 'complete')
    hooks.products = [
      alibabaProduct('own', 'Mini Wireless Mouse', 0.75, 0.77, 100, 'pieces', 'Kingmega'),
      alibabaProduct('competitor', 'MLOONG MX302', 9.5, 12.99, 20, 'boxes', 'Couso'),
    ]
    const orderTerms: ComparisonGroup = {
      ...PRICING,
      key: 'order_terms',
      letter: 'I',
      label: 'Order Terms & Bulk Pricing',
      semanticFieldTypes: ['order_terms'],
    }
    const detail: ParameterComparison = {
      ...DETAIL,
      parameter: {
        ...orderTerms,
        metrics: [
          {
            field: 'moq',
            label: 'Minimum order quantity',
            own: 100,
            competitor: 20,
            unit: 'pieces vs boxes',
            kind: 'number',
            higherIsBetter: false,
            winner: null,
            delta: null,
            deltaLabel: null,
          },
          {
            field: 'best_tier_price',
            label: 'Best bulk price',
            own: 0.0035,
            competitor: 9.5,
            unit: 'USD',
            kind: 'currency',
            higherIsBetter: false,
            winner: 'own',
            delta: -9.4965,
            deltaLabel: 'You are 9.50 (100%) ahead',
          },
        ],
      },
      own: {
        ...DETAIL.own,
        snippets: [
          { fieldType: 'order_terms', text: 'Minimum order quantity: 100 pieces', score: 0.7, chunkIndex: 0 },
        ],
      },
    }
    hooks.groups = [orderTerms]
    hooks.detail = detail
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /order terms & bulk pricing/i }))

    const table = screen.getByRole('table')
    expect(within(table).getByText('100 pieces')).toBeInTheDocument()
    expect(within(table).getByText('20 boxes')).toBeInTheDocument()
    expect(within(table).getByText('not comparable')).toBeInTheDocument()
    expect(within(table).getByText('US$0.0035')).toBeInTheDocument()
    expect(within(table).getByText('US$9.50')).toBeInTheDocument()
    expect(screen.getAllByText('Order terms & price tiers').length).toBeGreaterThan(0)
  })

  it('sends a non-e-commerce project to its pipeline instead', () => {
    hooks.project = { ...PROJECT, comparisonType: 'website', ecommercePlatform: null }
    hooks.pipeline = pipeline('idle', 'idle')
    renderPage()
    expect(screen.getByText('pipeline page')).toBeInTheDocument()
  })
})
