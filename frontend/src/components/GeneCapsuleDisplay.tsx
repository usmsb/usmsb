import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Dna,
  RefreshCw,
  Loader2,
  AlertCircle,
  Clock,
  Zap,
  Target,
  TrendingUp,
  Award,
  Eye,
  EyeOff,
  Star,
  Briefcase,
  Lightbulb,
  CheckCircle,
  XCircle,
  Shield,
  Plus,
  Search,
} from 'lucide-react'
import {
  getGeneCapsule,
  getGeneCapsuleSummary,
  searchAgentsByExperience,
  updateExperienceVisibility,
} from '@/lib/api'
import type {
  GeneCapsule,
  GeneCapsuleSummary,
  ExperienceGene,
  SkillGene,
  PatternGene,
  ShareLevel,
} from '@/types'
import clsx from 'clsx'

interface GeneCapsuleDisplayProps {
  agentId: string
  showSearch?: boolean
  onExperienceSelect?: (experience: ExperienceGene) => void
}

const SHARE_LEVEL_CONFIG: Record<ShareLevel, { label: string; color: string; icon: typeof Eye }> = {
  public: { label: 'Public', color: '#10b981', icon: Eye },
  semi_public: { label: 'Semi-Public', color: '#3b82f6', icon: Eye },
  private: { label: 'Private', color: '#f59e0b', icon: EyeOff },
  hidden: { label: 'Hidden', color: '#6b7280', icon: EyeOff },
}

const PROFICIENCY_COLORS: Record<string, string> = {
  basic: '#6b7280',
  intermediate: '#3b82f6',
  advanced: '#8b5cf6',
  expert: '#f59e0b',
  master: '#10b981',
}

const OUTCOME_CONFIG: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  success: { label: 'Success', color: '#10b981', icon: CheckCircle },
  partial: { label: 'Partial', color: '#f59e0b', icon: TrendingUp },
  failed: { label: 'Failed', color: '#ef4444', icon: XCircle },
}

