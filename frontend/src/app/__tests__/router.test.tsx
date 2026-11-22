import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'
import { routes } from '@/app/router'
import { useAuthStore } from '@/stores/auth-store'

/**
 * Every public route has to actually render something.
 *
 * These exist because lazily-loaded routes fail *silently*, a page that never
 * resolves shows a blank screen, not an error, and neither the type checker nor
 * a unit test of the page component would notice.
 */
function renderAt(path: string) {
  // App.tsx normally settles this on mount; without it the route guards sit on
  // their "checking your session" spinner forever.
  useAuthStore.setState({ user: null, initialising: false })

  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <RouterProvider router={router} />
      </TooltipProvider>
    </QueryClientProvider>,
  )
}

const PUBLIC_ROUTES: { path: string; heading: RegExp }[] = [
  { path: '/', heading: /outsmart your competitors, wherever you sell/i },
  { path: '/how-it-works', heading: /six steps, from your link to your content/i },
  { path: '/features', heading: /six steps, and what each one does today/i },
  { path: '/about', heading: /built as a final year project/i },
  { path: '/contact', heading: /get in touch/i },
]

describe('public routes render', () => {
  it.each(PUBLIC_ROUTES)('$path shows its page', async ({ path, heading }) => {
    renderAt(path)

    await waitFor(
      () => {
        expect(screen.getByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
      },
      { timeout: 5000 },
    )
  })
})

describe('auth routes render', () => {
  it.each([
    { path: '/login', heading: /^log in$/i },
    { path: '/signup', heading: /create your account/i },
    { path: '/forgot-password', heading: /reset your password/i },
  ])('$path shows its page', async ({ path, heading }) => {
    renderAt(path)

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
    })
  })
})

describe('navigating between routes', () => {
  /**
   * Rendering a route directly is not the same as arriving at it by clicking.
   * A lazily-loaded page that mounts inside an exit animation can end up
   * present but invisible, which reads as a blank screen, and the direct-mount
   * tests above would all still pass.
   */
  it.each([
    { link: /how it works/i, heading: /six steps, from your link to your content/i },
    { link: /^features$/i, heading: /six steps, and what each one does today/i },
    { link: /^about$/i, heading: /built as a final year project/i },
  ])('clicking $link reaches the page', async ({ link, heading }) => {
    const user = userEvent.setup()
    renderAt('/')

    await screen.findByRole('heading', { level: 1, name: /outsmart your competitors, wherever you sell/i })

    const nav = screen.getByRole('navigation', { name: /main/i })
    await user.click(within(nav).getByRole('link', { name: link }))

    await waitFor(
      () => {
        expect(screen.getByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
      },
      { timeout: 5000 },
    )
  })
})

describe('unknown routes', () => {
  it('render the 404 page rather than a blank screen', async () => {
    renderAt('/no-such-page')

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { level: 1, name: /not on the map/i }),
      ).toBeInTheDocument()
    })
  })
})
