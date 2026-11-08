import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { config } from '@/lib/config'

export type MarketingNavVariant = 'top' | 'vertical'

interface UiStore {
  /** Desktop sidebar: expanded with labels, or icon-only rail. */
  sidebarExpanded: boolean
  /** Mobile off-canvas drawer. Never persisted. */
  mobileNavOpen: boolean
  /**
   * Which public-site navigation to render. Both patterns are built; this lets
   * you compare them side by side without a rebuild. Defaults to the env var.
   */
  marketingNav: MarketingNavVariant
  toggleSidebar: () => void
  setSidebarExpanded: (expanded: boolean) => void
  setMobileNavOpen: (open: boolean) => void
  setMarketingNav: (variant: MarketingNavVariant) => void
}

export const useUiStore = create<UiStore>()(
  persist(
    (set, get) => ({
      sidebarExpanded: true,
      mobileNavOpen: false,
      marketingNav: config.marketingNav,
      toggleSidebar: () => {
        set({ sidebarExpanded: !get().sidebarExpanded })
      },
      setSidebarExpanded: (sidebarExpanded) => {
        set({ sidebarExpanded })
      },
      setMobileNavOpen: (mobileNavOpen) => {
        set({ mobileNavOpen })
      },
      setMarketingNav: (marketingNav) => {
        set({ marketingNav })
      },
    }),
    {
      name: 'optistratix-ui',
      partialize: (state) =>
        ({
          sidebarExpanded: state.sidebarExpanded,
          marketingNav: state.marketingNav,
        }) as UiStore,
    },
  ),
)
