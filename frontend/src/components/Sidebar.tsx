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
  Presentation,
  Dna,
  FileCode,
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
    { name: t('nav.geneCapsule'), href: '/app/gene-capsule/explore', icon: Dna, group: 'tools' },
    { name: t('nav.contracts', 'Contracts'), href: '/app/contracts', icon: FileCode, group: 'tools' },
  ]

  const quickActions = [
    { name: t('sidebar.publishService'), href: '/app/publish/service', icon: PlusCircle, desc: t('sidebar.publishServiceDesc'), color: 'blue' },
    { name: t('sidebar.publishDemand'), href: '/app/publish/demand', icon: Target, desc: t('sidebar.publishDemandDesc'), color: 'purple' },
    { name: t('sidebar.investorPresentation'), href: '/pitch', icon: Presentation, desc: t('sidebar.vibeIntroduction'), color: 'green' },
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
        bg-white border-r border-light-border shadow-sm
        /* ========================================
           DARK MODE - Cyberpunk Sci-Fi Style
           ======================================== */
        dark:bg-cyber-card/95 dark:backdrop-blur-xl dark:border-blue-500/20
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
        border-gray-200
        dark:border-blue-500/20
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
                  dark:group-hover:shadow-[0_0_20px_rgba(59,130,246,0.5)]
                `}
              />
            </div>
            <div className="flex flex-col">
              <span className={`
                font-bold text-lg leading-tight transition-colors
                text-gray-900 group-hover:text-blue-600
                dark:text-transparent dark:bg-clip-text dark:bg-gradient-to-r
                dark:from-blue-400 dark:via-purple-400 dark:to-green-400
                dark:font-cyber dark:group-hover:from-green-400 dark:group-hover:to-blue-400
              `}>USMSB</span>
              <span className={`
                text-xs
                text-gray-500
                dark:text-blue-400/60 dark:font-cyber
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
                  dark:group-hover:shadow-[0_0_20px_rgba(59,130,246,0.5)]
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
            text-gray-500 hover:text-gray-700 hover:bg-gray-100
            active:scale-95
            dark:text-blue-400/70 dark:hover:text-blue-400
            dark:hover:bg-blue-400/10
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
              text-gray-500
              dark:text-blue-400/60 dark:font-cyber
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
                /* Light Mode */
                ${isActive
                  ? 'bg-gradient-to-r from-blue-50 to-purple-50 text-blue-700 font-medium border border-blue-200'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 active:bg-gray-200 active:text-gray-900'
                }
                /* Dark Mode */
                ${isActive && isDark
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : isDark ? 'text-gray-300 hover:bg-blue-600/10 hover:text-blue-400 active:bg-blue-600/30 active:text-blue-400' : ''
                }
                ${!sidebarOpen ? 'justify-center' : ''}
              `}
              style={isDark ? { animationDelay: `${index * 50}ms` } : undefined}
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    size={20}
                    className={`
                      shrink-0 transition-all duration-200
                      ${isActive
                        ? isDark ? 'text-blue-400' : 'text-blue-600'
                        : 'text-gray-500 group-hover:text-gray-700'
                      }
                      ${!isActive && isDark ? '!text-gray-400 group-hover:!text-blue-400 active:!text-blue-400' : ''}
                    `}
                  />
                  {sidebarOpen && (
                    <span className={`
                      truncate transition-all
                      ${isActive 
                        ? isDark ? 'text-blue-400' : 'text-blue-700' 
                        : ''  
                      }
                      ${isActive ? 'font-medium' : ''}
                      ${isDark ? 'font-cyber tracking-wide group-hover:text-blue-400 active:text-blue-400' : ''}
                    `}>{item.name}</span>
                  )}
                   {/* Hover tooltip when collapsed */}
                  {!sidebarOpen && hoveredItem === item.name && (
                    <div className={`
                      absolute left-full ml-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap z-50
                      animate-fade-in
                      bg-white text-gray-900 shadow-lg border border-gray-200
                      dark:bg-cyber-card dark:border dark:border-blue-500/30 dark:text-blue-400
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
              text-gray-500
              dark:text-purple-400/60 dark:font-cyber
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
                  ? 'bg-gradient-to-r from-purple-50 to-pink-50 text-purple-700 font-medium border border-purple-200'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 active:bg-gray-200 active:text-gray-900'
                }
                /* Dark Mode - 使用紫色发光效果 */
                ${isActive && isDark
                  ? 'bg-purple-600/20 text-purple-400 border border-purple-500/30'
                  : isDark ? 'text-gray-300 hover:bg-purple-600/10 hover:text-purple-400 active:bg-purple-600/30 active:text-purple-400' : ''
                }
                ${!sidebarOpen ? 'justify-center' : ''}
              `}
              style={isDark ? { animationDelay: `${(index + mainNav.length) * 50}ms` } : undefined}
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    size={20}
                    className={`
                      shrink-0 transition-all duration-200
                      ${isActive
                        ? isDark ? 'text-purple-400' : 'text-purple-600'
                        : 'text-gray-500 group-hover:text-gray-700'
                      }
                      ${!isActive && isDark ? '!text-gray-400 group-hover:!text-purple-400 active:!text-purple-400' : ''}
                    `}
                  />
                  {sidebarOpen && (
                    <span className={`
                      truncate transition-all
                      ${isActive 
                        ? isDark ? 'text-purple-400' : 'text-purple-700' 
                        : ''  
                      }
                      ${isActive ? 'font-medium' : ''}
                      ${isDark ? 'font-cyber tracking-wide group-hover:text-purple-400 active:text-purple-400' : ''}
                    `}>{item.name}</span>
                  )}
                   {/* Hover tooltip when collapsed */}
                  {!sidebarOpen && hoveredItem === item.name && (
                    <div className={`
                      absolute left-full ml-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap z-50
                      animate-fade-in
                      bg-white text-gray-900 shadow-lg border border-gray-200
                      dark:bg-cyber-card dark:border dark:border-purple-500/30 dark:text-purple-400
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
              text-gray-500
              dark:text-green-400/60 dark:font-cyber
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
                        ? 'bg-blue-50 text-blue-700 border border-blue-200'
                        : 'bg-purple-50 text-purple-700 border border-purple-200'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }
                    /* Dark Mode */
                    ${isActive && isDark
                      ? action.color === 'blue'
                        ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                        : 'bg-purple-600/20 text-purple-400 border border-purple-500/30'
                      : isDark 
                        ? action.color === 'blue'
                          ? 'text-gray-300 hover:bg-blue-600/10 hover:text-blue-400 active:bg-blue-600/30 active:text-blue-400'
                          : 'text-gray-300 hover:bg-purple-600/10 hover:text-purple-400 active:bg-purple-600/30 active:text-purple-400'
                        : ''
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
                        ${isDark && action.color === 'blue' ? '!bg-blue-600/20 group-hover:!bg-blue-600/30' : ''}
                        ${isDark && action.color === 'purple' ? '!bg-purple-600/20 group-hover:!bg-purple-600/30' : ''}
                      `}>
                        <action.icon
                          size={16}
                          className={`
                            transition-all
                            ${action.color === 'blue' ? 'text-blue-600' : 'text-purple-600'}
                            ${isDark && action.color === 'blue' ? '!text-blue-400' : ''}
                            ${isDark && action.color === 'purple' ? '!text-purple-400' : ''}
                          `}
                        />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className={`
                          text-sm truncate
                          ${isDark 
                            ? action.color === 'blue' 
                              ? 'font-cyber group-hover:text-blue-400 active:text-blue-400' 
                              : 'font-cyber group-hover:text-purple-400 active:text-purple-400' 
                            : ''
                          }
                        `}>{action.name}</span>
                        <span className={`
                          text-xs truncate
                          text-gray-500
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
        border-gray-200 bg-gray-50
        dark:border-blue-500/20 dark:bg-cyber-card/50
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
              ? 'bg-gray-100 text-gray-900 font-medium'
              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 active:bg-gray-200 active:text-gray-900'
            }
            /* Dark Mode */
            ${isActive && isDark
              ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
              : isDark ? 'text-gray-300 hover:bg-blue-600/10 hover:text-blue-400 active:bg-blue-600/30 active:text-blue-400' : ''
            }
            ${!sidebarOpen ? 'justify-center' : ''}
          `}
        >
          {({ isActive }) => (
            <>
              <Settings
                size={20}
                className={`
                  shrink-0 transition-all duration-200
                  ${isActive
                    ? isDark ? 'text-blue-400' : 'text-gray-700'
                    : 'text-gray-500 group-hover:text-gray-700'
                  }
                  ${!isActive && isDark ? '!text-gray-400 group-hover:!text-blue-400 active:!text-blue-400' : ''}
                `}
              />
              {sidebarOpen && (
                <span className={`
                  truncate transition-all
                  ${isActive 
                    ? isDark ? 'text-blue-400' : 'text-gray-900' 
                    : ''  
                  }
                  ${isActive ? 'font-medium' : ''}
                  ${isDark ? 'font-cyber tracking-wide group-hover:text-blue-400 active:text-blue-400' : ''}
                `}>{t('nav.settings')}</span>
              )}
              {/* Hover tooltip when collapsed */}
              {!sidebarOpen && hoveredItem === 'settings' && (
                <div className={`
                  absolute left-full ml-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap z-50
                  animate-fade-in
                  bg-white text-gray-900 shadow-lg border border-gray-200
                  dark:bg-cyber-card dark:border dark:border-blue-500/30 dark:text-blue-400
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
              text-gray-500 hover:text-gray-700 hover:bg-gray-100
              dark:text-gray-500 dark:hover:text-green-400 dark:hover:bg-green-400/5
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
