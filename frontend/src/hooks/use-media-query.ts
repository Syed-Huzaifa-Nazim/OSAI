import { useEffect, useState } from 'react'

/** Subscribes to a media query. Returns false during SSR/first paint. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window === 'undefined' ? false : window.matchMedia(query).matches,
  )

  useEffect(() => {
    const list = window.matchMedia(query)
    const handler = (event: MediaQueryListEvent): void => {
      setMatches(event.matches)
    }
    setMatches(list.matches)
    list.addEventListener('change', handler)
    return () => {
      list.removeEventListener('change', handler)
    }
  }, [query])

  return matches
}

/** Tailwind breakpoint helpers, so magic strings live in one place. */
export const useIsDesktop = (): boolean => useMediaQuery('(min-width: 1024px)')
export const useIsMobile = (): boolean => useMediaQuery('(max-width: 767px)')
