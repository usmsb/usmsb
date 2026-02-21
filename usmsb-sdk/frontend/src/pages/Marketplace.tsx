import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Search, Star, Download, Cpu, Database, Bot, FileCode, Info, Lightbulb, TrendingUp, ChevronDown, ChevronUp, RefreshCw, AlertCircle } from 'lucide-react'
import { getServices, getDemands } from '@/lib/api'
import { toast } from '../stores/toastStore'
import type { ServiceResponse, DemandResponse } from '@/types'
import { parseSkillsArray } from '@/types'
import { EmptyState, Tooltip } from '@/components/ui'

// 应用场景数据 - Use i18n
const getUseCaseExamples = (t: (key: string) => string) => [
  {
    title: t('marketplace.useCase1Title'),
    description: t('marketplace.useCase1Desc'),
    scenario: t('marketplace.useCase1Scenario'),
    outcome: t('marketplace.useCase1Outcome'),
  },
  {
    title: t('marketplace.useCase2Title'),
    description: t('marketplace.useCase2Desc'),
    scenario: t('marketplace.useCase2Scenario'),
    outcome: t('marketplace.useCase2Outcome'),
  },
  {
    title: t('marketplace.useCase3Title'),
    description: t('marketplace.useCase3Desc'),
    scenario: t('marketplace.useCase3Scenario'),
    outcome: t('marketplace.useCase3Outcome'),
  },
]

type MarketplaceCategory = 'all' | 'models' | 'datasets' | 'agents' | 'tools' | 'services' | 'demands'

interface MarketplaceItem {
  id: string
  name: string
  description: string
  category: 'models' | 'datasets' | 'agents' | 'tools' | 'services' | 'demands'
  author: string
  downloads: number
  rating: number
  tags: string[]
  price: number
}

