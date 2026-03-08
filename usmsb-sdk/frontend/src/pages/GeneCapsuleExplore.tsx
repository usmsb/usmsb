import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Search,
  Dna,
  Filter,
  SortAsc,
  SortDesc,
  Grid3X3,
  List,
  Loader2,
  AlertCircle,
  ChevronRight,
  Shield,
} from 'lucide-react'
import clsx from 'clsx'
import { searchAgentsByExperience } from '@/lib/api'
import type { AgentExperienceSearchResult } from '@/types'

type ViewMode = 'grid' | 'list'
type SortBy = 'relevance' | 'tasks' | 'success_rate' | 'satisfaction'

export default function GeneCapsuleExplore() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [searchQuery, setSearchQuery] = useState('')
  const [skillsFilter, setSkillsFilter] = useState<string[]>([])
  const [skillInput, setSkillInput] = useState('')
  const [results, setResults] = useState<AgentExperienceSearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [sortBy, setSortBy] = useState<SortBy>('relevance')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [hasSearched, setHasSearched] = useState(false)

  const handleSearch = async () => {
    if (!searchQuery.trim() && skillsFilter.length === 0) {
      setError(t('geneCapsuleExplore.searchRequired', 'Please enter a search query or add skill filters'))
      return
    }

    setIsLoading(true)
    setError(null)
    setHasSearched(true)

    try {
      const searchResults = await searchAgentsByExperience(
        searchQuery,
        skillsFilter,
        0.2,
        20
      )

      // Sort results
      const sortedResults = sortResults(searchResults)
      setResults(sortedResults)
    } catch (err: any) {
      const errorMessage = err?.message || err?.response?.data?.message || 'Failed to search'
      setError(typeof errorMessage === 'string' ? errorMessage : 'Failed to search agents')
    } finally {
      setIsLoading(false)
    }
  }

  const sortResults = (results: AgentExperienceSearchResult[]) => {
    return [...results].sort((a, b) => {
      let comparison = 0

      switch (sortBy) {
        case 'relevance':
          comparison = a.overall_relevance - b.overall_relevance
          break
        case 'tasks':
          comparison = (a.matched_experiences?.length || 0) - (b.matched_experiences?.length || 1)
          break
        case 'success_rate':
          comparison = (a.total_experience_value || 0) - (b.total_experience_value || 0)
          break
        case 'satisfaction':
          comparison = (a.verified_experiences_count || 0) - (b.verified_experiences_count || 0)
          break
      }

      return sortOrder === 'desc' ? -comparison : comparison
    })
  }

  const addSkillFilter = () => {
    if (skillInput.trim() && !skillsFilter.includes(skillInput.trim())) {
      setSkillsFilter([...skillsFilter, skillInput.trim()])
      setSkillInput('')
    }
  }

  const removeSkillFilter = (skill: string) => {
    setSkillsFilter(skillsFilter.filter(s => s !== skill))
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (skillInput.trim()) {
        addSkillFilter()
      } else {
        handleSearch()
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
            <Dna className="text-purple-600 dark:text-purple-400" size={20} />
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-light-text-primary dark:text-secondary-100">
              {t('geneCapsuleExplore.title', 'Gene Capsule Explorer')}
            </h1>
            <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">
              {t('geneCapsuleExplore.subtitle', 'Discover agents by their experiences, skills, and patterns')}
            </p>
          </div>
        </div>
      </div>

      {/* Search Section */}
      <div className="card">
        <div className="space-y-4">
          {/* Search Input */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-secondary-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={t('geneCapsuleExplore.searchPlaceholder', 'Describe the task or skills you need...')}
                className="w-full bg-white dark:bg-gray-800 border border-light-border dark:border-gray-700 rounded-lg pl-10 pr-4 py-2.5 text-light-text-primary dark:text-secondary-100 placeholder-secondary-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={isLoading}
              className="btn btn-primary flex items-center justify-center gap-2 px-6"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Search className="w-5 h-5" />
              )}
              {t('common.search', 'Search')}
            </button>
          </div>

          {/* Skill Filters */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-secondary-600 dark:text-secondary-400 flex items-center gap-2">
              <Filter className="w-4 h-4" />
              {t('geneCapsuleExplore.skillFilters', 'Required Skills')}
            </label>
            <div className="flex flex-wrap gap-2">
              {skillsFilter.map((skill) => (
                <span
                  key={skill}
                  className="flex items-center gap-1 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-full text-sm"
                >
                  {skill}
                  <button
                    onClick={() => removeSkillFilter(skill)}
                    className="hover:text-red-500 dark:hover:text-red-400 transition-colors"
                  >
                    ×
                  </button>
                </span>
              ))}
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={skillInput}
                  onChange={(e) => setSkillInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder={t('geneCapsuleExplore.addSkill', 'Add skill...')}
                  className="bg-white dark:bg-gray-800 border border-light-border dark:border-gray-700 rounded-lg px-3 py-1 text-sm text-light-text-primary dark:text-secondary-100 placeholder-secondary-400 focus:border-blue-500 focus:outline-none w-32"
                />
                <button
                  onClick={addSkillFilter}
                  disabled={!skillInput.trim()}
                  className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 disabled:opacity-50 disabled:text-secondary-400"
                >
                  + {t('common.add', 'Add')}
                </button>
              </div>
            </div>
          </div>

          {/* View and Sort Options */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-3 border-t border-light-border dark:border-gray-700">
            <div className="flex items-center gap-3 flex-wrap">
              {/* View Mode Toggle */}
              <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('grid')}
                  className={clsx(
                    'p-1.5 rounded transition-colors',
                    viewMode === 'grid'
                      ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                      : 'text-secondary-500 hover:text-secondary-700 dark:hover:text-secondary-300'
                  )}
                >
                  <Grid3X3 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={clsx(
                    'p-1.5 rounded transition-colors',
                    viewMode === 'list'
                      ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                      : 'text-secondary-500 hover:text-secondary-700 dark:hover:text-secondary-300'
                  )}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>

              {/* Sort By */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className="bg-white dark:bg-gray-800 border border-light-border dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm text-light-text-primary dark:text-secondary-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="relevance">{t('geneCapsuleExplore.sortRelevance', 'Relevance')}</option>
                <option value="tasks">{t('geneCapsuleExplore.sortTasks', 'Task Count')}</option>
                <option value="success_rate">{t('geneCapsuleExplore.sortValue', 'Experience Value')}</option>
                <option value="satisfaction">{t('geneCapsuleExplore.sortVerified', 'Verified Count')}</option>
              </select>

              {/* Sort Order */}
              <button
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="p-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-secondary-500 hover:text-secondary-700 dark:hover:text-secondary-300 transition-colors"
              >
                {sortOrder === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
              </button>
            </div>

            {hasSearched && (
              <span className="text-sm text-secondary-500 dark:text-secondary-400">
                {t('geneCapsuleExplore.resultsCount', '{{count}} agents found', { count: results.length })}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="card border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-10 h-10 animate-spin text-blue-500 mb-4" />
          <p className="text-secondary-500 dark:text-secondary-400">{t('common.searching', 'Searching...')}</p>
        </div>
      ) : !hasSearched ? (
        /* Initial State */
        <div className="card">
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
              <Dna className="w-8 h-8 text-secondary-400" />
            </div>
            <h3 className="text-lg font-medium text-light-text-primary dark:text-secondary-100 mb-2">
              {t('geneCapsuleExplore.startTitle', 'Discover Agent Capabilities')}
            </h3>
            <p className="text-secondary-500 dark:text-secondary-400 text-center max-w-md">
              {t('geneCapsuleExplore.startDesc', 'Search for agents based on their experiences, skills, and work patterns. Find the perfect match for your needs.')}
            </p>
          </div>
        </div>
      ) : results.length === 0 ? (
        /* No Results */
        <div className="card">
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
              <Search className="w-8 h-8 text-secondary-400" />
            </div>
            <h3 className="text-lg font-medium text-light-text-primary dark:text-secondary-100 mb-2">
              {t('geneCapsuleExplore.noResults', 'No Agents Found')}
            </h3>
            <p className="text-secondary-500 dark:text-secondary-400 text-center max-w-md">
              {t('geneCapsuleExplore.noResultsDesc', 'Try adjusting your search query or skill filters to find more agents.')}
            </p>
          </div>
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {results.map((result, index) => (
            <AgentCard
              key={result.agent_id || index}
              result={result}
              onClick={() => navigate(`/app/agents/${result.agent_id}`)}
            />
          ))}
        </div>
      ) : (
        /* List View */
        <div className="space-y-3">
          {results.map((result, index) => (
            <AgentListItem
              key={result.agent_id || index}
              result={result}
              onClick={() => navigate(`/app/agents/${result.agent_id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// Agent Card Component (Grid View)
interface AgentCardProps {
  result: AgentExperienceSearchResult
  onClick: () => void
}

function AgentCard({ result, onClick }: AgentCardProps) {
  const { t } = useTranslation()

  const matchedExperiences = result.matched_experiences || []
  const topExperience = matchedExperiences[0]

  return (
    <div
      onClick={onClick}
      className="card cursor-pointer group hover:border-blue-300 dark:hover:border-blue-700 transition-all"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm">
              {(result.agent_name || result.agent_id || 'A').slice(0, 2).toUpperCase()}
            </div>
            <div>
              <h3 className="font-medium text-light-text-primary dark:text-secondary-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                {result.agent_name || result.agent_id?.slice(0, 8) || 'Unknown Agent'}
              </h3>
              <p className="text-xs text-secondary-500 dark:text-secondary-400">
                {result.verified_experiences_count || 0} verified
              </p>
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {(result.overall_relevance * 100).toFixed(0)}%
          </p>
          <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('geneCapsuleExplore.match', 'match')}</p>
        </div>
      </div>

      {/* Top Experience */}
      {topExperience && (
        <div className="mb-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('geneCapsuleExplore.topMatch', 'Top Match')}</p>
          <p className="text-sm text-light-text-primary dark:text-secondary-200 line-clamp-2">
            {topExperience.experience?.task_description || 'N/A'}
          </p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center p-2 bg-gray-50 dark:bg-gray-800/50 rounded">
          <p className="text-lg font-bold text-light-text-primary dark:text-secondary-100">{matchedExperiences.length}</p>
          <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('geneCapsuleExplore.matches', 'Matches')}</p>
        </div>
        <div className="text-center p-2 bg-gray-50 dark:bg-gray-800/50 rounded">
          <p className="text-lg font-bold text-green-600 dark:text-green-400">{result.verified_experiences_count || 0}</p>
          <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('geneCapsuleExplore.verified', 'Verified')}</p>
        </div>
        <div className="text-center p-2 bg-gray-50 dark:bg-gray-800/50 rounded">
          <p className="text-lg font-bold text-yellow-600 dark:text-yellow-400">{(result.total_experience_value || 0).toFixed(0)}</p>
          <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('geneCapsuleExplore.value', 'Value')}</p>
        </div>
      </div>

      {/* Matching Skills */}
      {topExperience?.matching_skills && topExperience.matching_skills.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {topExperience.matching_skills.slice(0, 3).map((skill, idx) => (
            <span key={idx} className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded text-xs">
              {skill}
            </span>
          ))}
          {topExperience.matching_skills.length > 3 && (
            <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-secondary-500 dark:text-secondary-400 rounded text-xs">
              +{topExperience.matching_skills.length - 3}
            </span>
          )}
        </div>
      )}

      {/* View Button */}
      <div className="mt-3 pt-3 border-t border-light-border dark:border-gray-700 flex items-center justify-between">
        <span className="text-sm text-secondary-500 dark:text-secondary-400">{t('geneCapsuleExplore.viewProfile', 'View full profile')}</span>
        <ChevronRight className="w-4 h-4 text-secondary-400 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors" />
      </div>
    </div>
  )
}

// Agent List Item Component (List View)
function AgentListItem({ result, onClick }: AgentCardProps) {
  const { t } = useTranslation()

  const matchedExperiences = result.matched_experiences || []

  return (
    <div
      onClick={onClick}
      className="card cursor-pointer group hover:border-blue-300 dark:hover:border-blue-700 transition-all flex items-center gap-4"
    >
      {/* Avatar */}
      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-base flex-shrink-0">
        {(result.agent_name || result.agent_id || 'A').slice(0, 2).toUpperCase()}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="font-medium text-light-text-primary dark:text-secondary-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors truncate">
            {result.agent_name || result.agent_id?.slice(0, 8) || 'Unknown Agent'}
          </h3>
          {result.verified_experiences_count > 0 && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-xs flex-shrink-0">
              <Shield className="w-3 h-3" />
              {result.verified_experiences_count} verified
            </span>
          )}
        </div>

        <p className="text-sm text-secondary-500 dark:text-secondary-400 mb-2">
          {matchedExperiences.length} matching experiences • Value score: {(result.total_experience_value || 0).toFixed(0)}
        </p>

        {/* Skill Tags */}
        <div className="flex flex-wrap gap-1">
          {matchedExperiences.slice(0, 2).flatMap((exp) =>
            (exp.matching_skills || []).slice(0, 2)
          ).slice(0, 5).map((skill, idx) => (
            <span key={idx} className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-secondary-600 dark:text-secondary-300 rounded text-xs">
              {skill}
            </span>
          ))}
        </div>
      </div>

      {/* Score */}
      <div className="text-right flex-shrink-0">
        <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
          {(result.overall_relevance * 100).toFixed(0)}%
        </p>
        <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('geneCapsuleExplore.relevance', 'relevance')}</p>
      </div>

      {/* Arrow */}
      <ChevronRight className="w-5 h-5 text-secondary-400 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors flex-shrink-0" />
    </div>
  )
}
