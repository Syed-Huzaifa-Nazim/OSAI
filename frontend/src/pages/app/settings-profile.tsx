import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Check, Monitor, Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { FormField } from '@/components/ui/form-field'
import { PageHeader } from '@/components/shared/page-header'
import { useAuthStore } from '@/stores/auth-store'
import { useThemeStore, type ThemeMode } from '@/stores/theme-store'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { profileSchema, type ProfileValues } from '@/lib/validation'
import { cn, formatDate, initials } from '@/lib/utils'

const THEMES: { mode: ThemeMode; label: string; icon: typeof Sun; hint: string }[] = [
  { mode: 'light', label: 'Light', icon: Sun, hint: 'Soft vanilla canvas' },
  { mode: 'dark', label: 'Dark', icon: Moon, hint: 'Ink black canvas' },
  { mode: 'system', label: 'System', icon: Monitor, hint: 'Follows your OS' },
]

export default function ProfileSettingsPage() {
  useDocumentTitle('Profile')
  const user = useAuthStore((state) => state.user)
  const updateProfile = useAuthStore((state) => state.updateProfile)
  const themeMode = useThemeStore((state) => state.mode)
  const setThemeMode = useThemeStore((state) => state.setMode)
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { fullName: user?.fullName ?? '' },
  })

  // The auth store settles after first paint, so seed the form once it does.
  useEffect(() => {
    if (user) reset({ fullName: user.fullName ?? '' })
  }, [user, reset])

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await updateProfile({ fullName: values.fullName })
      toast.success('Profile updated')
      reset(values)
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Could not update your profile.')
    }
  })

  return (
    <div className="mx-auto max-w-2xl space-y-7">
      <PageHeader
        eyebrow="Settings"
        title="Profile"
        description="How you appear on the reviews you sign off."
      />

      <Card className="p-6">
        <div className="flex items-center gap-4">
          <Avatar className="size-14">
            <AvatarFallback className="text-base">
              {initials(user?.fullName ?? user?.email ?? '?')}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <p className="font-display text-base font-semibold">
              {user?.fullName ?? 'Unnamed reviewer'}
            </p>
            <p className="truncate text-sm text-muted-foreground">{user?.email}</p>
            {user ? (
              <p className="mt-0.5 text-xs text-muted-foreground">
                Member since {formatDate(user.createdAt)}
              </p>
            ) : null}
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="font-display text-base font-semibold">Your details</h2>
        <form onSubmit={onSubmit} className="mt-5 space-y-5" noValidate>
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
              aria-invalid={Boolean(errors.fullName)}
              {...register('fullName')}
            />
          </FormField>

          <FormField
            label="Email"
            htmlFor="profile-email"
            hint="Change this under Account"
          >
            <Input id="profile-email" value={user?.email ?? ''} readOnly disabled />
          </FormField>

          <Button type="submit" loading={isSubmitting} disabled={!isDirty}>
            {isSubmitting ? 'Saving…' : 'Save changes'}
            {isSubmitting ? null : <Check />}
          </Button>
        </form>
      </Card>

      <Card className="p-6">
        <h2 className="font-display text-base font-semibold">Appearance</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Both themes use the same five brand tokens; only their roles swap.
        </p>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          {THEMES.map((theme) => {
            const selected = themeMode === theme.mode
            return (
              <button
                key={theme.mode}
                type="button"
                onClick={() => {
                  setThemeMode(theme.mode)
                }}
                aria-pressed={selected}
                className={cn(
                  'rounded-lg border p-4 text-left transition-colors',
                  selected
                    ? 'border-primary/50 bg-primary/8'
                    : 'border-border/25 hover:border-border/50',
                )}
              >
                <theme.icon
                  className={cn('size-4', selected ? 'text-primary' : 'text-muted-foreground')}
                />
                <p className="mt-3 text-sm font-medium">{theme.label}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{theme.hint}</p>
              </button>
            )
          })}
        </div>
      </Card>
    </div>
  )
}
