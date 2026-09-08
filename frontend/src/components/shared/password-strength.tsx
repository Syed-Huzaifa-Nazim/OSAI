import { cn } from '@/lib/utils'

const RULES = [
  { label: '8+ characters', test: (value: string) => value.length >= 8 },
  { label: 'Lowercase', test: (value: string) => /[a-z]/.test(value) },
  { label: 'Uppercase', test: (value: string) => /[A-Z]/.test(value) },
  { label: 'Number', test: (value: string) => /[0-9]/.test(value) },
]

/**
 * Shows which password rules are met as they are met, so the requirements are
 * not a surprise revealed only on submit.
 */
export function PasswordStrength({ value }: { value: string }) {
  if (!value) return null
  const met = RULES.filter((rule) => rule.test(value)).length

  return (
    <div className="space-y-2">
      <div className="flex gap-1" aria-hidden="true">
        {RULES.map((rule, index) => (
          <span
            key={rule.label}
            className={cn(
              'h-1 flex-1 rounded-full transition-colors',
              index < met
                ? met === RULES.length
                  ? 'bg-success'
                  : 'bg-primary'
                : 'bg-muted',
            )}
          />
        ))}
      </div>
      <ul className="flex flex-wrap gap-x-3 gap-y-1">
        {RULES.map((rule) => {
          const passed = rule.test(value)
          return (
            <li
              key={rule.label}
              className={cn('text-[11px]', passed ? 'text-success' : 'text-muted-foreground')}
            >
              {passed ? '✓' : '·'} {rule.label}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
