import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { MailCheck, Send } from 'lucide-react'
import { AuthShell } from '@/components/layout/auth-shell'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/ui/form-field'
import { forgotPasswordSchema, type ForgotPasswordValues } from '@/lib/validation'
import { useAuthStore, usingMockAuth } from '@/stores/auth-store'
import { useDocumentTitle } from '@/hooks/use-document-title'

export default function ForgotPasswordPage() {
  useDocumentTitle('Reset your password')
  const requestReset = useAuthStore((state) => state.requestPasswordReset)
  const [sent, setSent] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  })

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await requestReset(values.email)
      // Shown regardless of whether the address exists. Confirming which
      // emails are registered would leak the user list.
      setSent(true)
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Could not send the reset email.')
    }
  })

  if (sent) {
    return (
      <AuthShell
        title="Check your inbox"
        subtitle={`If an account exists for ${getValues('email')}, a reset link is on its way.`}
        footer={
          <p>
            <Link to="/login" className="text-primary hover:underline">
              Back to log in
            </Link>
          </p>
        }
      >
        <div className="flex items-start gap-3 rounded-md border border-border/25 bg-muted/40 p-4">
          <MailCheck className="mt-0.5 size-5 shrink-0 text-primary" />
          <p className="text-sm text-muted-foreground">
            The link expires in one hour. If it does not arrive, check your spam folder before
            requesting another.
            {usingMockAuth
              ? ' Supabase is not configured in this environment, so no email was actually sent.'
              : ''}
          </p>
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell
      title="Reset your password"
      subtitle="We will email you a link to set a new one."
      footer={
        <p>
          Remembered it?{' '}
          <Link to="/login" className="text-primary hover:underline">
            Back to log in
          </Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        {formError ? (
          <p
            role="alert"
            className="rounded-md border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive"
          >
            {formError}
          </p>
        ) : null}

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

        <Button type="submit" className="w-full" loading={isSubmitting}>
          {isSubmitting ? 'Sending…' : 'Send reset link'}
          {isSubmitting ? null : <Send />}
        </Button>
      </form>
    </AuthShell>
  )
}
