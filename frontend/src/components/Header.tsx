import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Bell, Search, Wallet, LogOut, User, Copy, Check, PlusCircle, Target, Menu, SkipForward, HelpCircle } from 'lucide-react'
import { useState } from 'react'
import { useDisconnect } from 'wagmi'
import { getHealth } from '@/lib/api'
import { useAppStore } from '@/store'
import { useAuthStore, USER_ROLE_LABELS } from '@/stores/authStore'
import { useWalletAuth } from '@/hooks/useWalletAuth'
import { useToken } from '@/hooks/useToken'
import LanguageSwitcher from './LanguageSwitcher'
import ThemeToggle from './ThemeToggle'
import MobileDrawer from './MobileDrawer'
import { Tooltip } from './ui/Tooltip'
import WalletBindingModal from './WalletBindingModal'

export default function Header() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { notifications } = useAppStore()
  const { disconnect: _disconnect } = useDisconnect()
  const { isAuthenticated, logout: authLogout } = useWalletAuth()
  const { formattedBalance } = useToken()
  const { 
    address, 
    isConnected, 
    bindingType, 
    userRole, 
    name, 
    reputation, 
    stake,
    setManualIdentifier,
  } = useAuthStore()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [copied, setCopied] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [showBindingModal, setShowBindingModal] = useState(false)

  // Handle skip wallet - use random identifier
  const handleSkipWallet = () => {
    const guestId = `guest_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
    setManualIdentifier(guestId)
    navigate('/app/dashboard')
  }

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000,
  })

  const handleLogout = async () => {
    await authLogout()
    setShowUserMenu(false)
  }

  const copyAddress = () => {
    if (address) {
      navigator.clipboard.writeText(address)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const formatAddress = (addr: string) => {
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`
  }

  return (
    <>
      {/* Mobile Drawer */}
      <MobileDrawer isOpen={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />

      <header className={`
        h-16 flex items-center justify-between px-4 md:px-6 relative z-20
        /* Light Mode: Clean white header */
        bg-white border-b border-light-border
        /* Dark Mode: Cyberpunk glass effect */
        dark:bg-cyber-card/80 dark:backdrop-blur-md dark:border-neon-blue/20
      `}>
        {/* Neon top border effect - Dark Mode Only */}
        <div className="hidden dark:block absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-blue to-transparent opacity-50" />

        {/* Left section - Hamburger + Search */}
        <div className="flex items-center gap-3">
          {/* Hamburger menu button - mobile only */}
          <button
            className={`
              md:hidden p-2 rounded-lg transition-all
              text-secondary-600 hover:bg-secondary-100
              dark:text-neon-blue dark:hover:bg-neon-blue/10 dark:hover:shadow-neon-blue
            `}
            onClick={() => setMobileMenuOpen(true)}
            aria-label="Toggle menu"
          >
            <Menu className="w-6 h-6" />
          </button>

          {/* Search */}
          <div className="relative w-full md:w-64 lg:w-96">
            <Search className={`
              absolute left-3 top-1/2 -translate-y-1/2
              text-secondary-400
              dark:text-neon-blue/60
            `} size={20} />
            <input
              type="text"
              placeholder={t('common.search') + '...'}
              className={`
                w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none transition-all
                /* Light Mode */
                bg-secondary-100 border-secondary-200 text-secondary-900
                focus:ring-2 focus:ring-blue-500 focus:border-transparent
                /* Dark Mode */
                dark:bg-cyber-dark/80 dark:border-neon-blue/30 dark:text-gray-100 dark:placeholder-neon-blue/40
                dark:focus:border-neon-blue dark:focus:ring-neon-blue/30
                dark:focus:shadow-[0_0_15px_rgba(0,245,255,0.2)]
              `}
            />
          </div>
        </div>

        {/* Right section */}
        <div className="flex items-center gap-4">
          {/* Status indicator */}
          {health && (
            <div className={`
              flex items-center gap-2 px-3 py-1.5 rounded-full
              /* Light Mode */
              bg-green-50
              /* Dark Mode */
              dark:bg-neon-green/10 dark:border dark:border-neon-green/30
            `}>
              <div className={`
                w-2 h-2 rounded-full animate-pulse
                bg-green-500
                dark:bg-neon-green dark:shadow-[0_0_8px_var(--neon-green)]
              `} />
              <span className={`
                text-sm font-medium
                text-green-700
                dark:text-neon-green
              `}>{t('agents.online')}</span>
            </div>
          )}

          {/* Theme toggle */}
          <ThemeToggle />

          {/* Language Switcher */}
          <LanguageSwitcher />

          {/* Notifications */}
          <Tooltip content={t('tooltips.notificationSettings', 'Notifications')} position="bottom">
            <button
              aria-label={`Notifications${notifications.length > 0 ? `, ${notifications.length} unread` : ''}`}
              className={`
                relative p-2 rounded-lg transition-all
                text-secondary-600 hover:bg-secondary-100
                dark:text-neon-blue dark:hover:bg-neon-blue/10 dark:hover:shadow-[0_0_10px_rgba(0,245,255,0.3)]
              `}
            >
              <Bell size={20} />
              {notifications.length > 0 && (
                <span className={`
                  absolute top-1 right-1 w-4 h-4 text-white text-xs rounded-full flex items-center justify-center
                  bg-red-500
                  dark:bg-neon-pink dark:shadow-[0_0_8px_var(--neon-pink)]
                `}>
                  {notifications.length}
                </span>
              )}
            </button>
          </Tooltip>

          {/* Help Button */}
          <Tooltip content={t('help.openHelp', 'Open Help Center')} position="bottom">
            <button
              onClick={() => window.dispatchEvent(new CustomEvent('open-help-center'))}
              aria-label={t('help.openHelp', 'Open Help Center')}
              className={`
                p-2 rounded-lg transition-all
                text-secondary-600 hover:bg-secondary-100
                dark:text-neon-blue dark:hover:bg-neon-blue/10 dark:hover:shadow-[0_0_10px_rgba(0,245,255,0.3)]
              `}
            >
              <HelpCircle size={20} />
            </button>
          </Tooltip>

          {/* Wallet / User section */}
          {isConnected && isAuthenticated ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className={`
                  flex items-center gap-3 px-3 py-2 rounded-lg transition-all
                  /* Light Mode */
                  bg-light-bg-tertiary hover:bg-secondary-100
                  /* Dark Mode */
                  dark:bg-cyber-dark/80 dark:border dark:border-neon-blue/30 dark:hover:border-neon-blue/50 dark:hover:shadow-[0_0_15px_rgba(0,245,255,0.2)]
                `}
              >
                {/* Avatar */}
                <div className={`
                  w-8 h-8 rounded-full flex items-center justify-center
                  /* Light Mode */
                  bg-primary-600
                  /* Dark Mode */
                  dark:bg-gradient-to-br dark:from-neon-blue dark:to-neon-purple dark:shadow-[0_0_10px_var(--neon-blue)]
                `}>
                  <span className="text-white text-sm font-medium">
                    {name ? name.slice(0, 2).toUpperCase() : address?.slice(2, 4).toUpperCase()}
                  </span>
                </div>
                {/* Info */}
                <div className="text-left">
                  <p className={`
                    text-sm font-medium
                    text-secondary-900
                    dark:text-gray-100
                  `}>
                    {name || formatAddress(address!)}
                  </p>
                  <p className={`
                    text-xs
                    text-secondary-500
                    dark:text-neon-blue/70
                  `}>
                    {stake} {t('header.vibeStaked')}
                  </p>
                </div>
                {/* Reputation badge */}
                <div className={`
                  px-2 py-0.5 text-xs rounded-full
                  /* Light Mode */
                  bg-yellow-100 text-yellow-700
                  /* Dark Mode */
                  dark:bg-neon-green/10 dark:text-neon-green dark:border dark:border-neon-green/30
                `}>
                  {t('header.rep')}: {reputation.toFixed(2)}
                </div>
              </button>

              {/* Dropdown menu */}
              {showUserMenu && (
                <div role="menu" aria-label="User menu" className={`
                  absolute right-0 top-full mt-2 w-72 rounded-lg shadow-lg border py-2 z-50
                  /* Light Mode */
                  bg-white border-secondary-200
                  /* Dark Mode */
                  dark:bg-cyber-card dark:border-neon-blue/30 dark:shadow-[0_0_30px_rgba(0,245,255,0.2)]
                `}>
                  {/* Address */}
                  <div className={`
                    px-4 py-2 border-b
                    border-secondary-200
                    dark:border-neon-blue/20
                  `}>
                    <p className={`
                      text-xs mb-1
                      text-secondary-500
                      dark:text-neon-blue/60
                    `}>{t('header.walletAddress')}</p>
                    <div className="flex items-center gap-2">
                      <p className={`
                        text-sm font-mono
                        text-secondary-700
                        dark:text-gray-200
                      `}>{formatAddress(address!)}</p>
                      <button
                        onClick={copyAddress}
                        aria-label="Copy wallet address"
                        className={`
                          p-1 rounded transition-colors
                          hover:bg-secondary-100
                          dark:hover:bg-neon-blue/10
                        `}
                      >
                        {copied ? (
                          <Check size={14} className="text-green-600 dark:text-neon-green" />
                        ) : (
                          <Copy size={14} className="text-secondary-400 dark:text-neon-blue/60" />
                        )}
                      </button>
                      <span className={`
                        text-xs px-2 py-0.5 rounded
                        bg-blue-100 text-blue-700
                        dark:bg-neon-blue/20 dark:text-neon-blue
                      `}>
                        {USER_ROLE_LABELS[userRole] || userRole}
                      </span>
                    </div>
                    {bindingType && (
                      <p className="text-xs text-secondary-400 dark:text-neon-blue/40 mt-1">
                        {bindingType === 'wallet' ? t('header.realWallet', '真实钱包') : 
                         bindingType === 'manual' ? t('header.tempId', '临时标识') : 
                         t('header.aiAgent', 'AI Agent')}
                      </p>
                    )}
                  </div>

                  {/* Stats */}
                  <div className={`
                    px-4 py-3 border-b
                    border-secondary-200
                    dark:border-neon-blue/20
                  `}>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className={`
                          text-xs
                          text-secondary-500
                          dark:text-neon-blue/60
                        `}>Balance</p>
                        <p className={`
                          text-lg font-semibold
                          text-secondary-900
                          dark:text-neon-blue
                        `}>{parseFloat(formattedBalance).toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
                      </div>
                      <div>
                        <p className={`
                          text-xs
                          text-secondary-500
                          dark:text-neon-blue/60
                        `}>{t('header.staked')}</p>
                        <p className={`
                          text-lg font-semibold
                          text-secondary-900
                          dark:text-neon-green
                        `}>{stake} VIBE</p>
                      </div>
                      <div>
                        <p className={`
                          text-xs
                          text-secondary-500
                          dark:text-neon-blue/60
                        `}>{t('header.reputation')}</p>
                        <p className={`
                          text-lg font-semibold
                          text-secondary-900
                          dark:text-neon-purple
                        `}>{reputation.toFixed(2)}</p>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="py-1" role="group">
                    <button
                      onClick={() => setShowBindingModal(true)}
                      className={`
                        flex items-center gap-2 px-4 py-2 text-sm w-full transition-colors
                        text-blue-600 hover:bg-blue-50
                        dark:text-neon-blue dark:hover:bg-neon-blue/10
                      `}
                    >
                      <Wallet size={16} />
                      {t('header.changeBinding', '更换绑定')}
                    </button>
                    <Link
                      to="/app/publish/service"
                      role="menuitem"
                      className={`
                        flex items-center gap-2 px-4 py-2 text-sm transition-colors
                        text-green-600 hover:bg-green-50
                        dark:text-neon-green dark:hover:bg-neon-green/10
                      `}
                    >
                      <PlusCircle size={16} />
                      {t('dashboard.publishService')}
                    </Link>
                    <Link
                      to="/app/publish/demand"
                      role="menuitem"
                      className={`
                        flex items-center gap-2 px-4 py-2 text-sm transition-colors
                        text-blue-600 hover:bg-blue-50
                        dark:text-neon-blue dark:hover:bg-neon-blue/10
                      `}
                    >
                      <Target size={16} />
                      {t('dashboard.publishDemand')}
                    </Link>
                    <div className={`
                      border-t my-1
                      border-secondary-200
                      dark:border-neon-blue/20
                    `} />
                    <a
                      href="/app/settings"
                      role="menuitem"
                      className={`
                        flex items-center gap-2 px-4 py-2 text-sm transition-colors
                        text-secondary-600 hover:bg-secondary-100
                        dark:text-gray-300 dark:hover:bg-white/5
                      `}
                    >
                      <User size={16} />
                      {t('header.profileSettings')}
                    </a>
                    <button
                      onClick={handleLogout}
                      role="menuitem"
                      className={`
                        flex items-center gap-2 px-4 py-2 text-sm w-full transition-colors
                        text-red-600 hover:bg-red-50
                        dark:text-neon-pink dark:hover:bg-neon-pink/10
                      `}
                    >
                      <LogOut size={16} />
                      {t('header.disconnectWallet')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            // Not connected - show connect button with skip option
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowBindingModal(true)}
                className={`
                  flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all
                  bg-blue-600 text-white hover:bg-blue-700
                  dark:bg-neon-blue/20 dark:text-neon-blue dark:border dark:border-neon-blue/50 dark:hover:bg-neon-blue/30
                `}
              >
                <Wallet size={18} />
                {t('header.connectWallet')}
              </button>
              <button
                onClick={handleSkipWallet}
                title={t('header.skipWalletHint')}
                className={`
                  flex items-center gap-1 px-3 py-2 text-sm rounded-lg transition-all
                  text-secondary-500 hover:text-secondary-700
                  hover:bg-secondary-100
                  dark:text-neon-blue/70 dark:hover:text-neon-blue dark:hover:bg-neon-blue/10
                `}
              >
                <SkipForward size={16} />
                <span className="hidden sm:inline">{t('header.skipWallet')}</span>
              </button>
            </div>
          )}
        </div>

        {/* Click outside to close menu */}
        {showUserMenu && (
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowUserMenu(false)}
          />
        )}
      </header>

      {/* Wallet Binding Modal */}
      <WalletBindingModal
        isOpen={showBindingModal}
        onClose={() => setShowBindingModal(false)}
      />
    </>
  )
}
