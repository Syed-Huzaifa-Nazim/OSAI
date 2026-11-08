import { lazy } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Link, RouterProvider, createMemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'
import { MarketingShell } from '@/components/layout/marketing-shell'

/**
 * A lazily-loaded route whose chunk takes real time to arrive.
 *
 * The router tests pass with the app's own lazy pages because Vitest resolves
 * those from the module cache in the same tick. The chunk is never actually
 * in flight. In a browser it is a network round trip, and that is the window in
 * which a page can mount into an animation, sit at `initial` (opacity 0), and
 * never be told to animate in. That was the blank screen.
 *
 * The delay here recreates that window so the shell's Suspense placement is
 * genuinely under test.
 */
function delayedPage(label: string, ms: number) {
  return lazy(
    () =>
      new Promise<{ default: () => JSX.Element }>((resolve) => {
        setTimeout(
          () =>
            resolve({
              default: () => <h1>{label}</h1>,
            }),
          ms,
        )
      }),
  )
}

const SlowPage = delayedPage('Slow page loaded', 120)
const OtherSlowPage = delayedPage('Other slow page loaded', 120)

function Home() {
  return (
    <div>
      <h1>Home</h1>
      <Link to="/slow">Go slow</Link>
      <Link to="/other">Go other</Link>
    </div>
  )
}

function renderShell(initialPath: string) {
  const router = createMemoryRouter(
    [
      {
        element: <MarketingShell />,
        children: [
          { path: '/', element: <Home /> },
          { path: '/slow', element: <SlowPage /> },
          { path: '/other', element: <OtherSlowPage /> },
        ],
      },
    ],
    { initialEntries: [initialPath] },
  )
  return render(
    <TooltipProvider>
      <RouterProvider router={router} />
    </TooltipProvider>,
  )
}

describe('MarketingShell with a genuinely async route', () => {
  it('shows the fallback, then the page, on a direct load', async () => {
    renderShell('/slow')

    expect(screen.getByRole('status')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Slow page loaded' })).toBeInTheDocument()
    })
  })

  it('reaches a slow page when navigated to, rather than going blank', async () => {
    const user = userEvent.setup()
    renderShell('/')

    expect(screen.getByRole('heading', { name: 'Home' })).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: 'Go slow' }))

    await waitFor(
      () => {
        expect(screen.getByRole('heading', { name: 'Slow page loaded' })).toBeInTheDocument()
      },
      { timeout: 3000 },
    )
  })

  it('reaches a second slow page after the first', async () => {
    const user = userEvent.setup()
    renderShell('/')

    await user.click(screen.getByRole('link', { name: 'Go other' }))
    await waitFor(
      () => {
        expect(
          screen.getByRole('heading', { name: 'Other slow page loaded' }),
        ).toBeInTheDocument()
      },
      { timeout: 3000 },
    )

    // The exit animation of one page overlapping the load of the next is
    // exactly where the blank screen came from.
    expect(screen.queryByRole('heading', { name: 'Home' })).not.toBeInTheDocument()
  })
})
