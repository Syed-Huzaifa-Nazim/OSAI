import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { AlertTriangle, KeyRound, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/ui/form-field'
import { PasswordInput } from '@/components/shared/password-input'
import { PasswordStrength } from '@/components/shared/password-strength'
import { PageHeader } from '@/components/shared/page-header'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAuthStore, usingMockAuth } from '@/stores/auth-store'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { changePasswordSchema, type ChangePasswordValues } from '@/lib/validation'

export default function AccountSettingsPage() {
  useDocumentTitle('Account')
  const user = useAuthStore((state) => state.user)
  const updatePassword = useAuthStore((state) => state.updatePassword)
  const signOut = useAuthStore((state) => state.signOut)
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const [confirmSignOut, setConfirmSignOut] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { password: '', confirmPassword: '' },
  })

  const password = watch('password')

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await updatePassword(values.password)
      toast.success('Password updated')
      reset()
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Could not update your password.')
    }
  })

  return (
    <div className="mx-auto max-w-2xl space-y-7">
      <PageHeader
        eyebrow="Settings"
        title="Account"
        description="Sign-in details and session control."
      />

      <Card className="p-6">
        <h2 className="font-display text-base font-semibold">Email address</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Changing the email on an account requires confirming the new address. That flow is not
          wired up yet: it is tracked in the project status log.
        </p>
        <div className="mt-5">
          <FormField label="Current email" htmlFor="account-email">
            <Input id="account-email" value={user?.email ?? ''} readOnly disabled />
          </FormField>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="font-display text-base font-semibold">Change password</h2>
        {usingMockAuth ? (
          <p className="mt-3 rounded-md border border-border/25 bg-muted/40 p-3 text-xs text-muted-foreground">
            Supabase is not configured, so this form validates but does not persist anything.
          </p>
        ) : null}

        <form onSubmit={onSubmit} className="mt-5 space-y-5" noValidate>
          {formError ? (
            <p
              role="alert"
              className="rounded-md border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive"
            >
              {formError}
            </p>
          ) : null}

          <FormField
            label="New password"
            htmlFor="password"
            error={errors.password?.message}
            required
          >
            <PasswordInput
              id="password"
              autoComplete="new-password"
              aria-invalid={Boolean(errors.password)}
              {...register('password')}
            />
            <PasswordStrength value={password} />
          </FormField>

          <FormField
            label="Confirm new password"
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

          <Button type="submit" loading={isSubmitting}>
            {isSubmitting ? 'Updating…' : 'Update password'}
            {isSubmitting ? null : <KeyRound />}
          </Button>
        </form>
      </Card>

      <Card className="border-destructive/25 p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-base font-semibold">Sessions</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Signing out ends this session on this device. Analyses in progress keep running
              server-side and will be waiting when you return.
            </p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => {
                setConfirmSignOut(true)
              }}
            >
              <LogOut />
              Sign out
            </Button>
          </div>
        </div>
      </Card>

      <Dialog open={confirmSignOut} onOpenChange={setConfirmSignOut}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sign out?</DialogTitle>
            <DialogDescription>
              You will need to log in again to reach your analyses.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => {
                setConfirmSignOut(false)
              }}
            >
              Stay signed in
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                void signOut()
                  .then(() => {
                    navigate('/')
                    toast.success('Signed out')
                  })
                  .catch(() => {
                    toast.error('Could not sign you out')
                  })
              }}
            >
              Sign out
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
