import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UsersManagement } from '@/pages/admin/users-management'

const get = vi.fn()
const post = vi.fn()
vi.mock('@/lib/api-client', () => ({
  api: { get: (...args: unknown[]) => get(...args), post: (...args: unknown[]) => post(...args) },
  errorMessage: (error: Error) => error.message,
}))

const row = { id: 'u1', email: 'person@example.com', verified: true, is_admin: false, created_at: '2026-01-01', wallet: { balance: 3, reserved: 0 } }
const detail = { ...row, full_name: 'Test Person', ledger: [], runs: [], requests: [], projects: [] }

function RoutedUsers() {
  const { detailId } = useParams()
  return <UsersManagement detailId={detailId} />
}

beforeEach(() => {
  get.mockReset()
  post.mockReset()
  get.mockImplementation(async (path: string) => {
    if (path.includes('/emails')) return []
    if (path === '/admin/users/u1') return detail
    return [row]
  })
  post.mockResolvedValue({ id: 'u2', email_status: 'pending_provider' })
})

describe('admin users page', () => {
  it('opens details in a dialog with overview, activity, and email tabs', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/admin/users']}><Routes>
      <Route path="/admin/users" element={<RoutedUsers />} />
      <Route path="/admin/users/:detailId" element={<RoutedUsers />} />
    </Routes></MemoryRouter>)
    await user.click(await screen.findByRole('link', { name: 'Open →' }))
    expect(await screen.findByRole('dialog', { name: /user details/i })).toBeInTheDocument()
    expect(screen.getByText('Test Person')).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Activity' }))
    expect(screen.getByRole('heading', { name: /projects/i })).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Email' }))
    expect(screen.getByText(/none are sent until GCP/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save to outbox' })).toBeDisabled()
  })

  it('creates an unverified user and reports that email delivery is pending', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter><UsersManagement /></MemoryRouter>)
    await screen.findByText('person@example.com')
    await user.type(screen.getByLabelText('Full name'), 'New Person')
    await user.type(screen.getByLabelText('Email'), 'new@example.com')
    await user.click(screen.getByRole('button', { name: 'Create user' }))
    await waitFor(() => expect(post).toHaveBeenCalledWith('/admin/users', {
      email: 'new@example.com', full_name: 'New Person', verified: false,
    }))
    expect(screen.getByRole('status')).toHaveTextContent(/delivery waits for GCP/i)
  })
})
