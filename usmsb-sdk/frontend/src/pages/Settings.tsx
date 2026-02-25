import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Bell,
  Palette,
  Shield,
  Wallet,
  Globe,
  Check,
  Copy,
  LogOut,
  Sun,
  Moon,
  Monitor,
  Coins,
  Lock,
  Unlock,
  Clock,
  AlertCircle,
  Bot,
} from 'lucide-react'
import clsx from 'clsx'
import { useToastStore } from '@/stores/toastStore'
import { useAppStore } from '@/store'
import { useWalletAuth } from '@/hooks/useWalletAuth'
import { useAuthStore } from '@/stores/authStore'
import { HelpIcon } from '@/components/ui'
import AgentWalletManager from '@/components/ui/AgentWalletManager'
import {
  getStakeConfig,
  getBalance,
  stakeTokens,
  requestUnstake,
  cancelUnstake,
  confirmUnstake,
} from '@/services/authService'

type SettingsSection = 'general' | 'notifications' | 'appearance' | 'privacy' | 'wallet' | 'staking' | 'agentWallets'

interface SettingsState {
  language: string
  emailNotifications: boolean
  pushNotifications: boolean
  weeklyDigest: boolean
  marketingEmails: boolean
  dataCollection: boolean
  analyticsOptIn: boolean
}

const languages = [
  { code: 'en', name: 'English', flag: 'US' },
  { code: 'zh', name: '中文', flag: 'CN' },
  { code: 'ja', name: '日本語', flag: 'JP' },
  { code: 'ko', name: '한국어', flag: 'KR' },
  { code: 'ru', name: 'Русский', flag: 'RU' },
  { code: 'fr', name: 'Français', flag: 'FR' },
  { code: 'de', name: 'Deutsch', flag: 'DE' },
  { code: 'es', name: 'Español', flag: 'ES' },
  { code: 'pt', name: 'Português', flag: 'BR' },
]

