import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '@/stores/auth-store'

function AuthPending() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background" role="status">
      <Loader2 className="size-5 animate-spin text-primary" />
      <span className="sr-only">Checking your session</span>
    </div>
  )
}

/**
 * Gate for /app/*. Unauthenticated visitors are sent to /login with the
 * destination preserved, so they land where they were headed after signing in.
 */
export function RequireAuth() {
  const user = useAuthStore((state) => state.user)
  const initialising = useAuthStore((state) => state.initialising)
  const location = useLocation()

  if (initialising) return <AuthPending />
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

/** Signed-in users have no business on /login or /signup. */
export function RedirectIfAuthenticated() {
  const user = useAuthStore((state) => state.user)
  const initialising = useAuthStore((state) => state.initialising)

  if (initialising) return <AuthPending />
  if (user) return <Navigate to="/app/dashboard" replace />
  return <Outlet />
}
