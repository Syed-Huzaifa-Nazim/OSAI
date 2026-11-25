import { beforeEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({
  getSession: vi.fn(),
  getUser: vi.fn(),
  signOut: vi.fn(),
  onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
}))

vi.mock('@/lib/supabase', () => ({ supabase: { auth } }))

import { useAuthStore } from '@/stores/auth-store'

describe('auth initialisation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ user: null, initialising: true })
    auth.signOut.mockResolvedValue({ error: null })
  })

  it('discards a cached session rejected by the current Supabase project', async () => {
    auth.getSession.mockResolvedValue({ data: { session: { access_token: 'old-token' } }, error: null })
    auth.getUser.mockResolvedValue({ data: { user: null }, error: new Error('Invalid JWT') })

    await useAuthStore.getState().initialise()

    expect(useAuthStore.getState()).toMatchObject({ user: null, initialising: false })
    expect(auth.signOut).toHaveBeenCalledWith({ scope: 'local' })
  })

  it('accepts a session verified by the current project', async () => {
    auth.getSession.mockResolvedValue({ data: { session: { access_token: 'current-token' } }, error: null })
    auth.getUser.mockResolvedValue({
      data: {
        user: {
          id: 'user-id',
          email: 'user@example.com',
          created_at: '2026-01-01T00:00:00Z',
        },
      },
      error: null,
    })

    await useAuthStore.getState().initialise()

    expect(useAuthStore.getState()).toMatchObject({
      user: { id: 'user-id', email: 'user@example.com' },
      initialising: false,
    })
    expect(auth.signOut).not.toHaveBeenCalled()
  })
})
