import { useTranslation } from 'react-i18next'
import { Globe, ChevronDown } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

const languages = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'zh', name: '中文', flag: '🇨🇳' },
  { code: 'ja', name: '日本語', flag: '🇯🇵' },
  { code: 'ko', name: '한국어', flag: '🇰🇷' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'pt', name: 'Português', flag: '🇧🇷' },
]

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const currentLang = languages.find((l) => l.code === i18n.language) || languages[0]

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLanguageChange = (code: string) => {
    i18n.changeLanguage(code)
    setIsOpen(false)
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label={`Current language: ${currentLang.name}. Change language`}
        className="flex items-center gap-2 px-3 py-2 text-sm text-light-text-secondary dark:text-secondary-400 hover:text-light-text-primary dark:hover:text-secondary-100 hover:bg-light-bg-tertiary dark:hover:bg-secondary-800 rounded-lg transition-colors"
      >
        <Globe size={18} />
        <span className="hidden sm:inline">{currentLang.flag} {currentLang.name}</span>
        <ChevronDown size={14} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div role="menu" aria-label="Language selection" className="absolute right-0 mt-1 w-40 bg-white dark:bg-cyber-card border border-light-border dark:border-secondary-700 rounded-lg shadow-lg py-1 z-50">
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => handleLanguageChange(lang.code)}
              role="menuitem"
              aria-current={i18n.language === lang.code ? 'true' : undefined}
              className={`w-full flex items-center gap-2 px-4 py-2 text-sm text-left hover:bg-light-bg-tertiary dark:hover:bg-secondary-700 transition-colors ${
                 i18n.language === lang.code ? 'bg-blue-50 text-blue-700 dark:bg-primary-900/30 dark:text-primary-400' : 'text-light-text-secondary dark:text-secondary-300'
              }`}
            >
              <span>{lang.flag}</span>
              <span>{lang.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