export default function Marketplace() {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<MarketplaceCategory>('all')
  const [showInfo, setShowInfo] = useState(false)

  // Fetch real data from API
  const { data: services, isLoading: servicesLoading, error: servicesError, refetch: refetchServices } = useQuery({
    queryKey: ['services'],
    queryFn: () => getServices(),
  })

  const { data: demands, isLoading: demandsLoading, error: demandsError, refetch: refetchDemands } = useQuery({
    queryKey: ['demands'],
    queryFn: () => getDemands(),
  })

  const isLoading = servicesLoading || demandsLoading
  const hasError = servicesError || demandsError

  // Convert services to marketplace items format
  const serviceItems: MarketplaceItem[] = (services || []).map((s: ServiceResponse) => ({
    id: s.id,
    name: s.service_name,
    description: s.description || '',
    category: 'services' as const,
    author: s.agent_id?.substring(0, 8) || 'Unknown',
    downloads: 0,
    rating: 4.5,
    tags: parseSkillsArray(s.skills),
    price: s.price || 0,
  }))

  // Convert demands to marketplace items format
  const demandItems: MarketplaceItem[] = (demands || []).map((d: DemandResponse) => ({
    id: d.id,
    name: d.title,
    description: d.description || '',
    category: 'demands' as const,
    author: d.agent_id?.substring(0, 8) || 'Unknown',
    downloads: 0,
    rating: 4.5,
    tags: parseSkillsArray(d.required_skills),
    price: d.budget_min || 0,
  }))

  // Combine only real data from services and demands (no mock data)
  const allItems = [...serviceItems, ...demandItems]

  const categories: { value: MarketplaceCategory; label: string; icon: typeof Cpu }[] = [
    { value: 'all', label: t('marketplace.all'), icon: FileCode },
    { value: 'models', label: t('marketplace.models'), icon: Cpu },
    { value: 'datasets', label: t('marketplace.datasets'), icon: Database },
    { value: 'agents', label: t('marketplace.agents'), icon: Bot },
    { value: 'tools', label: t('marketplace.tools'), icon: FileCode },
  ]

  const filteredItems = allItems.filter((item) => {
    const matchesSearch =
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'models':
        return Cpu
      case 'datasets':
        return Database
      case 'agents':
        return Bot
      default:
        return FileCode
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-secondary-900 dark:text-secondary-100">{t('marketplace.title')}</h1>
        <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">
          {t('marketplace.discover')}
        </p>
      </div>

      {/* 概念说明卡片 */}
      <div className="card bg-gradient-to-r from-cyan-50 to-blue-50 dark:from-cyan-900/20 dark:to-blue-900/20 border border-cyan-200 dark:border-cyan-800">
        <button
          onClick={() => setShowInfo(!showInfo)}
          className="w-full flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-cyan-100 dark:bg-cyan-900/30 rounded-lg flex items-center justify-center">
              <Lightbulb className="text-cyan-600 dark:text-cyan-400" size={20} />
            </div>
            <div className="text-left">
              <h3 className="font-semibold text-secondary-900 dark:text-secondary-100">{t('marketplace.whatIsMarketplace')}</h3>
              <p className="text-sm text-secondary-600 dark:text-secondary-400">{t('marketplace.clickToLearnConcepts')}</p>
            </div>
          </div>
          {showInfo ? <ChevronUp size={20} className="text-secondary-400" /> : <ChevronDown size={20} className="text-secondary-400" />}
        </button>

        {showInfo && (
          <div className="mt-6 space-y-6">
            <div>
              <h4 className="font-medium text-secondary-900 dark:text-secondary-100 mb-2 flex items-center gap-2">
                <Info size={16} className="text-cyan-500" />
                {t('marketplace.conceptDefinition')}
              </h4>
              <p className="text-secondary-700 dark:text-secondary-300 leading-relaxed">
                {t('marketplace.conceptDefinitionText')}
              </p>
            </div>

            <div>
              <h4 className="font-medium text-secondary-900 dark:text-secondary-100 mb-2 flex items-center gap-2">
                <TrendingUp size={16} className="text-cyan-500" />
                {t('marketplace.useCases')}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {getUseCaseExamples(t).map((example, idx) => (
                  <div key={idx} className="p-4 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700">
                    <h5 className="font-medium text-secondary-900 dark:text-secondary-100 mb-2">{example.title}</h5>
                    <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-3">{example.description}</p>
                    <div className="text-xs space-y-1">
                      <div className="flex gap-2">
                        <span className="text-secondary-500 dark:text-secondary-400">{t('marketplace.scenario')}:</span>
                        <span className="text-secondary-700 dark:text-secondary-300">{example.scenario}</span>
                      </div>
                      <div className="flex gap-2">
                        <span className="text-secondary-500 dark:text-secondary-400">{t('marketplace.outcome')}:</span>
                        <span className="text-green-600 dark:text-green-400">{example.outcome}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Search and Filters */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Tooltip content={t('placeholders.searchServices', 'Search services (e.g., "web development", "content writing")')} position="right">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary-400 dark:text-secondary-500"
                size={20}
              />
            </Tooltip>
            <input
              type="text"
              placeholder={t('placeholders.searchServices', 'Search services...')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10 dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
            />
          </div>
        </div>
        <div className="flex gap-2 mt-4 overflow-x-auto pb-2">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                selectedCategory === cat.value
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                  : 'bg-secondary-100 dark:bg-secondary-700 text-secondary-600 dark:text-secondary-400 hover:bg-secondary-200 dark:hover:bg-secondary-600'
              }`}
            >
              <cat.icon size={16} />
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Items grid */}
      {isLoading ? (
        <div className="card flex items-center justify-center py-12">
          <RefreshCw className="animate-spin text-primary-500 dark:text-primary-400" size={24} />
          <span className="ml-2 text-secondary-500 dark:text-secondary-400">Loading marketplace items...</span>
        </div>
      ) : hasError ? (
        <div className="card bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
            <AlertCircle size={18} />
            <span>Failed to load marketplace items. Please try again.</span>
          </div>
          <button
            onClick={() => { refetchServices(); refetchDemands(); }}
            className="btn btn-secondary btn-sm mt-3"
          >
            Retry
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredItems.map((item) => {
            const Icon = getCategoryIcon(item.category)
            return (
              <div key={item.id} className="card hover:shadow-md transition-shadow">
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-12 h-12 bg-primary-50 dark:bg-primary-900/30 rounded-xl flex items-center justify-center">
                    <Icon className="text-primary-600 dark:text-primary-400" size={24} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-secondary-900 dark:text-secondary-100 truncate">{item.name}</h3>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('marketplace.by')} {item.author}</p>
                  </div>
                </div>

                <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-4 line-clamp-2">{item.description}</p>

                <div className="flex flex-wrap gap-2 mb-4">
                  {item.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 bg-secondary-100 dark:bg-secondary-700 text-secondary-600 dark:text-secondary-300 text-xs rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-secondary-200 dark:border-secondary-700">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1">
                      <Star className="text-yellow-400 fill-yellow-400" size={16} />
                      <span className="text-sm font-medium text-secondary-700 dark:text-secondary-300">{item.rating}</span>
                    </div>
                    <div className="flex items-center gap-1 text-secondary-500 dark:text-secondary-400">
                      <Download size={16} />
                      <span className="text-sm">{item.downloads.toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {item.price > 0 ? (
                      <span className="text-lg font-bold text-secondary-900 dark:text-secondary-100">${item.price}</span>
                    ) : (
                      <span className="text-sm font-medium text-green-600 dark:text-green-400">Free</span>
                    )}
                  </div>
                </div>

                <button
                  className="btn btn-primary w-full mt-4"
                  onClick={() => {
                    if (item.price > 0) {
                      toast.info(`Purchase ${item.name} for $${item.price}`)
                    } else {
                      toast.success(`Deploying ${item.name}...`)
                    }
                  }}
                >
                  {item.price > 0 ? t('marketplace.purchase') : t('marketplace.deploy')}
                </button>
              </div>
            )
          })}
        </div>
      )}

      {!isLoading && !hasError && filteredItems.length === 0 && (
        <EmptyState
          icon={Search}
          title={t('emptyState.noResults', 'No results found')}
          description={t('emptyState.noResultsDesc', 'Try adjusting your search or filters.')}
          illustration="search"
          secondaryAction={{
            label: t('common.refresh', 'Refresh'),
            onClick: () => { refetchServices(); refetchDemands(); }
          }}
        />
      )}
    </div>
  )
}
