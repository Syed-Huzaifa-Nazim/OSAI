import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { gapsApi } from '@/lib/api/services'
import { GapCard } from '@/components/shared/gap-card'
import { AnalysisSummary } from '@/components/shared/analysis-summary'
import type { Gap } from '@/types/domain'
import type { AnalysisPart } from '@/types/pipeline'

const PLAIN_GAP: Gap = {
  id: 'gap-1',
  projectId: 'p-1',
  title: 'Your competitor posts carousels much more often than you do.',
  description: '12 of their 30 recent posts are carousels. You have 0 of 30.',
  category: 'content',
  priority: 'medium',
  userPriority: null,
  confidence: 0.9,
  evidence: [],
  opportunity: 'Try a few carousels and compare the results with your usual posts.',
  decision: 'pending',
  reviewerNote: null,
  createdAt: '2026-11-10T00:00:00Z',
  details: {
    kind: 'format',
    howSure: 'High',
    examples: [
      {
        who: 'competitor',
        postUrl: 'https://www.instagram.com/p/abc/',
        imageUrl: '',
        date: '12 Mar 2026',
        format: 'carousel',
        likes: 310,
        comments: 22,
        caption: 'New arrivals this week',
      },
      {
        who: 'you',
        postUrl: '',
        imageUrl: '',
        date: null,
        format: 'photo',
        likes: null,
        comments: 5,
        caption: '',
      },
    ],
    numbers: [{ label: 'Recent posts that are carousels', you: '0 of 30', competitor: '12 of 30', typical: null }],
    technical: ['Fisher exact test: p < 0.001 (shown only below 0.05).'],
  },
}

function renderCard(gap: Gap) {
  const client = new QueryClient()
  return render(
    <QueryClientProvider client={client}>
      <GapCard gap={gap} reviewable explainProjectId="p-1" />
    </QueryClientProvider>,
  )
}

const SAVED = {
  found: '12 of their 30 posts are carousels; you have 0 of 30 [E1].',
  why: 'Their carousels got about twice their usual likes [E1].',
  general: 'A carousel holds several photos in one post [K1].',
  explanation: '',
  grounded: true,
  evidence_used: ['E1'],
  knowledge_used: ['K1'],
  unknown_citations: [],
  evidence: [
    { id: 'E1', side: 'competitor' as const, format: 'carousel', date: '12 Mar 2026', likes: 310, comments: 22,
      post_url: 'https://www.instagram.com/p/abc/', image_url: '', retrieved: false, text: 'New arrivals this week' },
    { id: 'E2', side: 'you' as const, format: 'photo', date: null, likes: 90, comments: 5,
      post_url: 'https://www.instagram.com/p/def/', image_url: '', retrieved: true, text: '' },
  ],
  knowledge: [{ id: 'K1', text: 'A carousel is one post...', source: 'Instagram Help Center', url: 'https://help.instagram.com/x', verified: true }],
}

