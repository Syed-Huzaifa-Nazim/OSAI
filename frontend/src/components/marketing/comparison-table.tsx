import { motion } from 'framer-motion'
import { Check, Minus } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { staggerContainer, staggerItem, viewportOnce } from '@/lib/motion'

interface Row {
  capability: string
  hootsuite: boolean
  buzzsumo: boolean
  note: string
}

/**
 * The gap table from the defence deck. Claims about the two named tools are
 * scoped to what the deck asserts (scheduling and analytics for Hootsuite,
 * trending content for BuzzSumo), rather than a broader feature audit.
 */
const ROWS: Row[] = [
  {
    capability: 'Schedules and analyses your own posts',
    hootsuite: true,
    buzzsumo: false,
    note: 'Table stakes. Not where the gap is.',
  },
  {
    capability: 'Surfaces trending content in your category',
    hootsuite: false,
    buzzsumo: true,
    note: 'Tells you what is popular, not what you should do.',
  },
  {
    capability: 'Compares your content directly against competitors',
    hootsuite: false,
    buzzsumo: false,
    note: 'True comparative analysis across landing pages and social.',
  },
  {
    capability: 'Converts findings into an executable strategy',
    hootsuite: false,
    buzzsumo: false,
    note: 'Strategist and Critic produce initiatives with action steps.',
  },
  {
    capability: 'Cites the source behind every claim',
    hootsuite: false,
    buzzsumo: false,
    note: 'Retrieval-grounded: each gap carries its evidence.',
  },
  {
    capability: 'Requires human sign-off before acting',
    hootsuite: false,
    buzzsumo: false,
    note: 'Two mandatory checkpoints in every run.',
  },
]

export function ComparisonTable() {
  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      whileInView="animate"
      viewport={viewportOnce}
    >
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-border/20">
                <th scope="col" className="p-4 font-medium">
                  Capability
                </th>
                <th scope="col" className="p-4 text-center font-medium text-muted-foreground">
                  Hootsuite
                </th>
                <th scope="col" className="p-4 text-center font-medium text-muted-foreground">
                  BuzzSumo
                </th>
                <th scope="col" className="p-4 text-center font-medium text-primary">
                  OptiStratixAI
                </th>
                <th scope="col" className="p-4 font-medium">
                  What that means
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <motion.tr
                  key={row.capability}
                  variants={staggerItem}
                  className="border-b border-border/10 last:border-0"
                >
                  <th scope="row" className="p-4 font-normal">
                    {row.capability}
                  </th>
                  <Mark yes={row.hootsuite} />
                  <Mark yes={row.buzzsumo} />
                  <Mark yes accent />
                  <td className="p-4 text-muted-foreground">{row.note}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </motion.div>
  )
}

function Mark({ yes, accent = false }: { yes: boolean; accent?: boolean }) {
  return (
    <td className="p-4">
      <span className="flex justify-center">
        <span
          className={cn(
            'flex size-6 items-center justify-center rounded-full',
            yes
              ? accent
                ? 'bg-primary/18 text-primary'
                : 'bg-success/15 text-success'
              : 'bg-muted text-muted-foreground/60',
          )}
        >
          {yes ? (
            <Check className="size-3.5" strokeWidth={3} />
          ) : (
            <Minus className="size-3.5" strokeWidth={3} />
          )}
          <span className="sr-only">{yes ? 'Supported' : 'Not supported'}</span>
        </span>
      </span>
    </td>
  )
}
