import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ConfidenceMeter } from '@/components/shared/confidence-meter'

describe('ConfidenceMeter', () => {
  it('exposes the value to assistive technology, not just to sighted users', () => {
    render(<ConfidenceMeter value={0.91} />)

    const meter = screen.getByRole('meter', { name: /agent confidence/i })
    expect(meter).toHaveAttribute('aria-valuenow', '91')
    expect(meter).toHaveAttribute('aria-valuemin', '0')
    expect(meter).toHaveAttribute('aria-valuemax', '100')
  })

  it('renders the percentage label by default', () => {
    render(<ConfidenceMeter value={0.74} />)
    expect(screen.getByText('74%')).toBeInTheDocument()
  })

  it('can hide the label without hiding the value from screen readers', () => {
    render(<ConfidenceMeter value={0.74} showLabel={false} />)
    expect(screen.queryByText('74%')).not.toBeInTheDocument()
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '74')
  })
})