export default function Settings() {
  const { t, i18n } = useTranslation()
  const { addToast } = useToastStore()
  const { themeMode, setThemeMode } = useAppStore()
  const { address, isConnected, logout } = useWalletAuth()
  const { name: profileName } = useAuthStore()

  const [activeSection, setActiveSection] = useState<SettingsSection>('general')
  const [copiedAddress, setCopiedAddress] = useState(false)

  const [settings, setSettings] = useState<SettingsState>({
    language: i18n.language || 'en',
    emailNotifications: true,
    pushNotifications: true,
    weeklyDigest: false,
    marketingEmails: false,
    dataCollection: true,
    analyticsOptIn: true,
  })

  const sections: { id: SettingsSection; label: string; icon: typeof Globe }[] = [
    { id: 'general', label: t('settings.general', 'General'), icon: Globe },
    { id: 'notifications', label: t('settings.notifications', 'Notifications'), icon: Bell },
    { id: 'appearance', label: t('settings.appearance', 'Appearance'), icon: Palette },
    { id: 'privacy', label: t('settings.privacy', 'Privacy'), icon: Shield },
    { id: 'wallet', label: t('settings.wallet', 'Wallet'), icon: Wallet },
    { id: 'staking', label: t('settings.staking', 'Staking'), icon: Coins },
    { id: 'agentWallets', label: t('agentWallet.title', 'Agent Wallets'), icon: Bot },
  ]

  // Load settings from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('usmsb-user-settings')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setSettings((prev) => ({ ...prev, ...parsed }))
      } catch {
        // Invalid JSON, ignore
      }
    }
  }, [])

  // Sync language setting with i18n
  useEffect(() => {
    setSettings((prev) => ({ ...prev, language: i18n.language || 'en' }))
  }, [i18n.language])

  const updateSetting = <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
    setSettings((prev) => {
      const newSettings = { ...prev, [key]: value }
      localStorage.setItem('usmsb-user-settings', JSON.stringify(newSettings))
      return newSettings
    })
  }

  const handleLanguageChange = (langCode: string) => {
    i18n.changeLanguage(langCode)
    updateSetting('language', langCode)
    addToast({
      type: 'success',
      message: t('settings.languageChanged', 'Language changed successfully'),
    })
  }

  const handleThemeChange = (mode: 'light' | 'dark' | 'system') => {
    setThemeMode(mode)
    addToast({
      type: 'success',
      message: t('settings.themeChanged', 'Theme updated successfully'),
    })
  }

  const copyAddress = async () => {
    if (address) {
      await navigator.clipboard.writeText(address)
      setCopiedAddress(true)
      setTimeout(() => setCopiedAddress(false), 2000)
      addToast({
        type: 'success',
        message: t('settings.addressCopied', 'Address copied to clipboard'),
      })
    }
  }

  const handleDisconnectWallet = async () => {
    await logout()
    addToast({
      type: 'info',
      message: t('settings.walletDisconnected', 'Wallet disconnected'),
    })
  }

  const truncateAddress = (addr: string) => {
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`
  }

  // Toggle component
  const Toggle = ({
    checked,
    onChange,
    disabled = false,
  }: {
    checked: boolean
    onChange: (checked: boolean) => void
    disabled?: boolean
  }) => (
    <label className={clsx('relative inline-flex items-center', disabled && 'cursor-not-allowed opacity-50')}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="sr-only peer"
      />
      <div
        className={clsx(
          'w-11 h-6 rounded-full transition-colors',
          'bg-secondary-200 dark:bg-secondary-700',
          'peer-focus:ring-4 peer-focus:ring-primary-100 dark:peer-focus:ring-primary-900/30',
          'peer-checked:bg-primary-600',
          "after:content-[''] after:absolute after:top-[2px] after:left-[2px]",
          'after:bg-white after:rounded-full after:h-5 after:w-5',
          'after:transition-transform peer-checked:after:translate-x-full'
        )}
      />
    </label>
  )

  return (
    <div className="space-y-4 md:space-y-6 p-4 md:p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-light-text-primary dark:text-secondary-100">
            {t('settings.title', 'Settings')}
          </h1>
          <p className="text-sm md:text-base text-light-text-muted dark:text-secondary-400">
            {t('settings.subtitle', 'Manage your account settings and preferences')}
          </p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar Navigation */}
        <div className="w-full lg:w-56 flex-shrink-0">
          <nav className="card p-2 flex lg:flex-col gap-1 overflow-x-auto lg:overflow-x-visible">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={clsx(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors whitespace-nowrap',
                  activeSection === section.id
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                    : 'text-light-text-secondary dark:text-secondary-400 hover:bg-light-bg-tertiary dark:hover:bg-secondary-800'
                )}
              >
                <section.icon size={18} />
                <span className="font-medium">{section.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* General Settings */}
          {activeSection === 'general' && (
            <div className="card space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.languageSettings', 'Language Settings')}
                  <HelpIcon content={t('tooltips.languageSwitch', 'Change interface language')} />
                </h2>
                <p className="text-sm text-light-text-muted dark:text-secondary-400 mt-1">
                  {t('settings.languageSettingsDesc', 'Choose your preferred language for the interface')}
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {languages.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => handleLanguageChange(lang.code)}
                    className={clsx(
                      'flex items-center gap-3 px-4 py-3 rounded-lg border-2 transition-all',
                      settings.language === lang.code || i18n.language === lang.code
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-secondary-200 dark:border-secondary-700 hover:border-secondary-300 dark:hover:border-secondary-600'
                    )}
                  >
                    <span className="text-xl">{getFlagEmoji(lang.flag)}</span>
                    <span className="font-medium text-light-text-primary dark:text-secondary-100">{lang.name}</span>
                    {(settings.language === lang.code || i18n.language === lang.code) && (
                      <Check size={16} className="ml-auto text-primary-600" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Notification Settings */}
          {activeSection === 'notifications' && (
            <div className="card space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.notificationSettings', 'Notification Settings')}
                  <HelpIcon content={t('tooltips.notificationSettings', 'Configure notification preferences')} />
                </h2>
                <p className="text-sm text-light-text-muted dark:text-secondary-400 mt-1">
                  {t('settings.notificationSettingsDesc', 'Configure how you receive notifications')}
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-secondary-100 dark:border-secondary-700">
                  <div>
                    <p className="font-medium text-light-text-primary dark:text-secondary-100">
                      {t('settings.emailNotifications', 'Email Notifications')}
                    </p>
                    <p className="text-sm text-light-text-muted dark:text-secondary-400">
                      {t('settings.emailNotificationsDesc', 'Receive important updates via email')}
                    </p>
                  </div>
                  <Toggle
                    checked={settings.emailNotifications}
                    onChange={(v) => updateSetting('emailNotifications', v)}
                  />
                </div>

                <div className="flex items-center justify-between py-3 border-b border-secondary-100 dark:border-secondary-700">
                  <div>
                    <p className="font-medium text-light-text-primary dark:text-secondary-100">
                      {t('settings.pushNotifications', 'Push Notifications')}
                    </p>
                    <p className="text-sm text-light-text-muted dark:text-secondary-400">
                      {t('settings.pushNotificationsDesc', 'Receive push notifications in browser')}
                    </p>
                  </div>
                  <Toggle
                    checked={settings.pushNotifications}
                    onChange={(v) => updateSetting('pushNotifications', v)}
                  />
                </div>

                <div className="flex items-center justify-between py-3 border-b border-secondary-100 dark:border-secondary-700">
                  <div>
                    <p className="font-medium text-light-text-primary dark:text-secondary-100">
                      {t('settings.weeklyDigest', 'Weekly Digest')}
                    </p>
                    <p className="text-sm text-light-text-muted dark:text-secondary-400">
                      {t('settings.weeklyDigestDesc', 'Receive a weekly summary of activity')}
                    </p>
                  </div>
                  <Toggle
                    checked={settings.weeklyDigest}
                    onChange={(v) => updateSetting('weeklyDigest', v)}
                  />
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium text-light-text-primary dark:text-secondary-100">
                      {t('settings.marketingEmails', 'Marketing Emails')}
                    </p>
                    <p className="text-sm text-light-text-muted dark:text-secondary-400">
                      {t('settings.marketingEmailsDesc', 'Receive news and promotional content')}
                    </p>
                  </div>
                  <Toggle
                    checked={settings.marketingEmails}
                    onChange={(v) => updateSetting('marketingEmails', v)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Appearance Settings */}
          {activeSection === 'appearance' && (
            <div className="card space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.appearanceSettings', 'Appearance Settings')}
                  <HelpIcon content={t('tooltips.themeToggle', 'Switch between light and dark theme')} />
                </h2>
                <p className="text-sm text-light-text-muted dark:text-secondary-400 mt-1">
                  {t('settings.appearanceSettingsDesc', 'Customize how the app looks')}
                </p>
              </div>

              <div>
                <label className="label">{t('settings.theme', 'Theme')}</label>
                <div className="grid grid-cols-3 gap-4 mt-2">
                  <button
                    onClick={() => handleThemeChange('light')}
                    className={clsx(
                      'flex flex-col items-center gap-3 p-4 rounded-xl border-2 transition-all',
                      themeMode === 'light'
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-secondary-200 dark:border-secondary-700 hover:border-secondary-300 dark:hover:border-secondary-600'
                    )}
                  >
                    <div className="w-12 h-12 rounded-full bg-secondary-100 flex items-center justify-center">
                      <Sun size={24} className="text-yellow-500" />
                    </div>
                    <span className="font-medium text-light-text-primary dark:text-secondary-100">
                      {t('settings.light', 'Light')}
                    </span>
                  </button>

                  <button
                    onClick={() => handleThemeChange('dark')}
                    className={clsx(
                      'flex flex-col items-center gap-3 p-4 rounded-xl border-2 transition-all',
                      themeMode === 'dark'
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-secondary-200 dark:border-secondary-700 hover:border-secondary-300 dark:hover:border-secondary-600'
                    )}
                  >
                    <div className="w-12 h-12 rounded-full bg-secondary-800 flex items-center justify-center">
                      <Moon size={24} className="text-blue-400" />
                    </div>
                    <span className="font-medium text-light-text-primary dark:text-secondary-100">
                      {t('settings.dark', 'Dark')}
                    </span>
                  </button>

                  <button
                    onClick={() => handleThemeChange('system')}
                    className={clsx(
                      'flex flex-col items-center gap-3 p-4 rounded-xl border-2 transition-all',
                      themeMode === 'system'
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-secondary-200 dark:border-secondary-700 hover:border-secondary-300 dark:hover:border-secondary-600'
                    )}
                  >
                    <div className="w-12 h-12 rounded-full bg-gradient-to-r from-secondary-100 to-secondary-800 flex items-center justify-center">
                      <Monitor size={24} className="text-white" />
                    </div>
                    <span className="font-medium text-light-text-primary dark:text-secondary-100">
                      {t('settings.system', 'System')}
                    </span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Privacy Settings */}
          {activeSection === 'privacy' && (
            <div className="card space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.privacySettings', 'Privacy Settings')}
                  <HelpIcon content={t('tooltips.privacySettings', 'Control your data and privacy')} />
                </h2>
                <p className="text-sm text-light-text-muted dark:text-secondary-400 mt-1">
                  {t('settings.privacySettingsDesc', 'Control your data and privacy preferences')}
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-secondary-100 dark:border-secondary-700">
                  <div>
                    <p className="font-medium text-light-text-primary dark:text-secondary-100">
                      {t('settings.dataCollection', 'Data Collection')}
                    </p>
                    <p className="text-sm text-light-text-muted dark:text-secondary-400">
                      {t('settings.dataCollectionDesc', 'Allow collection of usage data to improve services')}
                    </p>
                  </div>
                  <Toggle
                    checked={settings.dataCollection}
                    onChange={(v) => updateSetting('dataCollection', v)}
                  />
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium text-light-text-primary dark:text-secondary-100">
                      {t('settings.analyticsOptIn', 'Analytics')}
                    </p>
                    <p className="text-sm text-light-text-muted dark:text-secondary-400">
                      {t('settings.analyticsOptInDesc', 'Help us improve by sharing anonymous analytics')}
                    </p>
                  </div>
                  <Toggle
                    checked={settings.analyticsOptIn}
                    onChange={(v) => updateSetting('analyticsOptIn', v)}
                  />
                </div>
              </div>

              <div className="mt-6 p-4 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
                <p className="text-sm text-light-text-secondary dark:text-secondary-400">
                  {t('settings.privacyNote', 'Your privacy is important to us. We only collect data that helps us improve your experience. You can change these settings at any time.')}
                </p>
              </div>
            </div>
          )}

          {/* Wallet Settings */}
          {activeSection === 'wallet' && (
            <div className="card space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.walletSettings', 'Wallet Settings')}
                  <HelpIcon content={t('tooltips.walletConnect', 'Connect your Web3 wallet to access all features')} />
                </h2>
                <p className="text-sm text-light-text-muted dark:text-secondary-400 mt-1">
                  {t('settings.walletSettingsDesc', 'Manage your connected wallet')}
                </p>
              </div>

              {isConnected && address ? (
                <div className="space-y-4">
                  <div className="p-4 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-light-text-muted dark:text-secondary-400">
                          {t('settings.connectedWallet', 'Connected Wallet')}
                        </p>
                        <p className="font-mono text-lg text-light-text-primary dark:text-secondary-100 mt-1">
                          {truncateAddress(address)}
                        </p>
                        {profileName && (
                          <p className="text-sm text-light-text-muted dark:text-secondary-400 mt-1">
                            {profileName}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={copyAddress}
                          className="p-2 text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded-lg transition-colors"
                          title={t('settings.copyAddress', 'Copy address')}
                        >
                          {copiedAddress ? <Check size={20} className="text-green-500" /> : <Copy size={20} />}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={handleDisconnectWallet}
                      className="btn btn-secondary flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                    >
                      <LogOut size={18} />
                      {t('settings.disconnectWallet', 'Disconnect Wallet')}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Wallet size={48} className="mx-auto text-secondary-300 dark:text-secondary-600 mb-4" />
                  <p className="text-light-text-muted dark:text-secondary-400">
                    {t('settings.noWalletConnected', 'No wallet connected')}
                  </p>
                  <p className="text-sm text-secondary-400 dark:text-secondary-500 mt-1">
                    {t('settings.connectWalletHint', 'Connect a wallet from the header to manage your account')}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Staking Settings */}
          {activeSection === 'staking' && (
            <StakingSection
              isConnected={isConnected}
              addToast={addToast}
              t={t}
            />
          )}

          {/* Agent Wallets Settings */}
          {activeSection === 'agentWallets' && (
            <AgentWalletManager />
          )}
        </div>
      </div>
    </div>
  )
}

// Staking Section Component
function StakingSection({
  isConnected,
  addToast,
  t,
}: {
  isConnected: boolean
  addToast: (toast: { type: 'success' | 'error' | 'warning' | 'info'; message: string }) => void
  t: (key: string, options?: { defaultValue?: string }) => string
}) {
  const {
    vibeBalance,
    stakeStatus,
    stakedAmount,
    lockedAmount,
    unlockAvailableAt,
    stakeRequired,
    updateStakeInfo,
    setStakeRequired,
  } = useAuthStore()

  const [stakeAmount, setStakeAmount] = useState('100')
  const [isProcessing, setIsProcessing] = useState(false)
  const [countdown, setCountdown] = useState('')

  // Fetch config and balance on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const config = await getStakeConfig()
        setStakeRequired(config.stakeRequired)

        if (isConnected) {
          const balance = await getBalance()
          updateStakeInfo({
            vibeBalance: balance.balance,
            stakedAmount: balance.stakedAmount,
            lockedAmount: balance.lockedAmount,
            stakeStatus: balance.stakeStatus,
            unlockAvailableAt: balance.unlockAvailableAt || null,
          })
        }
      } catch (error) {
        console.error('Failed to fetch stake info:', error)
      }
    }
    fetchData()
  }, [isConnected, setStakeRequired, updateStakeInfo])

  // Update countdown timer for unstaking
  useEffect(() => {
    if (stakeStatus !== 'unstaking' || !unlockAvailableAt) return

    const updateCountdown = () => {
      const now = Date.now() / 1000
      const remaining = unlockAvailableAt - now

      if (remaining <= 0) {
        setCountdown(t('staking.readyToUnlock', { defaultValue: 'Ready to unlock' }))
        return
      }

      const days = Math.floor(remaining / 86400)
      const hours = Math.floor((remaining % 86400) / 3600)
      const minutes = Math.floor((remaining % 3600) / 60)
      setCountdown(`${days}d ${hours}h ${minutes}m`)
    }

    updateCountdown()
    const interval = setInterval(updateCountdown, 60000)
    return () => clearInterval(interval)
  }, [stakeStatus, unlockAvailableAt, t])

  const handleStake = async () => {
    const amount = parseFloat(stakeAmount)
    if (isNaN(amount) || amount < 100) {
      addToast({ type: 'error', message: t('staking.minStake', { defaultValue: 'Minimum stake is 100 VIBE' }) })
      return
    }

    setIsProcessing(true)
    try {
      const result = await stakeTokens(amount)
      if (result.success) {
        const balance = await getBalance()
        updateStakeInfo({
          vibeBalance: balance.balance,
          stakedAmount: balance.stakedAmount,
          stakeStatus: balance.stakeStatus,
        })
        addToast({ type: 'success', message: t('staking.stakeSuccess', { defaultValue: 'Successfully staked!' }) })
      }
    } catch (error) {
      addToast({
        type: 'error',
        message: error instanceof Error ? error.message : t('staking.stakeFailed', { defaultValue: 'Failed to stake' }),
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const handleUnstake = async () => {
    setIsProcessing(true)
    try {
      const result = await requestUnstake()
      if (result.success) {
        const balance = await getBalance()
        updateStakeInfo({
          lockedAmount: balance.lockedAmount,
          stakeStatus: balance.stakeStatus,
          unlockAvailableAt: balance.unlockAvailableAt || null,
        })
        addToast({ type: 'success', message: result.message })
      }
    } catch (error) {
      addToast({
        type: 'error',
        message: error instanceof Error ? error.message : t('staking.unstakeFailed', { defaultValue: 'Failed to unstake' }),
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const handleCancelUnstake = async () => {
    setIsProcessing(true)
    try {
      const result = await cancelUnstake()
      if (result.success) {
        const balance = await getBalance()
        updateStakeInfo({
          lockedAmount: 0,
          stakeStatus: balance.stakeStatus,
          unlockAvailableAt: null,
        })
        addToast({ type: 'success', message: result.message })
      }
    } catch (error) {
      addToast({
        type: 'error',
        message: error instanceof Error ? error.message : t('staking.cancelFailed', { defaultValue: 'Failed to cancel' }),
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const handleConfirmUnstake = async () => {
    setIsProcessing(true)
    try {
      const result = await confirmUnstake()
      if (result.success) {
        const balance = await getBalance()
        updateStakeInfo({
          vibeBalance: balance.balance,
          stakedAmount: 0,
          lockedAmount: 0,
          stakeStatus: balance.stakeStatus,
          unlockAvailableAt: null,
        })
        addToast({ type: 'success', message: result.message })
      }
    } catch (error) {
      addToast({
        type: 'error',
        message: error instanceof Error ? error.message : t('staking.confirmFailed', { defaultValue: 'Failed to confirm' }),
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const getStakeTier = (amount: number) => {
    if (amount >= 1000) return { name: 'Gold', icon: '🥇', color: 'text-yellow-500' }
    if (amount >= 500) return { name: 'Silver', icon: '🥈', color: 'text-gray-400' }
    if (amount >= 100) return { name: 'Bronze', icon: '🥉', color: 'text-orange-400' }
    return { name: 'None', icon: '', color: '' }
  }

  const tier = getStakeTier(stakedAmount)

  if (!isConnected) {
    return (
      <div className="card space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 flex items-center gap-2">
            {t('settings.stakingSettings', { defaultValue: 'Staking Settings' })}
            <HelpIcon content={t('tooltips.staking', { defaultValue: 'Stake VIBE tokens to access all features' })} />
          </h2>
          <p className="text-sm text-light-text-muted dark:text-secondary-400 mt-1">
            {t('settings.stakingSettingsDesc', { defaultValue: 'Manage your VIBE token stake' })}
          </p>
        </div>
        <div className="text-center py-8">
          <Coins size={48} className="mx-auto text-secondary-300 dark:text-secondary-600 mb-4" />
          <p className="text-light-text-muted dark:text-secondary-400">
            {t('staking.connectWallet', { defaultValue: 'Connect wallet to manage staking' })}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="card space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 flex items-center gap-2">
          {t('settings.stakingSettings', { defaultValue: 'Staking Settings' })}
          <HelpIcon content={t('tooltips.staking', { defaultValue: 'Stake VIBE tokens to access all features' })} />
        </h2>
        <p className="text-sm text-light-text-muted dark:text-secondary-400 mt-1">
          {t('settings.stakingSettingsDesc', { defaultValue: 'Manage your VIBE token stake' })}
        </p>
      </div>

      {!stakeRequired && (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700/50">
          <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
            <AlertCircle size={20} />
            <p className="text-sm">{t('staking.disabledMode', { defaultValue: 'Staking requirement is disabled in current mode' })}</p>
          </div>
        </div>
      )}

      {/* Status Card */}
      <div className="p-4 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-light-text-muted dark:text-secondary-400">
              {t('staking.status', { defaultValue: 'Status' })}
            </p>
            <p className="font-semibold text-light-text-primary dark:text-secondary-100 flex items-center gap-2">
              {stakeStatus === 'staked' && <Lock size={16} className="text-green-500" />}
              {stakeStatus === 'unstaking' && <Clock size={16} className="text-yellow-500" />}
              {(stakeStatus === 'none' || stakeStatus === 'unlocked') && <Unlock size={16} className="text-gray-400" />}
              {stakeStatus === 'staked' && t('staking.staked', { defaultValue: 'Staked' })}
              {stakeStatus === 'unstaking' && t('staking.unstaking', { defaultValue: 'Unstaking' })}
              {stakeStatus === 'none' && t('staking.notStaked', { defaultValue: 'Not Staked' })}
              {stakeStatus === 'unlocked' && t('staking.unlocked', { defaultValue: 'Unlocked' })}
            </p>
          </div>
          <div>
            <p className="text-sm text-light-text-muted dark:text-secondary-400">
              {t('staking.stakeTier', { defaultValue: 'Stake Tier' })}
            </p>
            <p className={clsx('font-semibold flex items-center gap-1', tier.color)}>
              {tier.icon} {tier.name}
            </p>
          </div>
          <div>
            <p className="text-sm text-light-text-muted dark:text-secondary-400">
              {t('staking.stakedAmount', { defaultValue: 'Staked Amount' })}
            </p>
            <p className="font-semibold text-light-text-primary dark:text-secondary-100">
              {stakedAmount.toLocaleString()} VIBE
            </p>
          </div>
          <div>
            <p className="text-sm text-light-text-muted dark:text-secondary-400">
              {t('staking.availableBalance', { defaultValue: 'Available Balance' })}
            </p>
            <p className="font-semibold text-light-text-primary dark:text-secondary-100">
              {vibeBalance.toLocaleString()} VIBE
            </p>
          </div>
        </div>

        {stakeStatus === 'unstaking' && (
          <div className="mt-4 pt-4 border-t border-secondary-200 dark:border-secondary-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-light-text-muted dark:text-secondary-400">
                  {t('staking.unlockCountdown', { defaultValue: 'Unlock Countdown' })}
                </p>
                <p className="font-semibold text-yellow-600 dark:text-yellow-400">{countdown}</p>
              </div>
              <p className="text-sm text-light-text-muted dark:text-secondary-400">
                {t('staking.lockedAmount', { defaultValue: 'Locked' })}: {lockedAmount.toLocaleString()} VIBE
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="space-y-4">
        {stakeStatus === 'none' || stakeStatus === 'unlocked' ? (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                {t('staking.stakeAmount', { defaultValue: 'Stake Amount' })}
              </label>
              <div className="relative">
                <input
                  type="number"
                  className="input pr-16"
                  value={stakeAmount}
                  onChange={(e) => setStakeAmount(e.target.value)}
                  min="100"
                  placeholder="100"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-light-text-muted dark:text-secondary-400">
                  VIBE
                </span>
              </div>
              <p className="text-sm text-light-text-muted dark:text-secondary-400 mt-1">
                {t('staking.minStakeHint', { defaultValue: 'Minimum: 100 VIBE' })}
              </p>
            </div>
            <button
              onClick={handleStake}
              disabled={isProcessing}
              className="btn btn-primary w-full"
            >
              {isProcessing ? t('staking.processing', { defaultValue: 'Processing...' }) : t('staking.stakeNow', { defaultValue: 'Stake Now' })}
            </button>
          </div>
        ) : stakeStatus === 'staked' ? (
          <div className="flex gap-3">
            <button
              onClick={handleStake}
              disabled={isProcessing}
              className="btn btn-secondary flex-1"
            >
              {t('staking.addStake', { defaultValue: 'Add Stake' })}
            </button>
            <button
              onClick={handleUnstake}
              disabled={isProcessing}
              className="btn btn-secondary flex-1 text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
            >
              {t('staking.unstake', { defaultValue: 'Unstake' })}
            </button>
          </div>
        ) : stakeStatus === 'unstaking' ? (
          <div className="space-y-3">
            {unlockAvailableAt && Date.now() / 1000 >= unlockAvailableAt ? (
              <button
                onClick={handleConfirmUnstake}
                disabled={isProcessing}
                className="btn btn-primary w-full"
              >
                {t('staking.confirmUnlock', { defaultValue: 'Confirm Unlock' })}
              </button>
            ) : (
              <button
                onClick={handleCancelUnstake}
                disabled={isProcessing}
                className="btn btn-secondary w-full"
              >
                {t('staking.cancelUnstake', { defaultValue: 'Cancel Unstake' })}
              </button>
            )}
          </div>
        ) : null}
      </div>

      {/* Benefits */}
      <div className="mt-6 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
        <h4 className="font-medium text-primary-900 dark:text-primary-100 mb-2">
          {t('staking.benefits', { defaultValue: 'Staking Benefits' })}
        </h4>
        <ul className="text-sm text-primary-800 dark:text-primary-200 space-y-1">
          <li>* {t('staking.benefit1', { defaultValue: 'Publish services and demands' })}</li>
          <li>* {t('staking.benefit2', { defaultValue: 'Register AI Agents' })}</li>
          <li>* {t('staking.benefit3', { defaultValue: 'Participate in collaboration matching' })}</li>
          <li>* {t('staking.benefit4', { defaultValue: 'Governance voting rights' })}</li>
        </ul>
      </div>
    </div>
  )
}

// Helper function to get flag emoji from country code
function getFlagEmoji(countryCode: string): string {
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map((char) => 127397 + char.charCodeAt(0))
  return String.fromCodePoint(...codePoints)
}
