import { create } from 'zustand'
import { supabase } from '@/lib/supabase'
import { hasSupabase } from '@/lib/config'
import type { AuthUser } from '@/types/domain'
import { DEMO_USER_ID } from '@/lib/mock/demo-data'

interface AuthStore {
  user: AuthUser | null
  /** True until the initial session lookup settles, gates the route guards. */
  initialising: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, fullName: string) => Promise<void>
  signOut: () => Promise<void>
  requestPasswordReset: (email: string) => Promise<void>
  updatePassword: (password: string) => Promise<void>
  updateProfile: (patch: { fullName?: string; avatarUrl?: string }) => Promise<void>
  initialise: () => Promise<void>
}

/**
 * Errors thrown here carry a message safe to show the user. Supabase's own
 * messages are already human-readable; anything unexpected gets a fallback.
 */
function authError(error: { message?: string } | null, fallback: string): Error {
  return new Error(error?.message ?? fallback)
}

/** Demo identity used when Supabase is not configured. */
const DEMO_USER: AuthUser = {
  id: DEMO_USER_ID,
  email: 'demo@optistratix.ai',
  fullName: 'Demo Reviewer',
  avatarUrl: null,
  createdAt: new Date().toISOString(),
}

const DEMO_SESSION_KEY = 'optistratix-demo-session'
let authSubscription: { unsubscribe: () => void } | null = null

export const useAuthStore = create<AuthStore>()((set, get) => ({
  user: null,
  initialising: true,

  initialise: async () => {
    // No Supabase project configured: fall back to a local demo session so the
    // app is fully walkable on a fresh clone. Documented in docs/security.md.
    if (!supabase) {
      const active = localStorage.getItem(DEMO_SESSION_KEY) === 'true'
      set({ user: active ? DEMO_USER : null, initialising: false })
      return
    }

    let user: AuthUser | null = null
    try {
      const { data, error } = await supabase.auth.getSession()
      if (error) throw error
      if (data.session) {
        // A cached session alone does not prove that the current project
        // accepts it. This also catches revoked and migrated sessions.
        const verified = await supabase.auth.getUser()
        if (verified.error || !verified.data.user) throw verified.error ?? new Error('Invalid session')
        user = toAuthUser(verified.data.user)
      }
    } catch {
      // Invalid sessions should take the visitor to login, not leave a stale
      // bearer token making every API request fail with 401.
      try {
        await supabase.auth.signOut({ scope: 'local' })
      } catch {
        // The login screen remains usable if Auth is temporarily unavailable.
      }
    }

    set({ user, initialising: false })

    // App runs in React StrictMode, which calls initialise twice in dev.
    authSubscription?.unsubscribe()
    authSubscription = supabase.auth.onAuthStateChange((_event, session) => {
      set({ user: session ? toAuthUser(session.user) : null })
    }).data.subscription
  },

  signIn: async (email, password) => {
    if (!supabase) {
      localStorage.setItem(DEMO_SESSION_KEY, 'true')
      set({ user: DEMO_USER })
      return
    }
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw authError(error, 'Could not sign you in. Check your details and try again.')
  },

  signUp: async (email, password, fullName) => {
    if (!supabase) {
      localStorage.setItem(DEMO_SESSION_KEY, 'true')
      set({ user: { ...DEMO_USER, email, fullName } })
      return
    }
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    })
    if (error) throw authError(error, 'Could not create your account. Please try again.')
  },

  signOut: async () => {
    if (!supabase) {
      localStorage.removeItem(DEMO_SESSION_KEY)
      set({ user: null })
      return
    }
    const { error } = await supabase.auth.signOut()
    if (error) throw authError(error, 'Could not sign you out.')
    set({ user: null })
  },

  requestPasswordReset: async (email) => {
    if (!supabase) return
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    if (error) throw authError(error, 'Could not send the reset email.')
  },

  updatePassword: async (password) => {
    if (!supabase) return
    const { error } = await supabase.auth.updateUser({ password })
    if (error) throw authError(error, 'Could not update your password.')
  },

  updateProfile: async (patch) => {
    const current = get().user
    if (!current) throw new Error('You are not signed in.')

    if (!supabase) {
      set({ user: { ...current, fullName: patch.fullName ?? current.fullName } })
      return
    }
    const { error } = await supabase.auth.updateUser({
      data: { full_name: patch.fullName, avatar_url: patch.avatarUrl },
    })
    if (error) throw authError(error, 'Could not update your profile.')
    set({
      user: {
        ...current,
        fullName: patch.fullName ?? current.fullName,
        avatarUrl: patch.avatarUrl ?? current.avatarUrl,
      },
    })
  },
}))

interface SupabaseUserLike {
  id: string
  email?: string | undefined
  created_at: string
  user_metadata?: Record<string, unknown> | undefined
}

function toAuthUser(user: SupabaseUserLike): AuthUser {
  const metadata = user.user_metadata ?? {}
  return {
    id: user.id,
    email: user.email ?? '',
    fullName: typeof metadata.full_name === 'string' ? metadata.full_name : null,
    avatarUrl: typeof metadata.avatar_url === 'string' ? metadata.avatar_url : null,
    createdAt: user.created_at,
  }
}

/** True when the app is running without a real auth backend. */
export const usingMockAuth = !hasSupabase