describe('GapCard in plain words', () => {
  it('shows only the finding before Explain: no numbers and no suggestion', () => {
    renderCard(PLAIN_GAP)
    expect(screen.getByText(PLAIN_GAP.title)).toBeInTheDocument()
    expect(screen.getByText('How sure: High')).toBeInTheDocument()
    expect(screen.queryByText(/12 of their 30/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Try a few carousels/)).not.toBeInTheDocument()   // actions belong to the strategy
    expect(screen.getByRole('button', { name: /explain/i })).toBeInTheDocument()
    expect(screen.queryByText(/%$/)).not.toBeInTheDocument()
  })

  it('shows a saved explanation: the key insight, why it can matter (with its source), you vs competitor and the posts', () => {
    renderCard({ ...PLAIN_GAP, details: { ...PLAIN_GAP.details, explanation: SAVED } })
    expect(screen.queryByText('Key insight')).not.toBeInTheDocument()   // closed until asked for
    fireEvent.click(screen.getByRole('button', { name: /show explanation/i }))
    expect(screen.getByText('Key insight')).toBeInTheDocument()
    expect(screen.getByText(/12 of their 30 posts are carousels/)).toBeInTheDocument()
    expect(screen.getByText(/about twice their usual likes/)).toBeInTheDocument()
    expect(screen.getByText(/Why it can matter/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'source' })).toHaveAttribute('href', 'https://help.instagram.com/x')
    expect(screen.queryByText(/\[E1\]|\[K1\]/)).not.toBeInTheDocument()            // no raw [E1] markers
    expect(screen.getByLabelText('12 of 30')).toBeInTheDocument()                   // competitor tile
    expect(screen.getByLabelText('0 of 30')).toBeInTheDocument()                    // your tile
    expect(screen.getByRole('link', { name: 'Open post 1' })).toHaveAttribute('href', 'https://www.instagram.com/p/abc/')
    expect(screen.getByText('310')).toBeInTheDocument()
    expect(screen.queryByText('How we found this')).not.toBeInTheDocument()
    expect(screen.queryByText(/Fisher exact test/)).not.toBeInTheDocument()
  })

  it('closes the explanation after reading, and opens it again', () => {
    renderCard({ ...PLAIN_GAP, details: { ...PLAIN_GAP.details, explanation: SAVED } })
    fireEvent.click(screen.getByRole('button', { name: /show explanation/i }))
    expect(screen.getByText('Key insight')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /close explanation/i }))
    expect(screen.queryByText('Key insight')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /show explanation/i }))
    fireEvent.click(screen.getByRole('button', { name: /hide explanation/i }))
    expect(screen.queryByText('Key insight')).not.toBeInTheDocument()
  })

  it('shows every post in the row, the ones the explanation mentions first', () => {
    renderCard({ ...PLAIN_GAP, details: { ...PLAIN_GAP.details, explanation: SAVED } })
    fireEvent.click(screen.getByRole('button', { name: /show explanation/i }))
    const links = screen.getAllByRole('link', { name: /Open post/ })
    expect(links.map((link) => link.getAttribute('aria-label'))).toEqual(['Open post 1', 'Open post 2'])
    expect(screen.getByText(/1 from your competitor, 1 from you/)).toBeInTheDocument()
  })

  it('shows a reel as a play sign, not a broken picture', () => {
    const reel = {
      ...SAVED,
      evidence: [{ ...SAVED.evidence[0]!, format: 'video / reel', image_url: 'https://scontent.cdninstagram.com/v/a.mp4' }],
    }
    const { container } = renderCard({ ...PLAIN_GAP, details: { ...PLAIN_GAP.details, explanation: reel } })
    fireEvent.click(screen.getByRole('button', { name: /show explanation/i }))
    expect(container.querySelector('img')).toBeNull()
  })

  it('shows a reel by its cover picture with a play sign, and the whole post opens it', () => {
    const reel = {
      ...SAVED,
      evidence: [{ ...SAVED.evidence[0]!, format: 'video / reel', image_url: 'https://cdn.test/cover.jpg' }],
    }
    const { container } = renderCard({ ...PLAIN_GAP, details: { ...PLAIN_GAP.details, explanation: reel } })
    fireEvent.click(screen.getByRole('button', { name: /show explanation/i }))
    const link = screen.getByRole('link', { name: 'Open post 1' })
    expect(link).toHaveAttribute('href', 'https://www.instagram.com/p/abc/')
    expect(link.querySelector('img')).not.toBeNull()                                // the cover picture is inside the link
    expect(link).toHaveTextContent('310')                  // likes are part of the clickable card
    expect(container.querySelectorAll('svg.lucide-play').length).toBeGreaterThan(0)
  })

  it('shows that it is working while the explanation is written', () => {
    const spy = vi.spyOn(gapsApi, 'explain').mockReturnValue(new Promise(() => {}))
    renderCard(PLAIN_GAP)
    fireEvent.click(screen.getByRole('button', { name: /^explain$/i }))
    expect(screen.getByText('Writing your explanation…')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /explaining/i })).toBeDisabled()
    spy.mockRestore()
  })

  it('labels the new kinds of gap in plain words', () => {
    renderCard({ ...PLAIN_GAP, details: { ...PLAIN_GAP.details, kind: 'topic' } })
    expect(screen.getByText('What you post about')).toBeInTheDocument()
  })

  it('still draws older gaps (no details) the old way', () => {
    const { details: _unused, ...old } = PLAIN_GAP
    renderCard({ ...old, evidence: [] })
    expect(screen.getByText('Opportunity')).toBeInTheDocument()
    expect(screen.queryByText('Key insight')).not.toBeInTheDocument()
  })
})

