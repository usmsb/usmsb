import { NavLink, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard,
  Users,
  FlaskConical,
  BarChart3,
  Store,
  Scale,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
  Network,
  GitBranch,
  PlusCircle,
  Target,
  Home,
  Bot,
} from 'lucide-react'
import { useAppStore } from '@/store'
import { useState } from 'react'

export default function Sidebar() {
  const { t } = useTranslation()
  const { sidebarOpen, setSidebarOpen, theme } = useAppStore()
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)

  const isDark = theme === 'dark'

  // Logo source based on theme
  const logoSrc = isDark ? '/logo-dark.svg' : '/logo.svg'

  const navigation = [
    { name: t('nav.dashboard'), href: '/app/dashboard', icon: LayoutDashboard, group: 'main' },
    { name: t('nav.agents'), href: '/app/agents', icon: Users, group: 'main' },
    { name: t('nav.metaAgent'), href: '/app/chat', icon: Bot, group: 'main' },
    { name: t('nav.matching'), href: '/app/matching', icon: Zap, group: 'main' },
    { name: t('nav.network'), href: '/app/network', icon: Network, group: 'main' },
    { name: t('nav.collaborations'), href: '/app/collaborations', icon: GitBranch, group: 'tools' },
    { name: t('nav.simulations'), href: '/app/simulations', icon: FlaskConical, group: 'tools' },
    { name: t('nav.analytics'), href: '/app/analytics', icon: BarChart3, group: 'tools' },
    { name: t('nav.marketplace'), href: '/app/marketplace', icon: Store, group: 'tools' },
    { name: t('nav.governance'), href: '/app/governance', icon: Scale, group: 'tools' },
  ]

  const quickActions = [
    { name: t('sidebar.publishService'), href: '/app/publish/service', icon: PlusCircle, desc: t('sidebar.publishServiceDesc'), color: 'blue' },
    { name: t('sidebar.publishDemand'), href: '/app/publish/demand', icon: Target, desc: t('sidebar.publishDemandDesc'), color: 'purple' },
  ]

  // Group navigation items
  const mainNav = navigation.filter(item => item.group === 'main')
  const toolsNav = navigation.filter(item => item.group === 'tools')

  return (
    <aside
      className={`
        fixed left-0 top-0 h-full transition-all duration-300 ease-out z-30
        flex flex-col
        /* ========================================
           LIGHT MODE - Clean Professional Style
           ======================================== */
        bg-white border-r border-secondary-200 shadow-sm
        /* ========================================
           DARK MODE - Cyberpunk Sci-Fi Style
           ======================================== */
        dark:bg-cyber-card/95 dark:backdrop-blur-xl dark:border-neon-blue/20
        ${sidebarOpen ? 'w-64' : 'w-20'}
      `}
    >
      {/* Dark mode neon border effect - Dark Mode Only */}
      {isDark && (
        <div className="absolute top-0 right-0 bottom-0 w-px bg-gradient-to-b from-transparent via-neon-blue/50 to-transparent pointer-events-none" />
      )}

      {/* ========================================
          LOGO SECTION
          ======================================== */}
      <div className={`
        h-16 flex items-center justify-between px-4 shrink-0
        border-b
        border-secondary-200
        dark:border-neon-blue/20
      `}>
        {sidebarOpen ? (
          <Link to="/" className="flex items-center gap-3 group">
            <div className={`relative ${isDark ? 'pulse-ring rounded-full' : ''}`}>
              <img
                src={logoSrc}
                alt="USMSB Logo"
                className={`
                  w-9 h-9 transition-all duration-300
                  group-hover:scale-110
                  dark:group-hover:shadow-[0_0_20px_var(--neon-blue)]
                `}
              />
            </div>
            <div className="flex flex-col">
              <span className={`
                font-bold text-lg leading-tight transition-colors
                text-secondary-900 group-hover:text-primary-600
                dark:text-transparent dark:bg-clip-text dark:bg-gradient-to-r
                dark:from-neon-blue dark:via-neon-purple dark:to-neon-green
                dark:font-cyber dark:group-hover:from-neon-green dark:group-hover:to-neon-blue
              `}>USMSB</span>
              <span className={`
                text-xs
                text-secondary-400
                dark:text-neon-blue/60 dark:font-cyber
              `}>SDK Platform</span>
            </div>
          </Link>
        ) : (
          <Link to="/" className="flex items-center justify-center w-full group">
            <div className={`relative ${isDark ? 'pulse-ring rounded-full' : ''}`}>
              <img
                src={logoSrc}
                alt="USMSB Logo"
                className={`
                  w-9 h-9 transition-all duration-300
                  group-hover:scale-110
                  dark:group-hover:shadow-[0_0_20px_var(--neon-blue)]
                `}
              />
            </div>
          </Link>
        )}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-expanded={sidebarOpen}
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          className={`
            p-2 rounded-lg transition-all duration-200
            text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100
            active:scale-95
            dark:text-neon-blue/70 dark:hover:text-neon-blue
            dark:hover:bg-neon-blue/10
            dark:hover:shadow-[0_0_15px_rgba(0,245,255,0.3)]
            ${!sidebarOpen ? 'absolute right-2' : ''}
          `}
        >
          {sidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </button>
      </div>

      {/* ========================================
          NAVIGATION CONTENT - Scrollable
          ======================================== */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden py-4">
        {/* Main Navigation */}
        <nav className="px-3 space-y-1" aria-label="Main navigation">
          {sidebarOpen && (
            <p className={`
              px-3 text-xs font-semibold uppercase tracking-wider mb-2
              text-secondary-400
              dark:text-neon-blue/50 dark:font-cyber
            `}>
              Main
            </p>
          )}
          {mainNav.map((item, index) => (
            <NavLink
              key={item.name}
              to={item.href}
              onMouseEnter={() => setHoveredItem(item.name)}
              onMouseLeave={() => setHoveredItem(null)}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200
                group relative
                /* Light Mode Active */
                ${isActive
                  ? 'bg-primary-50 text-primary-700 font-medium'
                  : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                }
                /* Dark Mode Active */
                ${isActive && isDark
                  ? '!bg-neon-blue/10 !text-neon-blue border border-neon-blue/30 shadow-[0_0_15px_rgba(0,245,255,0.2)]'
                  : isDark ? '!text-gray-400 hover:!bg-neon-blue/5 hover:!text-neon-blue' : ''
                }
                ${!sidebarOpen ? 'justify-center' : ''}
              `}
              style={isDark ? { animationDelay: `${index * 50}ms` } : undefined}
            >
              {({ isActive }) => (
                <>
                  {/* Active indicator bar - Dark Mode Only */}
                  {isDark && isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-neon-blue rounded-r-full shadow-[0_0_10px_var(--neon-blue)]" />
                  )}
                  <item.icon
                    size={20}
                    className={`
                      shrink-0 transition-all duration-200
                      ${isActive
                        ? 'text-primary-600'
                        : 'text-secondary-400 group-hover:text-secondary-600'
                      }
                      ${isActive && isDark ? '!text-neon-blue drop-shadow-[0_0_8px_var(--neon-blue)]' : ''}
                      ${!isActive && isDark ? '!text-gray-500 group-hover:!text-neon-blue group-hover:drop-shadow-[0_0_6px_var(--neon-blue)]' : ''}
                    `}
                  />
                  {sidebarOpen && (
                    <span className={`
                      truncate transition-all
                      ${isActive ? 'font-medium' : ''}
                      ${isDark ? 'font-cyber tracking-wide' : ''}
                    `}>{item.name}</span>
                  )}
                  {/* Hover tooltip when collapsed */}
                  {!sidebarOpen && hoveredItem === item.name && (
                    <div className={`
                      absolute left-full ml-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap z-50
                      animate-fade-in
                      bg-secondary-900 text-white shadow-lg
                      dark:bg-cyber-card dark:border dark:border-neon-blue/30 dark:text-neon-blue
                      dark:shadow-[0_0_20px_rgba(0,245,255,0.3)]
                    `}>
                      {item.name}
                    </div>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Tools Section */}
        <nav className="px-3 mt-6 space-y-1" aria-label="Tools navigation">
          {sidebarOpen && (
            <p className={`
              px-3 text-xs font-semibold uppercase tracking-wider mb-2
              text-secondary-400
              dark:text-neon-purple/50 dark:font-cyber
            `}>
              Tools
            </p>
          )}
          {toolsNav.map((item, index) => (
            <NavLink
              key={item.name}
              to={item.href}
              onMouseEnter={() => setHoveredItem(item.name)}
              onMouseLeave={() => setHoveredItem(null)}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200
                group relative
                /* Light Mode */
                ${isActive
                  ? 'bg-primary-50 text-primary-700 font-medium'
                  : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                }
                /* Dark Mode - Purple accent for tools */
                ${isActive && isDark
                  ? '!bg-neon-purple/10 !text-neon-purple border border-neon-purple/30 shadow-[0_0_15px_rgba(191,0,255,0.2)]'
                  : isDark ? '!text-gray-400 hover:!bg-neon-purple/5 hover:!text-neon-purple' : ''
                }
                ${!sidebarOpen ? 'justify-center' : ''}
              `}
              style={isDark ? { animationDelay: `${(index + mainNav.length) * 50}ms` } : undefined}
            >
              {({ isActive }) => (
                <>
                  {/* Active indicator bar - Dark Mode Only */}
                  {isDark && isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-neon-purple rounded-r-full shadow-[0_0_10px_var(--neon-purple)]" />
                  )}
                  <item.icon
                    size={20}
                    className={`
                      shrink-0 transition-all duration-200
                      ${isActive
                        ? 'text-primary-600'
                        : 'text-secondary-400 group-hover:text-secondary-600'
                      }
                      ${isActive && isDark ? '!text-neon-purple drop-shadow-[0_0_8px_var(--neon-purple)]' : ''}
                      ${!isActive && isDark ? '!text-gray-500 group-hover:!text-neon-purple group-hover:drop-shadow-[0_0_6px_var(--neon-purple)]' : ''}
                    `}
                  />
                  {sidebarOpen && (
                    <span className={`
                      truncate transition-all
                      ${isActive ? 'font-medium' : ''}
                      ${isDark ? 'font-cyber tracking-wide' : ''}
                    `}>{item.name}</span>
                  )}
                  {/* Hover tooltip when collapsed */}
                  {!sidebarOpen && hoveredItem === item.name && (
                    <div className={`
                      absolute left-full ml-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap z-50
                      animate-fade-in
                      bg-secondary-900 text-white shadow-lg
                      dark:bg-cyber-card dark:border dark:border-neon-purple/30 dark:text-neon-purple
                      dark:shadow-[0_0_20px_rgba(191,0,255,0.3)]
                    `}>
                      {item.name}
                    </div>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Quick Actions */}
        {sidebarOpen && (
          <div className="px-3 mt-6">
            <p className={`
              px-3 text-xs font-semibold uppercase tracking-wider mb-2
              text-secondary-400
              dark:text-neon-green/50 dark:font-cyber
            `}>
              {t('sidebar.quickActions')}
            </p>
            <div className="space-y-1">
              {quickActions.map((action) => (
                <NavLink
                  key={action.name}
                  to={action.href}
                  className={({ isActive }) => `
                    flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200
                    group
                    /* Light Mode */
                    ${isActive
                      ? action.color === 'blue'
                        ? 'bg-blue-50 text-blue-700'
                        : 'bg-purple-50 text-purple-700'
                      : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                    }
                    /* Dark Mode */
                    ${isActive && isDark
                      ? action.color === 'blue'
                        ? '!bg-neon-blue/10 !text-neon-blue border border-neon-blue/30 shadow-[0_0_15px_rgba(0,245,255,0.2)]'
                        : '!bg-neon-purple/10 !text-neon-purple border border-neon-purple/30 shadow-[0_0_15px_rgba(191,0,255,0.2)]'
                      : isDark ? '!text-gray-400 hover:!bg-white/5' : ''
                    }
                  `}
                >
                  {({ isActive: _isActive }) => (
                    <>
                      <div className={`
                        p-1.5 rounded-md transition-all
                        ${action.color === 'blue'
                          ? 'bg-blue-100 group-hover:bg-blue-200'
                          : 'bg-purple-100 group-hover:bg-purple-200'
                        }
                        ${isDark && action.color === 'blue' ? '!bg-neon-blue/20 group-hover:!bg-neon-blue/30' : ''}
                        ${isDark && action.color === 'purple' ? '!bg-neon-purple/20 group-hover:!bg-neon-purple/30' : ''}
                      `}>
                        <action.icon
                          size={16}
                          className={`
                            transition-all
                            ${action.color === 'blue' ? 'text-blue-600' : 'text-purple-600'}
                            ${isDark && action.color === 'blue' ? '!text-neon-blue' : ''}
                            ${isDark && action.color === 'purple' ? '!text-neon-purple' : ''}
                          `}
                        />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className={`
                          text-sm truncate
                          ${isDark ? 'font-cyber' : ''}
                        `}>{action.name}</span>
                        <span className={`
                          text-xs truncate
                          text-secondary-400
                          dark:text-gray-500
                        `}>{action.desc}</span>
                      </div>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ========================================
          BOTTOM SECTION - Settings
          ======================================== */}
      <div className={`
        shrink-0 p-3 border-t
        border-secondary-200 bg-secondary-50/50
        dark:border-neon-blue/20 dark:bg-cyber-card/50
      `}>
        <NavLink
          to="/app/settings"
          onMouseEnter={() => setHoveredItem('settings')}
          onMouseLeave={() => setHoveredItem(null)}
          className={({ isActive }) => `
            flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200
            group relative
            /* Light Mode */
            ${isActive
              ? 'bg-secondary-100 text-secondary-900 font-medium'
              : 'text-secondary-600 hover:bg-secondary-100 hover:text-secondary-900'
            }
            /* Dark Mode */
            ${isActive && isDark
              ? '!bg-neon-blue/10 !text-neon-blue border border-neon-blue/30 shadow-[0_0_15px_rgba(0,245,255,0.2)]'
              : isDark ? '!text-gray-400 hover:!bg-neon-blue/5 hover:!text-neon-blue' : ''
            }
            ${!sidebarOpen ? 'justify-center' : ''}
          `}
        >
          {({ isActive }) => (
            <>
              {/* Active indicator bar - Dark Mode Only */}
              {isDark && isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-neon-blue rounded-r-full shadow-[0_0_10px_var(--neon-blue)]" />
              )}
              <Settings
                size={20}
                className={`
                  shrink-0 transition-all duration-200
                  ${isActive
                    ? 'text-secondary-700'
                    : 'text-secondary-400 group-hover:text-secondary-600'
                  }
                  ${isActive && isDark ? '!text-neon-blue drop-shadow-[0_0_8px_var(--neon-blue)]' : ''}
                  ${!isActive && isDark ? '!text-gray-500 group-hover:!text-neon-blue group-hover:drop-shadow-[0_0_6px_var(--neon-blue)]' : ''}
                `}
              />
              {sidebarOpen && (
                <span className={`
                  truncate
                  ${isActive ? 'font-medium' : ''}
                  ${isDark ? 'font-cyber tracking-wide' : ''}
                `}>{t('nav.settings')}</span>
              )}
              {/* Hover tooltip when collapsed */}
              {!sidebarOpen && hoveredItem === 'settings' && (
                <div className={`
                  absolute left-full ml-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap z-50
                  animate-fade-in
                  bg-secondary-900 text-white shadow-lg
                  dark:bg-cyber-card dark:border dark:border-neon-blue/30 dark:text-neon-blue
                  dark:shadow-[0_0_20px_rgba(0,245,255,0.3)]
                `}>
                  {t('nav.settings')}
                </div>
              )}
            </>
          )}
        </NavLink>

        {/* Back to home link */}
        {sidebarOpen && (
          <Link
            to="/"
            className={`
              flex items-center gap-3 px-3 py-2 mt-2 rounded-lg transition-all duration-200
              group
              text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100
              dark:text-gray-500 dark:hover:text-neon-green dark:hover:bg-neon-green/5
            `}
          >
            <Home size={18} className="shrink-0" />
            <span className={`
              text-sm
              ${isDark ? 'font-cyber' : ''}
            `}>
              Back to Home
            </span>
          </Link>
        )}
      </div>
    </aside>
  )
}
