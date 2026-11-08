import { LayoutPanelLeft, PanelTop } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useUiStore } from '@/stores/ui-store'
import { cn } from '@/lib/utils'

/**
 * Both marketing navigation patterns were built, so this floating control
 * switches between them live rather than making you rebuild to compare.
 *
 * It is a review aid, not a user-facing feature, remove it (and the
 * `marketingNav` field on the UI store) once a pattern is chosen.
 */
export function NavVariantSwitcher({ className }: { className?: string }) {
  const variant = useUiStore((state) => state.marketingNav)
  const setVariant = useUiStore((state) => state.setMarketingNav)

  return (
    <div
      className={cn(
        'glass-strong fixed bottom-5 right-5 z-50 flex items-center gap-1 rounded-full p-1.5',
        className,
      )}
    >
      <span className="px-2 text-[10px] uppercase tracking-wider text-muted-foreground">Nav</span>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant === 'top' ? 'default' : 'ghost'}
            size="icon-sm"
            className="rounded-full"
            onClick={() => {
              setVariant('top')
            }}
            aria-label="Use the top navbar"
            aria-pressed={variant === 'top'}
          >
            <PanelTop />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">Slim top navbar</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant === 'vertical' ? 'default' : 'ghost'}
            size="icon-sm"
            className="rounded-full"
            onClick={() => {
              setVariant('vertical')
            }}
            aria-label="Use the left vertical nav"
            aria-pressed={variant === 'vertical'}
          >
            <LayoutPanelLeft />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">Left vertical rail</TooltipContent>
      </Tooltip>
    </div>
  )
}
