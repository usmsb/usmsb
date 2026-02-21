import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import ToastContainer from './Toast'
import { useAppStore } from '@/store'
import { HelpPanel } from './ui/HelpSystem'

export default function Layout() {
  const { sidebarOpen, applyTheme, theme } = useAppStore()
  const [helpOpen, setHelpOpen] = useState(false)

  // Apply theme on mount
  useEffect(() => {
    applyTheme()
  }, [applyTheme])

  // Listen for help button click from Header
  useEffect(() => {
    const handleOpenHelp = () => setHelpOpen(true)
    window.addEventListener('open-help-center', handleOpenHelp)
    return () => window.removeEventListener('open-help-center', handleOpenHelp)
  }, [])

  return (
    <div className={`
      h-screen flex overflow-hidden relative
      /* Light Mode: Clean light background */
      bg-secondary-50
      /* Dark Mode: Cyberpunk dark background */
      dark:bg-cyber-dark
    `}>
      {/* Cyberpunk Background Effects - Dark Mode Only */}
      {theme === 'dark' && (
        <>
          {/* Grid Background */}
          <div className="cyber-bg" />
          {/* Scan Line Effect */}
          <div className="scanline" />
        </>
      )}

      {/* Skip to main content link for keyboard users */}
      <a
        href="#main-content"
        className={`
          sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50
          focus:px-4 focus:py-2 focus:bg-primary-600 focus:text-white focus:rounded-lg focus:outline-none
          dark:focus:bg-neon-blue dark:focus:text-cyber-dark
        `}
      >
        Skip to main content
      </a>

      {/* Sidebar - hidden on mobile */}
      <div className="hidden md:block">
        <Sidebar />
      </div>

      {/* Main content */}
      <div
        className={`
          flex-1 flex flex-col overflow-hidden transition-all duration-300 relative z-10
          ml-0
          md:ml-20
          ${sidebarOpen ? 'md:ml-64' : ''}
        `}
      >
        <Header />
        <main
          id="main-content"
          className={`
            flex-1 overflow-hidden p-4 md:p-6
            /* Light Mode: Light gray background */
            bg-secondary-50
            /* Dark Mode: Transparent to show cyber background */
            dark:bg-transparent
          `}
          role="main"
        >
          <Outlet />
        </main>
      </div>
      <ToastContainer />
      <HelpPanel isOpen={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  )
}
