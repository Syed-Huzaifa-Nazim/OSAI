import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvidenceList } from '@/components/shared/evidence-list'
import type { Evidence } from '@/types/domain'

const EVIDENCE: Evidence[] = [
  {
    sourceId: 'src-1',
    sourceUrl: 'https://northbrew.example/subscribe',
    sourceTitle: 'Northbrew. Subscription landing page',
    quote: 'Skip, pause or cancel any time.',
    relevance: 0.93,
  },
]

describe('EvidenceList', () => {
  it('shows the quote, the source and the retrieval relevance', () => {
    render(<EvidenceList evidence={EVIDENCE} />)

    expect(screen.getByText('Skip, pause or cancel any time.')).toBeInTheDocument()
    expect(screen.getByText('Northbrew. Subscription landing page')).toBeInTheDocument()
    expect(screen.getByText('93% match')).toBeInTheDocument()
  })

  it('links out safely', () => {
    render(<EvidenceList evidence={EVIDENCE} />)

    const link = screen.getByRole('link', { name: /northbrew\.example/ })
    expect(link).toHaveAttribute('href', 'https://northbrew.example/subscribe')
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'))
  })

  it('says so explicitly when a claim has no source', () => {
    // Silently rendering nothing would let an uncited claim pass as cited.
    render(<EvidenceList evidence={[]} />)
    expect(screen.getByText(/no supporting source/i)).toBeInTheDocument()
  })
})
