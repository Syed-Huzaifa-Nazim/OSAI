import { render, screen, fireEvent, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProjectSourcesPage from '../project-sources'
import type { Project, ScrapedPage, ScrapedPost } from '@/types/domain'
import type { PipelineState, StageState } from '@/types/pipeline'

/**
 * The scraped-data page for a website or social comparison: what it collected,
 * how a profile is named, and the post detail behind a grid tile.
 *
 * Data hooks are mocked; the page's own components -- the grid, the dialog, the
 * image handling -- are real.
 */

const hooks = vi.hoisted(() => ({
  project: null as unknown,
  pipeline: null as unknown,
  documents: null as unknown,
  groups: [] as unknown[],
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
  useStartScrape: () => ({ mutate: hooks.startScrape, isPending: false }),
  useStartAnalysis: () => ({ mutate: vi.fn(), isPending: false }),
  useSourceDocuments: (_id: string, enabled: boolean) => ({
    data: enabled ? hooks.documents : undefined,
    isError: false,
    refetch: vi.fn(),
  }),
  useEcommerceComparison: (_id: string, _competitor: string, enabled: boolean) => ({
    data: enabled ? hooks.groups : undefined,
    isError: false,
  }),
  useParameterComparison: () => ({ data: undefined, isError: false, isFetching: false }),
}))

const PROJECT: Project = {
  id: 'proj_1',
  ownerId: 'user_1',
  brandName: 'Umar Khan',
  brandWebsite: 'https://www.instagram.com/umar_here.official/',
  brandDescription: 'Public profile.',
  industry: 'other',
  targetAudience: null,
  objectives: ['See how we compare'],
  comparisonType: 'social_media',
  ecommercePlatform: null,
  socialPlatform: 'instagram',
  status: 'complete',
  currentStage: 3,
  competitorCount: 1,
  gapCount: 0,
  isDemo: false,
  createdAt: '2026-09-13T10:00:00Z',
  updatedAt: '2026-09-13T10:00:00Z',
}

function stage(id: number, status: StageState['status']): StageState {
  return {
    id: id as StageState['id'],
    status,
    progress: status === 'complete' ? 100 : 0,
    startedAt: null,
    completedAt: null,
    message: null,
    error: null,
    metrics: null,
  }
}

function pipeline(scrape: StageState['status'], embed: StageState['status']) {
  const stages = Object.fromEntries(
    Array.from({ length: 9 }, (_, index) => [
      index + 1,
      stage(index + 1, index === 0 ? 'complete' : 'idle'),
    ]),
  ) as PipelineState['stages']
  stages[2] = stage(2, scrape)
  stages[3] = stage(3, embed)
  return { projectId: 'proj_1', currentStage: 2, stages, blockedOn: null, updatedAt: '' } as PipelineState
}

const PROFILE = 'https://www.instagram.com/umar_here.official/'

function post(overrides: Partial<ScrapedPost> = {}): ScrapedPost {
  const id = overrides.id ?? 'post_1'
  return {
    id,
    projectId: 'proj_1',
    sourceId: 'src_1',
    competitorId: null,
    role: 'own',
    submittedUrl: PROFILE,
    profileUrl: PROFILE,
    postUrl: `https://www.instagram.com/p/${id}/`,
    // The profile's own handle, which is what the card is labelled with.
    profileUsername: 'umar_here.official',
    ownerUsername: 'umar_here.official',
    caption: 'Farm with friends',
    captionWordCount: 3,
    hashtags: ['picnic'],
    hashtagCount: 1,
    likeCount: 25,
    commentCount: 2,
    engagementCount: 27,
    videoViewCount: null,
    mediaType: 'Image',
    mediaUrl: 'https://scontent.cdninstagram.com/v/t51.29350-15/one.jpg',
    mediaCount: 1,
    locationName: null,
    isSponsored: false,
    postedAt: '2026-05-29T08:00:00Z',
    collectedCommentCount: 2,
    scrapedAt: '2026-09-13T10:01:00Z',
    media: [
      {
        id: `med_${id}`,
        postId: id,
        projectId: 'proj_1',
        position: 1,
        mediaType: 'Image',
        mediaUrl: 'https://scontent.cdninstagram.com/v/t51.29350-15/one.jpg',
      },
    ],
    comments: [
      {
        id: `cmt_${id}`,
        postId: id,
        projectId: 'proj_1',
        position: 1,
        commenterUsername: 'coffee_fan',
        commentText: 'Ordered this morning.',
        likeCount: 4,
        postedAt: null,
      },
    ],
    ...overrides,
  }
}

function page(overrides: Partial<ScrapedPage> = {}): ScrapedPage {
  return {
    id: 'page_1',
    projectId: 'proj_1',
    sourceId: 'src_1',
    competitorId: null,
    role: 'own',
    submittedUrl: 'https://books.toscrape.com/',
    pageUrl: 'https://books.toscrape.com/',
    canonicalUrl: null,
    statusCode: 200,
    title: 'All products',
    metaDescription: null,
    headings: [],
    headingCount: 3,
    linkCount: 12,
    wordCount: 174,
    textPreview: 'Books to Scrape. We love being scraped.',
    renderer: 'http',
    depth: 0,
    isRoot: true,
    scrapedAt: '2026-09-13T10:01:00Z',
    images: [
      {
        id: 'wimg_1',
        pageId: 'page_1',
        projectId: 'proj_1',
        position: 1,
        imageUrl: 'https://books.toscrape.com/static/social-card.jpg',
        altText: 'Shelves of books',
        source: 'og_image',
        width: null,
        height: null,
        isPrimary: true,
      },
    ],
    ...overrides,
  }
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/app/projects/proj_1/sources']}>
        <Routes>
          <Route path="/app/projects/:projectId/sources" element={<ProjectSourcesPage />} />
          <Route path="/app/projects/:projectId/comparison" element={<p>comparison page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  hooks.project = PROJECT
  hooks.pipeline = pipeline('complete', 'complete')
  hooks.groups = []
  hooks.documents = {
    kind: 'instagram',
    pages: [],
    posts: [post(), post({ id: 'post_2', caption: 'Cold brew season', likeCount: 98 })],
  }
  hooks.startScrape.mockReset()
})

describe('Scraped data, Instagram', () => {
  it("names the profile after the link that was submitted, not a post's author", () => {
    // The reported bug: a collaboration post is authored by the other account,
    // and the card was labelled with that author instead of the profile.
    hooks.documents = {
      kind: 'instagram',
      pages: [],
      posts: [post({ ownerUsername: 'beingssinglemom' }), post({ id: 'post_2' })],
    }
    renderPage()

    expect(screen.getByText('@umar_here.official')).toBeInTheDocument()
    expect(screen.queryByText('@beingssinglemom')).not.toBeInTheDocument()
  })

  it('falls back to the submitted link for posts scraped before the fix', () => {
    hooks.documents = {
      kind: 'instagram',
      pages: [],
      posts: [post({ profileUsername: null, ownerUsername: 'beingssinglemom' })],
    }
    renderPage()
    expect(screen.getByText('@umar_here.official')).toBeInTheDocument()
  })

  it('shows every post as a tile with its picture', () => {
    const { container } = renderPage()

    const tiles = screen.getAllByRole('button', { name: /open post/i })
    expect(tiles).toHaveLength(2)
    // The pictures are decorative -- the caption carries the meaning -- so they
    // are queried as elements rather than by an accessible name. Instagram's
    // CDN blocks cross-origin rendering, so each one goes through the API.
    const thumbnails = container.querySelectorAll('img[src*="scontent"]')
    expect(thumbnails).toHaveLength(2)
    expect(thumbnails[0]?.getAttribute('src')).toContain('/scrapers/media?url=')
    expect(screen.getAllByText('Posts read')).toHaveLength(2)
  })

  it('opens a post with its caption, hashtags and comments', () => {
    renderPage()

    fireEvent.click(screen.getAllByRole('button', { name: /open post/i })[0] as HTMLElement)

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText('Farm with friends')).toBeInTheDocument()
    expect(within(dialog).getByText('#picnic')).toBeInTheDocument()
    expect(within(dialog).getByText('@coffee_fan')).toBeInTheDocument()
    expect(within(dialog).getByText('Ordered this morning.')).toBeInTheDocument()
    expect(within(dialog).getByText('1 collected')).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: /open on instagram/i })).toBeInTheDocument()
  })

  it('marks a post published with another account as a collaboration', () => {
    hooks.documents = {
      kind: 'instagram',
      pages: [],
      posts: [post({ ownerUsername: 'beingssinglemom' })],
    }
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /open post/i }))
    expect(
      within(screen.getByRole('dialog')).getByText('Collaboration with @beingssinglemom'),
    ).toBeInTheDocument()
  })

  it('still renders when the API has not been restarted and omits the new fields', () => {
    // A backend running code from before post media and comments were served
    // sends neither field. That must read as "nothing collected", not as a
    // crashed page -- which is exactly what it did.
    hooks.documents = {
      kind: 'instagram',
      pages: [],
      posts: [post({ media: undefined, comments: undefined })],
    }
    renderPage()

    expect(screen.getByText('@umar_here.official')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /open post/i }))
    expect(
      within(screen.getByRole('dialog')).getByText(/no comments were collected/i),
    ).toBeInTheDocument()
  })

  it('says so when a post had no comments collected', () => {
    hooks.documents = { kind: 'instagram', pages: [], posts: [post({ comments: [] })] }
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /open post/i }))
    expect(
      within(screen.getByRole('dialog')).getByText(/no comments were collected/i),
    ).toBeInTheDocument()
  })
})

