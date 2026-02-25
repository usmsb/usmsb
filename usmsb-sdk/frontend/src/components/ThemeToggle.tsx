import { useTranslation } from 'react-i18next'
import { Sun, Moon, Monitor } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '@/store'
import clsx from 'clsx'

type ThemeMode = 'light' | 'dark' | 'system'

export default function ThemeToggle() {
  const { t } = useTranslation()
  const { themeMode, theme, setThemeMode } = useAppStore()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const themeOptions: { mode: ThemeMode; icon: typeof Sun; label: string }[] = [
    { mode: 'light', icon: Sun, label: t('settings.light', 'Light') },
    { mode: 'dark', icon: Moon, label: t('settings.dark', 'Dark') },
    { mode: 'system', icon: Monitor, label: t('settings.system', 'System') },
  ]

  const CurrentIcon = themeMode === 'system' ? Monitor : theme === 'light' ? Sun : Moon

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label={t('settings.toggleTheme', 'Toggle theme')}
        aria-expanded={isOpen}
        className={clsx(
          'p-2 rounded-lg transition-colors',
          'text-light-text-muted hover:bg-light-bg-tertiary',
          'dark:text-secondary-400 dark:hover:bg-secondary-700'
        )}
      >
        <CurrentIcon size={20} />
      </button>

      {isOpen && (
        <div
          role="menu"
          aria-label={t('settings.themeOptions', 'Theme options')}
          className={clsx(
            'absolute right-0 top-full mt-2 w-36 rounded-lg shadow-lg border py-1 z-50',
            'bg-white border-light-border',
            'dark:bg-secondary-800 dark:border-secondary-700'
          )}
        >
          {themeOptions.map(({ mode, icon: Icon, label }) => (
            <button
              key={mode}
              role="menuitem"
              onClick={() => {
                setThemeMode(mode)
                setIsOpen(false)
              }}
              className={clsx(
                'w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors',
                themeMode === mode
                  ? 'bg-blue-50 text-blue-700 dark:bg-primary-900/30 dark:text-primary-400'
                  : 'text-light-text-secondary hover:bg-light-bg-tertiary dark:text-secondary-300 dark:hover:bg-secondary-700/50'
              )}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
