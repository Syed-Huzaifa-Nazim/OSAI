import { useEffect } from 'react'

const SUFFIX = 'OptiStratixAI'

/** Sets the document title for a route and restores nothing on unmount, *  the next route sets its own. */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = title === SUFFIX ? SUFFIX : `${title} · ${SUFFIX}`
  }, [title])
}
