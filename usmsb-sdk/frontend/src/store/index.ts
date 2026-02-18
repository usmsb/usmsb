import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Agent, Environment } from '@/types'

export type ThemeMode = 'light' | 'dark' | 'system'

// Helper function to get system theme preference
const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'light'
}

// Helper function to get the effective theme
const getEffectiveTheme = (mode: ThemeMode): 'light' | 'dark' => {
  if (mode === 'system') {
    return getSystemTheme()
  }
  return mode
}

interface AppState {
  // UI State
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void

  // Selected items
  selectedAgent: Agent | null
  setSelectedAgent: (agent: Agent | null) => void

  selectedEnvironment: Environment | null
  setSelectedEnvironment: (env: Environment | null) => void

  // Notifications
  notifications: Notification[]
  addNotification: (notification: Omit<Notification, 'id'>) => void
  removeNotification: (id: string) => void

  // Theme
  themeMode: ThemeMode
  theme: 'light' | 'dark' // Effective theme (resolved from mode)
  setThemeMode: (mode: ThemeMode) => void
  toggleTheme: () => void
  applyTheme: () => void
}

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // UI State
      sidebarOpen: true,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      // Selected items
      selectedAgent: null,
      setSelectedAgent: (agent) => set({ selectedAgent: agent }),

      selectedEnvironment: null,
      setSelectedEnvironment: (env) => set({ selectedEnvironment: env }),

      // Notifications
      notifications: [],
      addNotification: (notification) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            { ...notification, id: Math.random().toString(36).substr(2, 9) },
          ],
        })),
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),

      // Theme
      themeMode: 'system',
      theme: getSystemTheme(),
      setThemeMode: (mode) => {
        const effectiveTheme = getEffectiveTheme(mode)
        set({ themeMode: mode, theme: effectiveTheme })
        // Apply theme to document
        if (effectiveTheme === 'dark') {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
      },
      toggleTheme: () => {
        const { theme } = get()
        const newTheme = theme === 'light' ? 'dark' : 'light'
        set({ themeMode: newTheme, theme: newTheme })
        // Apply theme to document
        if (newTheme === 'dark') {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
      },
      applyTheme: () => {
        const { themeMode } = get()
        const effectiveTheme = getEffectiveTheme(themeMode)
        set({ theme: effectiveTheme })
        if (effectiveTheme === 'dark') {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
      },
    }),
    {
      name: 'usmsb-app-storage',
      partialize: (state) => ({
        themeMode: state.themeMode,
        theme: state.theme,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
)

// Setup system theme change listener
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', () => {
    const state = useAppStore.getState()
    if (state.themeMode === 'system') {
      state.applyTheme()
    }
  })
}
