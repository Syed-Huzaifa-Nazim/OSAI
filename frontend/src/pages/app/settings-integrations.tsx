import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { Boxes, Check, Plug, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/shared/page-header'
import { ErrorState, LoadingCards } from '@/components/shared/state-views'
import { integrationsApi } from '@/lib/api/services'
import { queryKeys } from '@/lib/query-client'
import { errorMessage } from '@/lib/api-client'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { FEATURES } from '@/features/registry'
import { formatDate } from '@/lib/utils'
import { staggerContainer, staggerItem } from '@/lib/motion'
import type { Integration } from '@/types/domain'

/**
 * The slot where teammates' separately-built feature repos get connected.
 * Rows come from the backend `integrations` table; the registered-features
 * panel below reflects what is actually mounted in this build.
 */
export default function IntegrationsSettingsPage() {
  useDocumentTitle('Integrations')
  const client = useQueryClient()

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: queryKeys.integrations,
    queryFn: integrationsApi.list,
  })

  const toggle = useMutation({
    mutationFn: (id: string) => integrationsApi.toggle(id),
    onSuccess: async (integration: Integration) => {
      await client.invalidateQueries({ queryKey: queryKeys.integrations })
      toast.success(
        integration.status === 'connected'
          ? `${integration.name} connected`
          : `${integration.name} disconnected`,
      )
    },
    onError: (mutationError) => {
      toast.error('Could not change that connection', {
        description: errorMessage(mutationError),
      })
    },
  })

  return (
    <div className="mx-auto max-w-3xl space-y-7">
      <PageHeader
        eyebrow="Settings"
        title="Integrations"
        description="Modules built separately by the team, connected into this app."
      />

      {isError ? (
        <ErrorState
          message={errorMessage(error)}
          onRetry={() => {
            void refetch()
          }}
        />
      ) : isLoading ? (
        <LoadingCards count={3} />
      ) : (
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="space-y-4"
        >
          {(data ?? []).map((integration) => (
            <motion.div key={integration.id} variants={staggerItem}>
              <Card className="flex flex-wrap items-start gap-4 p-5">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/12 text-primary">
                  <Plug className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-display text-base font-semibold">{integration.name}</h2>
                    {integration.status === 'connected' ? (
                      <Badge variant="success">
                        <Check />
                        Connected
                      </Badge>
                    ) : integration.status === 'coming_soon' ? (
                      <Badge variant="muted">Not available yet</Badge>
                    ) : (
                      <Badge variant="outline">Available</Badge>
                    )}
                  </div>
                  <p className="mt-1.5 text-sm text-muted-foreground">{integration.description}</p>
                  <p className="mt-2 font-mono text-xs text-muted-foreground/70">
                    feature_key: {integration.featureKey}
                  </p>
                  {integration.connectedAt ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Connected {formatDate(integration.connectedAt)}
                    </p>
                  ) : null}
                </div>
                <Button
                  variant={integration.status === 'connected' ? 'outline' : 'default'}
                  disabled={integration.status === 'coming_soon'}
                  loading={toggle.isPending && toggle.variables === integration.id}
                  onClick={() => {
                    toggle.mutate(integration.id)
                  }}
                >
                  {integration.status === 'connected' ? 'Disconnect' : 'Connect'}
                </Button>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}

      <Card className="p-6">
        <div className="flex items-start gap-3">
          <Boxes className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-base font-semibold">Registered feature modules</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              What is actually mounted in this build, read from{' '}
              <code className="font-mono text-xs">src/features/registry.ts</code>.
            </p>

            {FEATURES.length === 0 ? (
              <div className="mt-4 rounded-md border border-dashed border-border/30 p-5 text-center">
                <Plus className="mx-auto size-5 text-muted-foreground/60" />
                <p className="mt-2 text-sm font-medium">No feature modules registered yet</p>
                <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
                  Drop a module into <code className="font-mono">src/features/</code>, export a
                  manifest, and add one line to the registry. The router and sidebar pick it up
                  automatically. See docs/architecture.md.
                </p>
              </div>
            ) : (
              <ul className="mt-4 space-y-2">
                {FEATURES.map((feature) => (
                  <li
                    key={feature.key}
                    className="flex items-center justify-between gap-3 rounded-md border border-border/20 p-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{feature.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {feature.routes.length} route{feature.routes.length === 1 ? '' : 's'} ·
                        owner: {feature.owner}
                      </p>
                    </div>
                    <Badge variant={feature.enabled ? 'success' : 'muted'}>
                      {feature.enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
