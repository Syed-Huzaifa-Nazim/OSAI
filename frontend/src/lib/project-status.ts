/** How a project's status is shown: a short label and its pill colours. */
export const PROJECT_STATUS: Record<string, { label: string; tone: string }> = {
  awaiting_review: { label: 'Awaiting review', tone: 'bg-primary/10 text-primary' },
  complete: { label: 'Completed', tone: 'bg-success/10 text-success' },
  running: { label: 'Running', tone: 'bg-warning/15 text-warning-ink' },
  draft: { label: 'Draft', tone: 'bg-muted text-muted-foreground' },
  failed: { label: 'Needs attention', tone: 'bg-destructive/10 text-destructive' },
  archived: { label: 'Archived', tone: 'bg-muted text-muted-foreground' },
}

export function projectStatus(status: string): { label: string; tone: string } {
  return PROJECT_STATUS[status] ?? PROJECT_STATUS.draft!
}
