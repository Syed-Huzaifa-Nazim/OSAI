import { useId, useState, type ReactNode } from 'react'
import { Table2, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export interface ChartSeries {
  label: string
  color: string
}

interface ChartFrameProps {
  title: string
  description?: string
  /** Present whenever there are two or more series. Identity is never colour alone. */
  series?: ChartSeries[]
  /** The same numbers as a table, for screen readers and for anyone who would
   *  rather read the values. Always offered. */
  table: { columns: string[]; rows: (string | number)[][] }
  children: ReactNode
  className?: string
  height?: number
}

/**
 * Wraps every chart with its title, legend, and a table view of the same data.
 * The table is not a fallback. It is a peer view, and the toggle is visible.
 */
export function ChartFrame({
  title,
  description,
  series,
  table,
  children,
  className,
  height = 260,
}: ChartFrameProps) {
  const [view, setView] = useState<'chart' | 'table'>('chart')
  const titleId = useId()

  return (
    <Card className={cn('overflow-hidden', className)}>
      <div className="flex flex-wrap items-start justify-between gap-3 p-5 pb-3">
        <div className="min-w-0 space-y-1">
          <h3 id={titleId} className="font-display text-sm font-semibold">
            {title}
          </h3>
          {description ? (
            <p className="text-xs text-muted-foreground">{description}</p>
          ) : null}
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => {
            setView(view === 'chart' ? 'table' : 'chart')
          }}
          aria-label={view === 'chart' ? 'Show data as a table' : 'Show as a chart'}
        >
          {view === 'chart' ? <Table2 /> : <BarChart3 />}
        </Button>
      </div>

      {series && series.length > 1 ? (
        <ul className="flex flex-wrap gap-x-4 gap-y-1.5 px-5 pb-3">
          {series.map((item) => (
            <li key={item.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span
                className="size-2.5 rounded-sm"
                style={{ backgroundColor: item.color }}
                aria-hidden="true"
              />
              {item.label}
            </li>
          ))}
        </ul>
      ) : null}

      <div className="px-2 pb-4">
        {view === 'chart' ? (
          <div style={{ height }} aria-labelledby={titleId} role="img">
            {children}
          </div>
        ) : (
          <div className="max-h-[320px] overflow-auto px-3">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-card">
                <tr className="border-b border-border/20">
                  {table.columns.map((column) => (
                    <th key={column} className="py-2 pr-3 font-medium text-muted-foreground">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, index) => (
                  <tr key={index} className="border-b border-border/10 last:border-0">
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className={cn('py-2 pr-3', cellIndex > 0 && 'tabular-nums')}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Card>
  )
}
