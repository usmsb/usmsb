import { create } from 'zustand'

interface UIState {
  sidebarOpen: boolean
  mobileTabIndex: number
  toggleSidebar: () => void
  setSidebarOpen: (v: boolean) => void
  setMobileTabIndex: (i: number) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  mobileTabIndex: 0,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  setMobileTabIndex: (i) => set({ mobileTabIndex: i }),
}))
