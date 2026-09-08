import { Link } from 'react-router-dom'
import { CreditCard, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/shared/page-header'
import { useDocumentTitle } from '@/hooks/use-document-title'

/**
 * PLACEHOLDER. No billing provider is integrated and no payment is collected
 * anywhere in the application. This page exists so the settings area matches
 * the public pricing page, which is itself placeholder content.
 */
export default function BillingSettingsPage() {
  useDocumentTitle('Billing')

  return (
    <div className="mx-auto max-w-2xl space-y-7">
      <PageHeader
        eyebrow="Settings"
        title="Billing"
        description="Plan and payment details."
      />

      <Card className="flex items-start gap-3 border-brand-butter-cream/30 bg-brand-butter-cream/5 p-4">
        <Info className="mt-0.5 size-4 shrink-0 text-brand-butter-cream" />
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Placeholder page.</span> No billing provider
          is integrated, no card details are collected, and nothing here charges anyone. It mirrors
          the placeholder tiers on the public{' '}
          <Link to="/pricing" className="text-primary hover:underline">
            pricing page
          </Link>
          .
        </p>
      </Card>

      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-display text-base font-semibold">Current plan</h2>
              <Badge variant="outline">Pilot</Badge>
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground">
              One analysis per month, up to two competitors per run. All nine pipeline stages and
              both human checkpoints are included on every tier.
            </p>
          </div>
          <Button asChild variant="outline">
            <Link to="/pricing">Compare plans</Link>
          </Button>
        </div>
      </Card>

      <Card className="p-6">
        <div className="flex items-start gap-3">
          <CreditCard className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <div>
            <h2 className="font-display text-base font-semibold">Payment method</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              None on file. Adding a payment provider is out of scope for the current project
              phase.
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}
