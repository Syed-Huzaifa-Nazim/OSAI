import { Badge } from '@/components/ui/badge'
import type { ProjectStatus } from '@/types/domain'

const STATUS: Record<
  ProjectStatus,
  { label: string; variant: 'default' | 'secondary' | 'outline' | 'success' | 'destructive' | 'muted' }
> = {
  draft: { label: 'Draft', variant: 'muted' },
  running: { label: 'Running', variant: 'default' },
  awaiting_review: { label: 'Awaiting your review', variant: 'secondary' },
  complete: { label: 'Complete', variant: 'success' },
  failed: { label: 'Failed', variant: 'destructive' },
  archived: { label: 'Archived', variant: 'outline' },
}

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  const config = STATUS[status]
  return <Badge variant={config.variant}>{config.label}</Badge>
}
