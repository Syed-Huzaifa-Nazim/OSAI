import { act, lazy } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { RequireAuth } from '@/app/route-guards'
import { useAuthStore } from '@/stores/auth-store'

describe('protected lazy routes', () => {
  it('returns to login if the session ends while the admin page loads', async () => {
    let finishLoading: ((page: { default: () => JSX.Element }) => void) | undefined
    const AdminPage = lazy(
      () =>
        new Promise<{ default: () => JSX.Element }>((resolve) => {
          finishLoading = resolve
        }),
    )
    useAuthStore.setState({
      initialising: false,
      user: {
        id: 'admin-id',
        email: 'admin@example.com',
        fullName: null,
        avatarUrl: null,
        createdAt: '2026-01-01T00:00:00Z',
      },
    })

    const router = createMemoryRouter(
      [
        {
          element: <RequireAuth />,
          children: [{ path: '/admin/*', element: <AdminPage /> }],
        },
        { path: '/login', element: <h1>Log in</h1> },
      ],
      { initialEntries: ['/admin'] },
    )
    render(<RouterProvider router={router} />)

    expect(screen.getByRole('status')).toHaveTextContent('Checking your session')

    act(() => useAuthStore.setState({ user: null }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Log in' })).toBeInTheDocument())

    await act(async () => {
      finishLoading?.({ default: () => <h1>Admin portal</h1> })
    })
    expect(screen.queryByRole('heading', { name: 'Admin portal' })).not.toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
  })
})
