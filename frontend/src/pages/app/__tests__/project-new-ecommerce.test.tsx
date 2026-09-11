import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import NewProjectPage from '../project-new'

/**
 * The intake form's default shape.
 *
 * Scope note: this file asserts the *rendered default* only. Driving Radix's
 * Select through a mode switch hangs under this repo's jsdom setup, so the
 * mode-switch behaviour is covered where it can be tested honestly:
 *
 *   - the conditional rules, in `lib/__tests__/validation.test.ts`
 *   - the conditional labelling, verified against a real browser
 *   - the backend half, in `backend/tests/test_projects.py`
 */

vi.mock('@/hooks/use-projects', () => ({
  useCreateProject: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/use-platforms', () => ({
  usePlatforms: () => ({
    data: [
      {
        platform: 'daraz',
        label: 'Daraz',
        urlHint: 'A Daraz product page link',
        urlExample: 'https://www.daraz.pk/products/example-i123456789-s987654321.html',
      },
    ],
    isPending: false,
  }),
  useStartScrape: () => ({ mutate: vi.fn(), isPending: false }),
}))

function renderForm() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <NewProjectPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('New analysis, comparison type', () => {
  it('asks what is being compared', () => {
    renderForm()
    expect(screen.getByRole('combobox', { name: /comparison type/i })).toBeInTheDocument()
  })

  it('defaults to an e-commerce comparison, the one type available', () => {
    renderForm()

    expect(screen.getByRole('combobox', { name: /^platform/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/^product name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^your product link/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^product link/i)).toBeInTheDocument()
  })

  it('lists website and social media as not yet available', () => {
    const { container } = renderForm()
    // Radix mirrors each item into a hidden native <select> for forms; its
    // options carry the disabled state without opening the dropdown.
    const option = (value: string) =>
      container.querySelector<HTMLOptionElement>(`select option[value="${value}"]`)

    expect(option('website')?.disabled).toBe(true)
    expect(option('social_media')?.disabled).toBe(true)
    expect(option('ecommerce_product')?.disabled).toBe(false)
  })

  it('says scraping starts on create', () => {
    renderForm()
    expect(screen.getByText(/scraping starts as soon as you create the analysis/i)).toBeInTheDocument()
  })

  it('does not ask for competitor social handles', () => {
    renderForm()
    expect(screen.queryByLabelText(/instagram/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/linkedin/i)).not.toBeInTheDocument()
  })

  it('shows the 120-character limits, and who you sell to as optional', () => {
    renderForm()
    expect(screen.getByText('Up to 120 characters')).toBeInTheDocument()
    expect(screen.getByText('Optional, up to 120 characters')).toBeInTheDocument()
    expect(screen.queryByText(/at least 40 characters/i)).not.toBeInTheDocument()
  })
})