export function GeneCapsuleDisplay({
  agentId,
  showSearch = false,
  onExperienceSelect,
}: GeneCapsuleDisplayProps) {
  const { t } = useTranslation()
  const [capsule, setCapsule] = useState<GeneCapsule | null>(null)
  const [summary, setSummary] = useState<GeneCapsuleSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'experiences' | 'skills' | 'patterns'>('experiences')
  const [showSearchPanel, setShowSearchPanel] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)

  useEffect(() => {
    loadCapsule()
  }, [agentId])

  const loadCapsule = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [capsuleData, summaryData] = await Promise.all([
        getGeneCapsule(agentId),
        getGeneCapsuleSummary(agentId),
      ])
      setCapsule(capsuleData)
      setSummary(summaryData)
    } catch (err: any) {
      const errorMessage = err?.message || err?.response?.data?.message || 'Failed to load gene capsule'
      setError(typeof errorMessage === 'string' ? errorMessage : 'Failed to load gene capsule')
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggleVisibility = async (geneId: string, currentLevel: ShareLevel) => {
    const levels: ShareLevel[] = ['private', 'semi_public', 'public', 'hidden']
    const currentIndex = levels.indexOf(currentLevel)
    const nextLevel = levels[(currentIndex + 1) % levels.length]

    try {
      await updateExperienceVisibility(agentId, geneId, nextLevel)
      await loadCapsule()
    } catch (err) {
      console.error('Failed to update visibility:', err)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    setIsSearching(true)
    try {
      const results = await searchAgentsByExperience(searchQuery, [], 0.3, 5)
      setSearchResults(results)
    } catch (err) {
      console.error('Search failed:', err)
    } finally {
      setIsSearching(false)
    }
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleDateString()
  }

  const formatTime = (seconds: number) => {
    if (!seconds) return ''
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  }

  // Helper to get data from capsule (supports both naming conventions)
  const getExperiences = () => capsule?.experiences || capsule?.experience_genes || []
  const getSkills = () => capsule?.skills || capsule?.skill_genes || []
  const getPatterns = () => capsule?.patterns || capsule?.pattern_genes || []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        <span className="ml-2 text-secondary-500 dark:text-secondary-400">{t('common.loading', 'Loading...')}</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        <span>{error}</span>
      </div>
    )
  }

  return (
    <div className="card space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
            <Dna className="w-4 h-4 text-purple-600 dark:text-purple-400" />
          </div>
          <h3 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100">
            {t('geneCapsule.title', 'Gene Capsule')}
          </h3>
          {summary && (
            <span className="text-xs text-secondary-400 dark:text-secondary-500 ml-2">v{summary.version}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {showSearch && (
            <button
              onClick={() => setShowSearchPanel(!showSearchPanel)}
              className={clsx(
                'p-2 rounded-lg transition-colors',
                showSearchPanel
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-200'
              )}
            >
              <Search className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={loadCapsule}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-200"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Briefcase className="w-4 h-4 text-blue-500 dark:text-blue-400" />
            </div>
            <p className="text-xl font-bold text-light-text-primary dark:text-secondary-100">{summary.total_tasks}</p>
            <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('geneCapsule.tasks', 'Tasks')}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <TrendingUp className="w-4 h-4 text-green-500 dark:text-green-400" />
            </div>
            <p className="text-xl font-bold text-green-600 dark:text-green-400">{summary.success_rate}%</p>
            <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('geneCapsule.successRate', 'Success')}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Star className="w-4 h-4 text-yellow-500 dark:text-yellow-400" />
            </div>
            <p className="text-xl font-bold text-yellow-600 dark:text-yellow-400">{summary.avg_satisfaction}</p>
            <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('geneCapsule.satisfaction', 'Rating')}</p>
          </div>
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Lightbulb className="w-4 h-4 text-purple-500 dark:text-purple-400" />
            </div>
            <p className="text-xl font-bold text-purple-600 dark:text-purple-400">{summary.patterns_count}</p>
            <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('geneCapsule.patterns', 'Patterns')}</p>
          </div>
        </div>
      )}

      {/* Category Breakdown */}
      {summary && Object.keys(summary.categories).length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-secondary-600 dark:text-secondary-400">{t('geneCapsule.categories', 'Categories')}</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(summary.categories).map(([category, count]) => (
              <div
                key={category}
                className="px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-full text-xs text-secondary-600 dark:text-secondary-300"
              >
                {category}: {count}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search Panel */}
      {showSearchPanel && (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('geneCapsule.searchPlaceholder', 'Search agents by experience...')}
              className="flex-1 bg-white dark:bg-gray-700 border border-light-border dark:border-gray-600 rounded-lg px-3 py-2 text-light-text-primary dark:text-secondary-100 text-sm focus:outline-none focus:border-blue-500"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="btn btn-primary px-4 py-2"
            >
              {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            </button>
          </div>

          {searchResults.length > 0 && (
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {searchResults.map((result, idx) => (
                <div
                  key={idx}
                  className="bg-white dark:bg-gray-700/50 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-light-text-primary dark:text-secondary-100">
                        {result.agent_name || result.agent_id.slice(0, 8)}
                      </p>
                      <p className="text-xs text-secondary-500 dark:text-secondary-400">
                        {result.matched_experiences.length} matching experiences
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-blue-600 dark:text-blue-400">
                        {(result.overall_relevance * 100).toFixed(0)}%
                      </p>
                      <p className="text-xs text-secondary-400 dark:text-secondary-500">relevance</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
        {(['experiences', 'skills', 'patterns'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors',
              activeTab === tab
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-secondary-500 hover:text-secondary-700 dark:hover:text-secondary-300 hover:bg-gray-50 dark:hover:bg-gray-700/50'
            )}
          >
            {tab === 'experiences' && t('geneCapsule.experiences', 'Experiences')}
            {tab === 'skills' && t('geneCapsule.skills', 'Skills')}
            {tab === 'patterns' && t('geneCapsule.patternsTab', 'Patterns')}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-[200px]">
        {/* Experiences Tab */}
        {activeTab === 'experiences' && (
          <div className="space-y-3">
            {getExperiences().length === 0 ? (
              <EmptyState
                icon={Briefcase}
                title={t('geneCapsule.noExperiences', 'No Experiences Yet')}
                description={t('geneCapsule.noExperiencesDesc', 'Complete tasks to build your experience portfolio')}
                actionLabel={t('geneCapsule.addExperience', 'Add Experience')}
                onAction={() => {/* TODO: Open add experience modal */}}
              />
            ) : (
              getExperiences().map((exp: any) => (
                <ExperienceCard
                  key={exp.gene_id || exp.id}
                  experience={exp}
                  onToggleVisibility={() => handleToggleVisibility(exp.gene_id || exp.id, exp.share_level as ShareLevel)}
                  onClick={() => onExperienceSelect?.(exp)}
                  formatDate={formatDate}
                  formatTime={formatTime}
                />
              ))
            )}
          </div>
        )}

        {/* Skills Tab */}
        {activeTab === 'skills' && (
          <div className="space-y-3">
            {getSkills().length === 0 ? (
              <EmptyState
                icon={Zap}
                title={t('geneCapsule.noSkills', 'No Skills Yet')}
                description={t('geneCapsule.noSkillsDesc', 'Skills are automatically extracted from your experiences')}
              />
            ) : (
              getSkills().map((skill: any) => (
                <SkillCard key={skill.skill_id || skill.id} skill={skill} />
              ))
            )}
          </div>
        )}

        {/* Patterns Tab */}
        {activeTab === 'patterns' && (
          <div className="space-y-3">
            {getPatterns().length === 0 ? (
              <EmptyState
                icon={Lightbulb}
                title={t('geneCapsule.noPatterns', 'No Patterns Yet')}
                description={t('geneCapsule.noPatternsDesc', 'Patterns emerge from repeated successful approaches')}
              />
            ) : (
              getPatterns().map((pattern: any) => (
                <PatternCard key={pattern.pattern_id || pattern.id} pattern={pattern} />
              ))
            )}
          </div>
        )}
      </div>

      {/* Top Skills Summary */}
      {summary && summary.top_skills.length > 0 && activeTab !== 'skills' && (
        <div className="space-y-2 pt-2 border-t border-light-border dark:border-gray-700">
          <p className="text-sm font-medium text-secondary-600 dark:text-secondary-400">{t('geneCapsule.topSkills', 'Top Skills')}</p>
          <div className="flex flex-wrap gap-2">
            {summary.top_skills.map((skill, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 px-3 py-1 rounded-full text-xs"
                style={{
                  backgroundColor: `${PROFICIENCY_COLORS[skill.level] || '#6b7280'}20`,
                  color: PROFICIENCY_COLORS[skill.level] || '#6b7280',
                }}
              >
                <span>{skill.name}</span>
                <span className="opacity-60">({skill.times_used})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Last Updated */}
      {summary && (
        <div className="flex items-center justify-end text-xs text-secondary-400 dark:text-secondary-500 pt-2 border-t border-light-border dark:border-gray-700">
          <Clock className="w-3 h-3 mr-1" />
          {t('geneCapsule.lastUpdated', 'Updated')}: {formatDate(summary.last_updated)}
        </div>
      )}
    </div>
  )
}

// Experience Card Component
interface ExperienceCardProps {
  experience: ExperienceGene
  onToggleVisibility: () => void
  onClick?: () => void
  formatDate: (date: string) => string
  formatTime: (seconds: number) => string
}

// Empty State Component
interface EmptyStateProps {
  icon: typeof Briefcase
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}

function EmptyState({ icon: Icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-secondary-400" />
      </div>
      <h4 className="text-lg font-medium text-light-text-primary dark:text-secondary-100 mb-2">{title}</h4>
      {description && (
        <p className="text-sm text-secondary-500 dark:text-secondary-400 text-center max-w-sm mb-4">{description}</p>
      )}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="flex items-center gap-2 px-4 py-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
        >
          <Plus className="w-4 h-4" />
          {actionLabel}
        </button>
      )}
    </div>
  )
}

function ExperienceCard({ experience, onToggleVisibility, onClick, formatDate, formatTime }: ExperienceCardProps) {
  const { t } = useTranslation()
  const outcomeConfig = OUTCOME_CONFIG[experience.outcome] || OUTCOME_CONFIG.partial
  const shareConfig = SHARE_LEVEL_CONFIG[experience.share_level as ShareLevel] || SHARE_LEVEL_CONFIG.private
  const OutcomeIcon = outcomeConfig.icon
  const ShareIcon = shareConfig.icon

  return (
    <div
      onClick={onClick}
      className={clsx(
        'bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 transition-colors',
        onClick && 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700/50'
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-200 dark:bg-gray-700 text-secondary-600 dark:text-secondary-300">
              {experience.task_category}
            </span>
            <span
              className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
              style={{ backgroundColor: `${outcomeConfig.color}20`, color: outcomeConfig.color }}
            >
              <OutcomeIcon className="w-3 h-3" />
              {outcomeConfig.label}
            </span>
            {experience.verified && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400">
                <Shield className="w-3 h-3" />
                {t('geneCapsule.verified', 'Verified')}
              </span>
            )}
          </div>
          <p className="text-sm text-light-text-primary dark:text-secondary-100">{experience.task_description}</p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onToggleVisibility()
          }}
          className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          title={`Visibility: ${shareConfig.label}`}
        >
          <ShareIcon className="w-4 h-4" style={{ color: shareConfig.color }} />
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-2">
        {experience.techniques_used.slice(0, 3).map((tech, idx) => (
          <span key={idx} className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded text-xs">
            {tech}
          </span>
        ))}
        {experience.techniques_used.length > 3 && (
          <span className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-secondary-500 dark:text-secondary-400 rounded text-xs">
            +{experience.techniques_used.length - 3}
          </span>
        )}
      </div>

      <div className="flex items-center gap-4 text-xs text-secondary-500 dark:text-secondary-400">
        <div className="flex items-center gap-1">
          <Star className="w-3 h-3 text-yellow-500 dark:text-yellow-400" />
          <span>{(experience.quality_score * 100).toFixed(0)}%</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          <span>{formatTime(experience.completion_time)}</span>
        </div>
        {experience.client_rating && (
          <div className="flex items-center gap-1">
            <Award className="w-3 h-3 text-yellow-500 dark:text-yellow-400" />
            <span>{experience.client_rating}/5</span>
          </div>
        )}
        <div className="ml-auto">
          {formatDate(experience.created_at)}
        </div>
      </div>
    </div>
  )
}

// Skill Card Component
interface SkillCardProps {
  skill: SkillGene
}

function SkillCard({ skill }: SkillCardProps) {
  const { t } = useTranslation()
  const proficiencyColor = PROFICIENCY_COLORS[skill.proficiency_level] || '#6b7280'
  const successRate = skill.times_used > 0 ? (skill.success_count / skill.times_used) * 100 : 0

  return (
    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4" style={{ color: proficiencyColor }} />
          <span className="font-medium text-light-text-primary dark:text-secondary-100">{skill.skill_name}</span>
        </div>
        <span
          className="px-2 py-0.5 rounded text-xs font-medium capitalize"
          style={{ backgroundColor: `${proficiencyColor}20`, color: proficiencyColor }}
        >
          {skill.proficiency_level}
        </span>
      </div>

      <div className="flex items-center gap-4 text-sm text-secondary-500 dark:text-secondary-400 mb-2">
        <span>{t('geneCapsule.usedTimes', '{{count}} times', { count: skill.times_used })}</span>
        <span className="text-green-600 dark:text-green-400">{successRate.toFixed(0)}% {t('geneCapsule.success', 'success')}</span>
        <span className="text-yellow-600 dark:text-yellow-400">
          {t('geneCapsule.avgQuality', '{{score}} avg', { score: (skill.avg_quality_score * 100).toFixed(0) })}
        </span>
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-secondary-400 dark:text-secondary-500">
          <span>{t('geneCapsule.proficiency', 'Proficiency')}</span>
        </div>
        <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(100, skill.times_used * 10)}%`,
              backgroundColor: proficiencyColor,
            }}
          />
        </div>
      </div>

      {skill.certifications.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {skill.certifications.map((cert, idx) => (
            <span key={idx} className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded text-xs">
              {cert}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// Pattern Card Component
interface PatternCardProps {
  pattern: PatternGene
}

function PatternCard({ pattern }: PatternCardProps) {
  const { t } = useTranslation()

  return (
    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-purple-500 dark:text-purple-400" />
          <span className="font-medium text-light-text-primary dark:text-secondary-100">{pattern.pattern_name}</span>
        </div>
        <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded text-xs capitalize">
          {pattern.pattern_type.replace('_', ' ')}
        </span>
      </div>

      <p className="text-sm text-secondary-600 dark:text-secondary-300 mb-3">{pattern.approach}</p>

      <div className="flex items-center gap-4 text-xs text-secondary-500 dark:text-secondary-400 mb-3">
        <div className="flex items-center gap-1">
          <Target className="w-3 h-3" />
          <span>{pattern.times_applied} {t('geneCapsule.applied', 'applied')}</span>
        </div>
        <div className="flex items-center gap-1">
          <TrendingUp className="w-3 h-3 text-green-500 dark:text-green-400" />
          <span className="text-green-600 dark:text-green-400">{(pattern.success_rate * 100).toFixed(0)}%</span>
        </div>
        <div className="flex items-center gap-1">
          <CheckCircle className="w-3 h-3" />
          <span>{(pattern.confidence * 100).toFixed(0)}% {t('geneCapsule.confidence', 'confidence')}</span>
        </div>
      </div>

      {pattern.trigger_conditions.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-secondary-400 dark:text-secondary-500">{t('geneCapsule.triggers', 'Triggers')}:</p>
          <div className="flex flex-wrap gap-1">
            {pattern.trigger_conditions.slice(0, 3).map((trigger, idx) => (
              <span key={idx} className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-secondary-500 dark:text-secondary-400 rounded text-xs">
                {trigger}
              </span>
            ))}
            {pattern.trigger_conditions.length > 3 && (
              <span className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-secondary-400 dark:text-secondary-500 rounded text-xs">
                +{pattern.trigger_conditions.length - 3}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default GeneCapsuleDisplay
