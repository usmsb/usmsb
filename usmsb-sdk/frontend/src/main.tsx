import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { WagmiProvider } from 'wagmi'
import { config } from './config/wagmi'
import App from './App'
import './i18n'
import './index.css'

// Initialize theme before React renders to prevent flash
const initTheme = () => {
  const stored = localStorage.getItem('usmsb-app-storage')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      const themeMode = parsed.state?.themeMode || 'system'
      const effectiveTheme = themeMode === 'system'
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : themeMode
      if (effectiveTheme === 'dark') {
        document.documentElement.classList.add('dark')
      }
    } catch {
      // Use system default
    }
  }
}
initTheme()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </WagmiProvider>
  </React.StrictMode>,
)
