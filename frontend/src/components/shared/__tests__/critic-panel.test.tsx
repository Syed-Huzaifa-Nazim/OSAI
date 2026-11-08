import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CriticPanel } from '@/components/shared/critic-panel'
import type { CriticFeedback } from '@/types/domain'

const FEEDBACK: CriticFeedback[] = [
  {
    id: 'crit-1',
    targetInitiativeId: 'init-1',
    verdict: 'challenged',
    dimension: 'feasibility',
    comment: 'The draft proposed three guides per week, which is not sustainable.',
    before: 'Publish three long-form guides per week.',
    after: 'Publish one guide per week.',
    severity: 'major',
  },
  {
    id: 'crit-2',
    targetInitiativeId: null,
    verdict: 'rejected',
    dimension: 'feasibility',
    comment: 'No budget was declared, so the paid programme was removed.',
    before: 'Launch a $4,000/month paid retargeting programme.',
    after: null,
    severity: 'major',
  },
]

describe('CriticPanel', () => {
  it('shows both sides of a revision, not just the final text', () => {
    // The whole trust argument rests on the before being visible next to the
    // after; rendering only the result would make the claim unverifiable.
    render(<CriticPanel feedback={FEEDBACK} />)

    expect(screen.getByText('Publish three long-form guides per week.')).toBeInTheDocument()
    expect(screen.getByText('Publish one guide per week.')).toBeInTheDocument()
  })

  it('says plainly when something was removed rather than rewritten', () => {
    render(<CriticPanel feedback={FEEDBACK} />)
    expect(screen.getByText(/removed from the strategy entirely/i)).toBeInTheDocument()
  })

  it('flags major interventions', () => {
    render(<CriticPanel feedback={FEEDBACK} />)
    expect(screen.getAllByText('Major')).toHaveLength(2)
  })

  it('filters to one initiative when asked', () => {
    render(<CriticPanel feedback={FEEDBACK} initiativeId="init-1" />)
    expect(screen.getByText('Publish one guide per week.')).toBeInTheDocument()
    expect(screen.queryByText(/removed from the strategy entirely/i)).not.toBeInTheDocument()
  })

  it('is explicit when the Critic found nothing', () => {
    render(<CriticPanel feedback={[]} />)
    expect(screen.getByText(/did not flag anything/i)).toBeInTheDocument()
  })
})
