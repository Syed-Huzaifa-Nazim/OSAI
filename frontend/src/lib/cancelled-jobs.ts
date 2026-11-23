/**
 * Projects whose running job the user cancelled in this tab. The app-wide job watcher
 * (background-jobs.tsx) sees the project stop running and must not announce it as finished.
 */
const cancelled = new Set<string>()

export function markCancelled(projectId: string): void {
  cancelled.add(projectId)
}

/** True once for a cancelled project, then forgotten. */
export function takeCancelled(projectId: string): boolean {
  return cancelled.delete(projectId)
}