describe('AnalysisSummary', () => {
  const PART: AnalysisPart = {
    competitor: 'rival',
    results: {
      status: 'ran',
      reason: '',
      context: 'behind',
      user: { percentile: 70.5, quarter: 2, posts: 30, band: 'medium' },
      competitor: { percentile: 91.6, quarter: 3, posts: 30, band: 'medium' },
      peers: 332,
    },
    habits: {
      status: 'ran',
      reason: '',
      checked: 9,
      related: 3,
      gaps: 1,
      table: [
        {
          label: 'Posting rate',
          you: '7.0 posts a week',
          competitor: '0.2 posts a week',
          typical: '0.5 to 3.1',
          you_percentile: 95,
          competitor_percentile: 10,
        },
      ],
    },
    formats: { user: { photo: 0.7 }, competitor: { carousel: 0.4, photo: 0.6 }, gaps: 1, weak_spots: 1 },
    topics: {
      status: 'ran',
      reason: '',
      hashtag_gaps: 1,
      coverage: { user: '20 of 30', competitor: '25 of 30' },
      topics: { user: { 'Orders and availability': 0.5 }, competitor: { 'Seasonal collections': 0.4 } },
    },
    media: {
      status: 'ran',
      reason: '',
      scored: {
        user: { posts: 30, scored: 29, failed: 1, videos_skipped: 0 },
        competitor: { posts: 30, scored: 30, failed: 0, videos_skipped: 0 },
      },
      models: {
        image_quality: {
          label: 'Picture quality',
          scale: '1 to 5',
          available: true,
          trained_on: 'KonIQ-10k',
          n_train: 8000,
          srcc: 0.82,
          baseline_srcc: 0.55,
          description: 'a resnet50 vision network (pre-trained on general photos) reads each picture, and a ridge regression we trained on KonIQ-10k turns what it sees into a score',
        },
      },
    },
    strengths: [{ kind: 'topic', label: 'Posts about "Orders and availability"', detail: 'They get about 400 likes and comments, against 80 for your other posts.' }],
  }

  it('compares the two accounts with similar accounts in plain words and has no comment row', () => {
    render(<AnalysisSummary parts={[PART]} />)
    expect(screen.getByText('How your results compare')).toBeInTheDocument()
    expect(screen.getByText(/@rival is doing better than you/)).toBeInTheDocument()
    expect(screen.queryByText(/comment mood/i)).not.toBeInTheDocument()
  })

  it('explains the topic, picture and strength rows, and says how the scores were made', () => {
    render(<AnalysisSummary parts={[PART]} />)
    expect(screen.getByText('What the posts are about')).toBeInTheDocument()
    expect(screen.getByText('7.0 posts a week')).toBeInTheDocument()            // habits: a comparison table
    expect(screen.getByText(/For comparison only, not advice/)).toBeInTheDocument()
    expect(screen.getByText(/Checked 29 of your 30 posts/)).toBeInTheDocument()
    expect(screen.getByText(/vision network \(pre-trained on general photos\)/)).toBeInTheDocument()
    expect(screen.getByText(/against 0.55 for simple measurements alone/)).toBeInTheDocument()
    expect(screen.getByText('What works for you')).toBeInTheDocument()
    expect(screen.getByText(/They get about 400 likes and comments/)).toBeInTheDocument()
  })

  it('tells the user plainly when the picture models are not trained yet', () => {
    const part = { ...PART, media: { status: 'not_trained', reason: 'The picture and video models have not been trained yet.' } }
    render(<AnalysisSummary parts={[part]} />)
    expect(screen.getByText(/have not been trained yet/)).toBeInTheDocument()
  })

  it('does not crash on an older summary shape', () => {
    render(<AnalysisSummary parts={[{ competitor: 'old' } as AnalysisPart]} />)
    expect(screen.getByText(/you vs @old/)).toBeInTheDocument()
  })
})
