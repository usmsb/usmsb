import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { HelpCircle, X, Book, MessageCircle, ExternalLink, ChevronRight, Search } from 'lucide-react'
import clsx from 'clsx'

interface HelpItem {
  id: string
  title: string
  description: string
  category: 'getting-started' | 'features' | 'account' | 'troubleshooting'
}

const helpItems: HelpItem[] = [
  {
    id: 'what-is-usmsb',
    title: 'What is USMSB?',
    description: 'Learn about the Silicon-based Civilization Society platform and its mission.',
    category: 'getting-started',
  },
  {
    id: 'connect-wallet',
    title: 'How to connect wallet?',
    description: 'Step-by-step guide to connect your Web3 wallet and create your identity.',
    category: 'getting-started',
  },
  {
    id: 'register-agent',
    title: 'Register an AI Agent',
    description: 'Learn how to register your AI Agent with different protocols (MCP, A2A, Skills.md).',
    category: 'features',
  },
  {
    id: 'marketplace',
    title: 'Using the Marketplace',
    description: 'Discover how to publish services and find AI services on the marketplace.',
    category: 'features',
  },
  {
    id: 'theme-settings',
    title: 'Theme Settings',
    description: 'Customize your experience with light/dark mode and other appearance options.',
    category: 'account',
  },
  {
    id: 'wallet-issues',
    title: 'Wallet Connection Issues',
    description: 'Troubleshoot common wallet connection problems.',
    category: 'troubleshooting',
  },
]

interface HelpPanelProps {
  isOpen: boolean
  onClose: () => void
}

export function HelpPanel({ isOpen, onClose }: HelpPanelProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [selectedItem, setSelectedItem] = useState<HelpItem | null>(null)

  const filteredItems = helpItems.filter((item) => {
    const matchesSearch =
      searchQuery === '' ||
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = activeCategory === null || item.category === activeCategory
    return matchesSearch && matchesCategory
  })

  const categories = [
    { id: 'getting-started', label: t('help.gettingStarted', 'Getting Started'), icon: Book },
    { id: 'features', label: t('help.features', 'Features'), icon: MessageCircle },
    { id: 'account', label: t('help.account', 'Account'), icon: HelpCircle },
    { id: 'troubleshooting', label: t('help.troubleshooting', 'Troubleshooting'), icon: HelpCircle },
  ]

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[9998] flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative w-full max-w-md h-full bg-white dark:bg-cyber-card shadow-2xl animate-slide-in-right overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-light-border dark:border-secondary-700">
          <div className="flex items-center gap-2">
            <HelpCircle className="text-primary-600 dark:text-primary-400" size={20} />
            <h2 className="font-semibold text-light-text-primary dark:text-white">
              {t('help.title', 'Help Center')}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-light-bg-tertiary dark:hover:bg-secondary-700"
          >
            <X size={20} className="text-light-text-muted dark:text-secondary-400" />
          </button>
        </div>

        {/* Search */}
        <div className="p-4 border-b border-light-border dark:border-secondary-700">
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-light-text-muted"
              size={18}
            />
            <input
              type="text"
              placeholder={t('help.searchPlaceholder', 'Search help topics...')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-light-border dark:border-secondary-600 rounded-lg bg-light-bg-tertiary dark:bg-secondary-700 text-light-text-primary dark:text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {selectedItem ? (
            <div className="p-4">
              <button
                onClick={() => setSelectedItem(null)}
                className="flex items-center gap-1 text-sm text-primary-600 dark:text-primary-400 mb-4"
              >
                <ChevronRight size={16} className="rotate-180" />
                {t('common.back', 'Back')}
              </button>
              <h3 className="text-lg font-semibold text-light-text-primary dark:text-white mb-3">
                {selectedItem.title}
              </h3>
              <p className="text-light-text-secondary dark:text-secondary-400 mb-4">
                {selectedItem.description}
              </p>
              <div className="p-4 bg-light-bg-tertiary dark:bg-secondary-700/50 rounded-lg">
                <p className="text-sm text-light-text-secondary dark:text-secondary-400">
                  {t('help.detailedHelp', 'Detailed help content will be available here.')}
                </p>
              </div>
            </div>
          ) : (
            <div className="p-4">
              {/* Categories */}
              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  onClick={() => setActiveCategory(null)}
                  className={clsx(
                    'px-3 py-1.5 text-sm rounded-full transition-colors',
                    activeCategory === null
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'bg-light-bg-tertiary dark:bg-secondary-700 text-light-text-secondary dark:text-secondary-400'
                  )}
                >
                  {t('help.all', 'All')}
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => setActiveCategory(cat.id)}
                    className={clsx(
                      'px-3 py-1.5 text-sm rounded-full transition-colors flex items-center gap-1',
                      activeCategory === cat.id
                        ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                        : 'bg-light-bg-tertiary dark:bg-secondary-700 text-light-text-secondary dark:text-secondary-400'
                    )}
                  >
                    <cat.icon size={14} />
                    {cat.label}
                  </button>
                ))}
              </div>

              {/* Help items */}
              <div className="space-y-2">
                {filteredItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className="w-full p-3 text-left rounded-lg border border-light-border dark:border-secondary-700 hover:border-primary-300 dark:hover:border-primary-600 hover:bg-light-bg-tertiary dark:hover:bg-secondary-700/50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-light-text-primary dark:text-white">
                          {item.title}
                        </h4>
                        <p className="text-sm text-light-text-muted dark:text-secondary-400">
                          {item.description}
                        </p>
                      </div>
                      <ChevronRight size={18} className="text-light-text-muted" />
                    </div>
                  </button>
                ))}
              </div>

              {filteredItems.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-secondary-500 dark:text-secondary-400">
                    {t('help.noResults', 'No results found')}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-light-border dark:border-secondary-700 bg-light-bg-secondary dark:bg-secondary-700/50">
          <div className="flex items-center justify-between text-sm">
            <a
              href="/docs"
              className="flex items-center gap-1 text-primary-600 dark:text-primary-400 hover:underline"
            >
              <Book size={16} />
              {t('help.viewDocs', 'View Docs')}
            </a>
            <a
              href="https://github.com/usmsb/usmsb"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-secondary-600 dark:text-secondary-400 hover:underline"
            >
              <ExternalLink size={16} />
              {t('help.community', 'Community')}
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

// Help button component to be placed in headers
interface HelpButtonProps {
  onClick: () => void
  className?: string
}

export function HelpButton({ onClick, className }: HelpButtonProps) {
  const { t } = useTranslation()

  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center gap-1.5 px-3 py-2 rounded-lg',
        'text-secondary-600 dark:text-secondary-400',
        'hover:bg-secondary-100 dark:hover:bg-secondary-700',
        'transition-colors',
        className
      )}
      title={t('help.openHelp', 'Open Help Center')}
    >
      <HelpCircle size={18} />
      <span className="hidden sm:inline">{t('help.help', 'Help')}</span>
    </button>
  )
}