describe('Scraped data, website', () => {
  beforeEach(() => {
    hooks.project = { ...PROJECT, comparisonType: 'website', socialPlatform: null }
    hooks.documents = { kind: 'website', pages: [page()], posts: [] }
  })

  it("shows the pictures a site leads with, alongside its pages", () => {
    renderPage()

    const image = screen.getByAltText('Shelves of books')
    expect(image).toHaveAttribute('src', 'https://books.toscrape.com/static/social-card.jpg')
    expect(image).toHaveAttribute('referrerpolicy', 'no-referrer')
    expect(screen.getByText('All products')).toBeInTheDocument()
    // Both sides render a card; only this one had a page to read.
    expect(screen.getAllByText('Pages read')).toHaveLength(2)
    expect(screen.getByText('Nothing could be read from this site.')).toBeInTheDocument()
  })

  it('still renders pages that came back without an images field', () => {
    hooks.documents = { kind: 'website', pages: [page({ images: undefined })], posts: [] }
    renderPage()

    expect(screen.getByText('All products')).toBeInTheDocument()
    expect(screen.getAllByText('Pages read')).toHaveLength(2)
  })

  it('replaces an expired image with a placeholder rather than breaking the card', () => {
    renderPage()

    fireEvent.error(screen.getByAltText('Shelves of books'))

    expect(screen.queryByAltText('Shelves of books')).not.toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Image unavailable' })).toBeInTheDocument()
    expect(screen.getByText('All products')).toBeInTheDocument()
  })
})