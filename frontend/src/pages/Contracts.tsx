import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  FileCode,
  ExternalLink,
  Copy,
  Check,
  Search,
  Filter,
  Globe,
  Clock,
  Wallet,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import clsx from 'clsx'
import {
  deploymentData,
  getCategoryColor,
  getCategoryLabel,
  type ContractInfo,
} from '@/data/contracts'

export default function Contracts() {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [copiedAddress, setCopiedAddress] = useState<string | null>(null)
  const [expandedContract, setExpandedContract] = useState<string | null>(null)

  const categories = ['all', 'core', 'token', 'staking', 'governance', 'rewards', 'infrastructure']

  // Filter contracts
  const filteredContracts = deploymentData.contracts.filter((contract) => {
    const matchesSearch =
      contract.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      contract.address.toLowerCase().includes(searchQuery.toLowerCase()) ||
      contract.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = selectedCategory === 'all' || contract.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  // Group contracts by category
  const contractsByCategory = deploymentData.contracts.reduce(
    (acc, contract) => {
      if (!acc[contract.category]) {
        acc[contract.category] = []
      }
      acc[contract.category].push(contract)
      return acc
    },
    {} as Record<string, ContractInfo[]>
  )

  // Copy address to clipboard
  const copyAddress = (address: string) => {
    navigator.clipboard.writeText(address)
    setCopiedAddress(address)
    setTimeout(() => setCopiedAddress(null), 2000)
  }

  // Open in explorer
  const openInExplorer = (address: string) => {
    window.open(`${deploymentData.explorerUrl}/address/${address}`, '_blank')
  }

  // Format timestamp
  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-light-text-primary dark:text-secondary-100">
            {t('contracts.title', 'Smart Contracts')}
          </h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">
            {t('contracts.subtitle', 'Deployed smart contracts on VIBE Protocol')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={deploymentData.explorerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary flex items-center gap-2"
          >
            <Globe size={18} />
            <span className="hidden sm:inline">{t('contracts.openExplorer', 'Explorer')}</span>
          </a>
        </div>
      </div>

      {/* Network Info Card */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Globe className="text-blue-600 dark:text-blue-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('contracts.network', 'Network')}</p>
              <p className="font-medium text-light-text-primary dark:text-secondary-100">
                {deploymentData.networkName}
              </p>
            </div>
          </div>
          <div className="h-10 w-px bg-secondary-200 dark:bg-secondary-700" />
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <Wallet className="text-purple-600 dark:text-purple-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('contracts.deployer', 'Deployer')}</p>
              <p className="font-mono text-sm text-light-text-primary dark:text-secondary-100">
                {deploymentData.deployer.slice(0, 10)}...{deploymentData.deployer.slice(-8)}
              </p>
            </div>
          </div>
          <div className="h-10 w-px bg-secondary-200 dark:bg-secondary-700" />
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <Clock className="text-green-600 dark:text-green-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('contracts.deployedAt', 'Deployed')}</p>
              <p className="font-medium text-light-text-primary dark:text-secondary-100">
                {formatDate(deploymentData.timestamp)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats - Category counts */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {categories.slice(1).map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat === selectedCategory ? 'all' : cat)}
            className={clsx(
              'card text-left transition-all',
              selectedCategory === cat
                ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'hover:border-blue-400'
            )}
          >
            <div className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">
              {contractsByCategory[cat]?.length || 0}
            </div>
            <div className="text-sm text-secondary-500 dark:text-secondary-400">
              {t(`contracts.categories.${cat}`, getCategoryLabel(cat))}
            </div>
          </button>
        ))}
      </div>

      {/* Search and Filter */}
      <div className="card">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary-400 dark:text-secondary-500" size={20} />
            <input
              type="text"
              placeholder={t('contracts.search', 'Search contracts...')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input w-full pl-10"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter size={20} className="text-secondary-400 dark:text-secondary-500" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="input"
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat === 'all' ? t('contracts.allCategories', 'All Categories') : t(`contracts.categories.${cat}`, getCategoryLabel(cat))}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Contracts List */}
      <div className="space-y-3">
        {filteredContracts.map((contract) => (
          <div
            key={contract.name}
            className={clsx(
              'card transition-all cursor-pointer',
              expandedContract === contract.name
                ? 'ring-2 ring-blue-500'
                : 'hover:border-blue-400'
            )}
            onClick={() =>
              setExpandedContract(expandedContract === contract.name ? null : contract.name)
            }
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {/* Category Badge */}
                <span
                  className={clsx(
                    'px-3 py-1 rounded-full text-xs font-medium',
                    getCategoryColor(contract.category) === 'blue' &&
                      'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
                    getCategoryColor(contract.category) === 'purple' &&
                      'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
                    getCategoryColor(contract.category) === 'green' &&
                      'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
                    getCategoryColor(contract.category) === 'yellow' &&
                      'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
                    getCategoryColor(contract.category) === 'orange' &&
                      'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
                    getCategoryColor(contract.category) === 'cyan' &&
                      'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300'
                  )}
                >
                  {t(`contracts.categories.${contract.category}`, getCategoryLabel(contract.category))}
                </span>

                {/* Contract Name */}
                <h3 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100">
                  {contract.name}
                </h3>
              </div>

              <div className="flex items-center gap-3">
                {/* Address */}
                <div className="hidden md:flex items-center gap-2">
                  <code className="text-sm text-secondary-500 dark:text-secondary-400 font-mono">
                    {contract.address.slice(0, 10)}...{contract.address.slice(-8)}
                  </code>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      copyAddress(contract.address)
                    }}
                    className="p-1.5 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded-lg transition-colors"
                  >
                    {copiedAddress === contract.address ? (
                      <Check className="w-4 h-4 text-green-500" size={16} />
                    ) : (
                      <Copy className="w-4 h-4 text-secondary-400 dark:text-secondary-500" size={16} />
                    )}
                  </button>
                </div>

                {/* View on Explorer Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    openInExplorer(contract.address)
                  }}
                  className="btn btn-primary flex items-center gap-1.5 text-sm"
                >
                  <ExternalLink size={16} />
                  <span className="hidden sm:inline">{t('contracts.view', 'View')}</span>
                </button>

                {/* Expand Icon */}
                {expandedContract === contract.name ? (
                  <ChevronUp className="w-5 h-5 text-secondary-400 dark:text-secondary-500" size={20} />
                ) : (
                  <ChevronDown className="w-5 h-5 text-secondary-400 dark:text-secondary-500" size={20} />
                )}
              </div>
            </div>

            {/* Mobile Address */}
            <div className="md:hidden mt-3 flex items-center gap-2">
              <code className="text-sm text-secondary-500 dark:text-secondary-400 font-mono">
                {contract.address}
              </code>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  copyAddress(contract.address)
                }}
                className="p-1.5 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded-lg transition-colors"
              >
                {copiedAddress === contract.address ? (
                  <Check className="w-4 h-4 text-green-500" size={16} />
                ) : (
                  <Copy className="w-4 h-4 text-secondary-400 dark:text-secondary-500" size={16} />
                )}
              </button>
            </div>

            {/* Expanded Details */}
            {expandedContract === contract.name && (
              <div className="mt-4 pt-4 border-t border-secondary-200 dark:border-secondary-700">
                <div className="space-y-3">
                  <p className="text-secondary-600 dark:text-secondary-400">{contract.description}</p>
                  <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                    <span className="text-sm text-secondary-500 dark:text-secondary-400">{t('contracts.fullAddress', 'Full Address')}:</span>
                    <code className="text-sm bg-secondary-100 dark:bg-secondary-800 px-3 py-1.5 rounded font-mono break-all">
                      {contract.address}
                    </code>
                    <button
                      onClick={() => copyAddress(contract.address)}
                      className="p-1.5 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded-lg transition-colors"
                    >
                      {copiedAddress === contract.address ? (
                        <Check className="w-4 h-4 text-green-500" size={16} />
                      ) : (
                        <Copy className="w-4 h-4 text-secondary-400 dark:text-secondary-500" size={16} />
                      )}
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <a
                      href={`${deploymentData.explorerUrl}/address/${contract.address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-primary flex items-center gap-1.5 text-sm"
                    >
                      <Globe size={16} />
                      {t('contracts.viewOnExplorer', 'View on BaseScan')}
                    </a>
                    <a
                      href={`${deploymentData.explorerUrl}/tx?a=${contract.address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary flex items-center gap-1.5 text-sm"
                    >
                      <FileCode size={16} />
                      {t('contracts.viewTxs', 'View Transactions')}
                    </a>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* No Results */}
      {filteredContracts.length === 0 && (
        <div className="card text-center py-12">
          <FileCode className="w-16 h-16 mx-auto text-secondary-300 dark:text-secondary-600 mb-4" size={64} />
          <p className="text-secondary-500 dark:text-secondary-400">{t('contracts.noResults', 'No contracts found matching your criteria')}</p>
        </div>
      )}
    </div>
  )
}
