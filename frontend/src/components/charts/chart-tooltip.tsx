import type { TooltipProps } from 'recharts'

type Payload = NonNullable<TooltipProps<number, string>['payload']>

interface ChartTooltipProps extends TooltipProps<number, string> {
  /** Formats the numeric value, e.g. as currency or a percentage. */
  format?: (value: number) => string
}

/**
 * Shared tooltip. Values wear text tokens, not the series colour. The swatch
 * beside them carries identity.
 */
export function ChartTooltip({ active, payload, label, format }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null

  const rows = payload as Payload

  return (
    <div className="glass-strong rounded-md px-3 py-2 text-xs">
      {label ? <p className="mb-1.5 font-medium text-foreground">{String(label)}</p> : null}
      <ul className="space-y-1">
        {rows.map((row, index) => (
          <li key={index} className="flex items-center gap-2">
            <span
              className="size-2 shrink-0 rounded-sm"
              style={{ backgroundColor: row.color ?? row.payload?.fill }}
              aria-hidden="true"
            />
            <span className="text-muted-foreground">{row.name}</span>
            <span className="ml-auto font-medium tabular-nums text-foreground">
              {format ? format(Number(row.value)) : String(row.value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
