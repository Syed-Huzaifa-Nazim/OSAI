import { Toaster as SonnerToaster } from 'sonner'
import { useThemeStore } from '@/stores/theme-store'

/** Sonner, wired to the app theme and restyled with brand tokens. */
export function Toaster() {
  const resolved = useThemeStore((state) => state.resolved)
  return (
    <SonnerToaster
      theme={resolved}
      position="bottom-right"
      closeButton
      toastOptions={{
        classNames: {
          toast: 'glass-strong !rounded-lg !border-border/20 !text-foreground',
          title: '!font-display !font-semibold',
          description: '!text-muted-foreground',
          actionButton: '!bg-primary !text-primary-foreground',
          cancelButton: '!bg-muted !text-muted-foreground',
          error: '!border-destructive/40',
          success: '!border-success/40',
        },
      }}
    />
  )
}
