import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'
import { MarketingShell } from '@/components/layout/marketing-shell'
import { useUiStore } from '@/stores/ui-store'

/**
 * The mobile drawer must leave the DOM when it closes.
 *
 * It used to close visually and stay mounted: the exit animation ran, but
 * AnimatePresence's removal was lost inside the router navigation that the
 * same tap started. The drawer sat at translateX(-100%) with eleven focusable
 * links still in the tab order, invisible to sighted users, fully present to
 * a screen reader or a keyboard.
 *
 * "Not visible" is not the assertion that matters here; "not in the document"
 * is.
 */
function renderShell(initialPath = '/') {
  useUiStore.setState({ marketingNav: 'vertical', mobileNavOpen: false })

  const router = createMemoryRouter(
    [
      {
        element: <MarketingShell />,
        children: [
          { path: '/', element: <h1>Home page</h1> },
          { path: '/pricing', element: <h1>Pricing page</h1> },
          { path: '/about', element: <h1>About page</h1> },
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

const drawer = () => screen.queryByRole('dialog', { name: /navigation/i })

describe('marketing mobile drawer', () => {
  beforeEach(() => {
    useUiStore.setState({ mobileNavOpen: false })
  })

  it('is absent until opened', () => {
    renderShell()
    expect(drawer()).not.toBeInTheDocument()
  })

  it('opens from the menu button', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByLabelText('Open navigation'))
    await waitFor(() => {
      expect(drawer()).toBeInTheDocument()
    })
  })

  it('leaves the DOM after the close button', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByLabelText('Open navigation'))
    await waitFor(() => expect(drawer()).toBeInTheDocument())

    await user.click(screen.getByLabelText('Close menu'))
    await waitFor(() => {
      expect(drawer()).not.toBeInTheDocument()
    })
  })

  it('leaves the DOM after navigating from inside it', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByLabelText('Open navigation'))
    await waitFor(() => expect(drawer()).toBeInTheDocument())

    const links = screen.getAllByRole('link', { name: /pricing/i })
    await user.click(links[links.length - 1]!)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Pricing page' })).toBeInTheDocument()
    })
    // The navigation must not leave the dialog behind.
    await waitFor(() => {
      expect(drawer()).not.toBeInTheDocument()
    })
  })

  it('leaves no focusable links behind after closing', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByLabelText('Open navigation'))
    await waitFor(() => expect(drawer()).toBeInTheDocument())

    const links = screen.getAllByRole('link', { name: /about/i })
    await user.click(links[links.length - 1]!)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'About page' })).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(document.querySelectorAll('[role="dialog"] a')).toHaveLength(0)
    })
  })
})
