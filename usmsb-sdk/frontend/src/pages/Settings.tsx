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
} from 'lucide-react'
import clsx from 'clsx'
import { useToastStore } from '@/stores/toastStore'
import { useAppStore } from '@/store'
import { useWalletAuth } from '@/hooks/useWalletAuth'
import { useAuthStore } from '@/stores/authStore'
import { HelpIcon } from '@/components/ui'

type SettingsSection = 'general' | 'notifications' | 'appearance' | 'privacy' | 'wallet'

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
          <h1 className="text-xl md:text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            {t('settings.title', 'Settings')}
          </h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">
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
                    : 'text-secondary-600 dark:text-secondary-400 hover:bg-secondary-50 dark:hover:bg-secondary-800'
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
                <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.languageSettings', 'Language Settings')}
                  <HelpIcon content={t('tooltips.languageSwitch', 'Change interface language')} />
                </h2>
                <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-1">
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
                    <span className="font-medium text-secondary-900 dark:text-secondary-100">{lang.name}</span>
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
                <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.notificationSettings', 'Notification Settings')}
                  <HelpIcon content={t('tooltips.notificationSettings', 'Configure notification preferences')} />
                </h2>
                <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-1">
                  {t('settings.notificationSettingsDesc', 'Configure how you receive notifications')}
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-secondary-100 dark:border-secondary-700">
                  <div>
                    <p className="font-medium text-secondary-900 dark:text-secondary-100">
                      {t('settings.emailNotifications', 'Email Notifications')}
                    </p>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">
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
                    <p className="font-medium text-secondary-900 dark:text-secondary-100">
                      {t('settings.pushNotifications', 'Push Notifications')}
                    </p>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">
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
                    <p className="font-medium text-secondary-900 dark:text-secondary-100">
                      {t('settings.weeklyDigest', 'Weekly Digest')}
                    </p>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">
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
                    <p className="font-medium text-secondary-900 dark:text-secondary-100">
                      {t('settings.marketingEmails', 'Marketing Emails')}
                    </p>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">
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
                <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.appearanceSettings', 'Appearance Settings')}
                  <HelpIcon content={t('tooltips.themeToggle', 'Switch between light and dark theme')} />
                </h2>
                <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-1">
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
                    <span className="font-medium text-secondary-900 dark:text-secondary-100">
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
                    <span className="font-medium text-secondary-900 dark:text-secondary-100">
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
                    <span className="font-medium text-secondary-900 dark:text-secondary-100">
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
                <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.privacySettings', 'Privacy Settings')}
                  <HelpIcon content={t('tooltips.privacySettings', 'Control your data and privacy')} />
                </h2>
                <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-1">
                  {t('settings.privacySettingsDesc', 'Control your data and privacy preferences')}
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-secondary-100 dark:border-secondary-700">
                  <div>
                    <p className="font-medium text-secondary-900 dark:text-secondary-100">
                      {t('settings.dataCollection', 'Data Collection')}
                    </p>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">
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
                    <p className="font-medium text-secondary-900 dark:text-secondary-100">
                      {t('settings.analyticsOptIn', 'Analytics')}
                    </p>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">
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
                <p className="text-sm text-secondary-600 dark:text-secondary-400">
                  {t('settings.privacyNote', 'Your privacy is important to us. We only collect data that helps us improve your experience. You can change these settings at any time.')}
                </p>
              </div>
            </div>
          )}

          {/* Wallet Settings */}
          {activeSection === 'wallet' && (
            <div className="card space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 flex items-center gap-2">
                  {t('settings.walletSettings', 'Wallet Settings')}
                  <HelpIcon content={t('tooltips.walletConnect', 'Connect your Web3 wallet to access all features')} />
                </h2>
                <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-1">
                  {t('settings.walletSettingsDesc', 'Manage your connected wallet')}
                </p>
              </div>

              {isConnected && address ? (
                <div className="space-y-4">
                  <div className="p-4 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-secondary-500 dark:text-secondary-400">
                          {t('settings.connectedWallet', 'Connected Wallet')}
                        </p>
                        <p className="font-mono text-lg text-secondary-900 dark:text-secondary-100 mt-1">
                          {truncateAddress(address)}
                        </p>
                        {profileName && (
                          <p className="text-sm text-secondary-500 dark:text-secondary-400 mt-1">
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
                  <p className="text-secondary-500 dark:text-secondary-400">
                    {t('settings.noWalletConnected', 'No wallet connected')}
                  </p>
                  <p className="text-sm text-secondary-400 dark:text-secondary-500 mt-1">
                    {t('settings.connectWalletHint', 'Connect a wallet from the header to manage your account')}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
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
