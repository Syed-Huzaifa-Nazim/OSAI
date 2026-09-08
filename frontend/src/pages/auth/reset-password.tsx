import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Check } from 'lucide-react'
import { AuthShell } from '@/components/layout/auth-shell'
import { Button } from '@/components/ui/button'
import { FormField } from '@/components/ui/form-field'
import { PasswordInput } from '@/components/shared/password-input'
import { PasswordStrength } from '@/components/shared/password-strength'
import { resetPasswordSchema, type ResetPasswordValues } from '@/lib/validation'
import { useAuthStore } from '@/stores/auth-store'
import { useDocumentTitle } from '@/hooks/use-document-title'

/**
 * Reached from the emailed link. Supabase puts a recovery session in place
 * before this page renders, so `updateUser` is all that is needed here.
 */
export default function ResetPasswordPage() {
  useDocumentTitle('Set a new password')
  const updatePassword = useAuthStore((state) => state.updatePassword)
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '', confirmPassword: '' },
  })

  const password = watch('password')

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await updatePassword(values.password)
      toast.success('Password updated', { description: 'Use it next time you log in.' })
      navigate('/app/dashboard', { replace: true })
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Could not update your password.')
    }
  })

  return (
    <AuthShell title="Set a new password" subtitle="Choose something you have not used before.">
      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        {formError ? (
          <p
            role="alert"
            className="rounded-md border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive"
          >
            {formError}
          </p>
        ) : null}

        <FormField label="New password" htmlFor="password" error={errors.password?.message} required>
          <PasswordInput
            id="password"
            autoComplete="new-password"
            aria-invalid={Boolean(errors.password)}
            {...register('password')}
          />
          <PasswordStrength value={password} />
        </FormField>

        <FormField
          label="Confirm password"
          htmlFor="confirmPassword"
          error={errors.confirmPassword?.message}
          required
        >
          <PasswordInput
            id="confirmPassword"
            autoComplete="new-password"
            aria-invalid={Boolean(errors.confirmPassword)}
            {...register('confirmPassword')}
          />
        </FormField>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          {isSubmitting ? 'Updating…' : 'Update password'}
          {isSubmitting ? null : <Check />}
        </Button>
      </form>
    </AuthShell>
  )
}
