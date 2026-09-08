import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeStore {
  mode: ThemeMode
  /** The mode actually applied to the document, 'system' resolved. */
  resolved: 'light' | 'dark'
  setMode: (mode: ThemeMode) => void
  toggle: () => void
}

function resolveMode(mode: ThemeMode): 'light' | 'dark' {
  if (mode !== 'system') return mode
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

function applyToDocument(mode: ThemeMode): 'light' | 'dark' {
  const resolved = resolveMode(mode)
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', resolved)
  }
  return resolved
}

/**
 * Theme lives in localStorage under `optistratix-theme`. The inline script in
 * index.html reads the same key before first paint, so there is no flash.
 */
export const useThemeStore = create<ThemeStore>()(
  persist(
    (set, get) => ({
      mode: 'dark',
      resolved: 'dark',
      setMode: (mode) => {
        set({ mode, resolved: applyToDocument(mode) })
      },
      toggle: () => {
        const next = get().resolved === 'dark' ? 'light' : 'dark'
        set({ mode: next, resolved: applyToDocument(next) })
      },
    }),
    {
      name: 'optistratix-theme',
      partialize: (state) => ({ mode: state.mode }) as ThemeStore,
      onRehydrateStorage: () => (state) => {
        if (state) state.resolved = applyToDocument(state.mode)
      },
    },
  ),
)

/** Keeps 'system' in sync when the OS preference changes mid-session. */
export function watchSystemTheme(): () => void {
  if (typeof window === 'undefined') return () => {}
  const query = window.matchMedia('(prefers-color-scheme: light)')
  const handler = (): void => {
    const { mode } = useThemeStore.getState()
    if (mode === 'system') {
      useThemeStore.setState({ resolved: applyToDocument('system') })
    }
  }
  query.addEventListener('change', handler)
  return () => {
    query.removeEventListener('change', handler)
  }
}
