import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

  it('defaults to an Instagram comparison, the product the site is about', () => {
    renderForm()

    expect(screen.getByLabelText(/^page name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^platform link/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/^product name/i)).not.toBeInTheDocument()
  })

  it('offers Instagram and marketplace listings, and no longer offers websites', () => {
    const { container } = renderForm()
    // Radix mirrors each item into a hidden native <select> for forms; its
    // options carry the disabled state without opening the dropdown.
    const option = (value: string) =>
      container.querySelector<HTMLOptionElement>(`select option[value="${value}"]`)

    expect(option('website')).toBeNull()
    expect(option('social_media')?.disabled).toBe(false)
    expect(option('ecommerce_product')?.disabled).toBe(false)
  })

  it('says reading starts on create', () => {
    renderForm()
    expect(screen.getByText(/starts as soon as you create the analysis/i)).toBeInTheDocument()
  })

  it('stays on page 1 and marks the empty fields when Next is pressed too early', async () => {
    renderForm()
    expect(screen.getByText(/page 1 of 2/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /^next$/i }))
    await waitFor(() => {
      expect(screen.getByLabelText(/^page name/i)).toHaveAttribute('aria-invalid', 'true')
    })
    expect(screen.getByText(/page 1 of 2/i)).toBeInTheDocument()
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
