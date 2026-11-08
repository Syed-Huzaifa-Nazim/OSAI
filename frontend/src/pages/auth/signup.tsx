import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { ArrowRight } from 'lucide-react'
import { AuthShell } from '@/components/layout/auth-shell'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { FormField } from '@/components/ui/form-field'
import { PasswordInput } from '@/components/shared/password-input'
import { PasswordStrength } from '@/components/shared/password-strength'
import { signupSchema, type SignupValues } from '@/lib/validation'
import { useAuthStore, usingMockAuth } from '@/stores/auth-store'
import { useDocumentTitle } from '@/hooks/use-document-title'

export default function SignupPage() {
  useDocumentTitle('Create an account')
  const signUp = useAuthStore((state) => state.signUp)
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<SignupValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      fullName: '',
      email: '',
      password: '',
      confirmPassword: '',
      acceptTerms: false as unknown as true,
    },
  })

  const password = watch('password')
  const acceptTerms = watch('acceptTerms')

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await signUp(values.email, values.password, values.fullName)
      toast.success('Account created', {
        description: usingMockAuth
          ? 'Running on a local demo session.'
          : 'Check your inbox to confirm your email address.',
      })
      navigate('/app/dashboard', { replace: true })
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Could not create your account.')
    }
  })

  return (
    <AuthShell
      title="Create your account"
      subtitle="Run your first competitor analysis in a few minutes."
      footer={
        <p>
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:underline">
            Log in
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

        <FormField label="Full name" htmlFor="fullName" error={errors.fullName?.message} required>
          <Input
            id="fullName"
            autoComplete="name"
            placeholder="Ada Lovelace"
            aria-invalid={Boolean(errors.fullName)}
            {...register('fullName')}
          />
        </FormField>

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

        <FormField label="Password" htmlFor="password" error={errors.password?.message} required>
          <PasswordInput
            id="password"
            autoComplete="new-password"
            placeholder="At least 8 characters"
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
            placeholder="Type it again"
            aria-invalid={Boolean(errors.confirmPassword)}
            {...register('confirmPassword')}
          />
        </FormField>

        <div className="space-y-2">
          <div className="flex items-start gap-2.5">
            <Checkbox
              id="acceptTerms"
              checked={Boolean(acceptTerms)}
              onCheckedChange={(checked) => {
                setValue('acceptTerms', (checked === true) as true, { shouldValidate: true })
              }}
              aria-invalid={Boolean(errors.acceptTerms)}
            />
            <Label htmlFor="acceptTerms" className="text-sm font-normal leading-snug">
              I agree to the terms of service and privacy policy.
            </Label>
          </div>
          {errors.acceptTerms ? (
            <p role="alert" className="text-xs text-destructive">
              {errors.acceptTerms.message}
            </p>
          ) : null}
        </div>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          {isSubmitting ? 'Creating your account…' : 'Create account'}
          {isSubmitting ? null : <ArrowRight />}
        </Button>
      </form>
    </AuthShell>
  )
}
