import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { LogIn } from 'lucide-react'
import { AuthShell } from '@/components/layout/auth-shell'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/ui/form-field'
import { PasswordInput } from '@/components/shared/password-input'
import { loginSchema, type LoginValues } from '@/lib/validation'
import { useAuthStore, usingMockAuth } from '@/stores/auth-store'
import { useDocumentTitle } from '@/hooks/use-document-title'

interface LocationState {
  from?: { pathname: string }
}

export default function LoginPage() {
  useDocumentTitle('Log in')
  const signIn = useAuthStore((state) => state.signIn)
  const navigate = useNavigate()
  const location = useLocation()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  // Send the user where they were originally headed, not always the dashboard.
  const destination = (location.state as LocationState | null)?.from?.pathname ?? '/app/dashboard'

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await signIn(values.email, values.password)
      toast.success('Welcome back')
      navigate(destination, { replace: true })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not sign you in.'
      // Supabase does not say which field was wrong, on purpose, so neither do we.
      setFormError(message)
      setError('password', { message: ' ' })
    }
  })

  return (
    <AuthShell
      title="Log in"
      subtitle="Pick up an analysis where you left it."
      footer={
        <p>
          No account yet?{' '}
          <Link to="/signup" className="text-primary hover:underline">
            Create one
          </Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        {usingMockAuth ? (
          <p className="rounded-md border border-border/25 bg-muted/40 p-3 text-xs text-muted-foreground">
            Supabase is not configured, so the app is running on a local demo session. Any email and
            password will sign you in.
          </p>
        ) : null}

        {formError ? (
          <p
            role="alert"
            className="rounded-md border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive"
          >
            {formError}
          </p>
        ) : null}

        <Button type="button" variant="outline" className="w-full justify-center gap-2">
          <span className="font-display text-base font-semibold text-primary">G</span>
          Continue with Google
        </Button>

        <div className="flex items-center gap-3 text-[11px] uppercase tracking-[0.18em] text-muted-foreground/70">
          <span className="h-px flex-1 bg-border/40" />
          or continue with email
          <span className="h-px flex-1 bg-border/40" />
        </div>

        <FormField label="Email" htmlFor="email" error={errors.email?.message} required>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            aria-invalid={Boolean(errors.email)}
            {...register('email')}
          />
        </FormField>

        <FormField
          label="Password"
          htmlFor="password"
          error={errors.password?.message?.trim() || undefined}
          required
        >
          <PasswordInput
            id="password"
            autoComplete="current-password"
            placeholder="Your password"
            aria-invalid={Boolean(errors.password)}
            {...register('password')}
          />
        </FormField>

        <div className="flex justify-end">
          <Link to="/forgot-password" className="text-xs text-muted-foreground hover:text-primary">
            Forgot your password?
          </Link>
        </div>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          {isSubmitting ? 'Signing you in…' : 'Log in'}
          {isSubmitting ? null : <LogIn />}
        </Button>
      </form>
    </AuthShell>
  )
}
