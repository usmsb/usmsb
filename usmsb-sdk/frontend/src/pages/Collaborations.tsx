import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  Users,
  GitBranch,
  CheckCircle,
  XCircle,
  Pause,
  Plus,
  ArrowRight,
  RefreshCw,
  Info,
  Lightbulb,
  TrendingUp,
  Target,
  ChevronDown,
  ChevronUp,
  AlertCircle,
} from 'lucide-react'
import { toast } from '../stores/toastStore'
import { getStatusColor } from '@/utils/statusColors'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

interface CollaborationSession {
  session_id: string
  goal: {
    id: string
    name: string
    description: string
  }
  plan: {
    plan_id: string
    mode: 'parallel' | 'sequential' | 'hybrid'
    roles: CollaborationRole[]
  }
  status: 'analyzing' | 'organizing' | 'executing' | 'integrating' | 'completed' | 'failed'
  participants: string[]
  coordinator_id: string
  started_at?: number
  completed_at?: number
  result?: Record<string, unknown>
  error?: string
}

interface CollaborationRole {
  role_id: string
  role_type: 'coordinator' | 'primary' | 'specialist' | 'support' | 'validator'
  required_skills: string[]
  assigned_agent_id?: string
  assigned_agent_name?: string
  status: 'pending' | 'assigned' | 'executing' | 'completed'
}

const getRoleTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    coordinator: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    primary: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    specialist: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    support: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    validator: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  }
  return colors[type] || 'bg-gray-100 text-gray-700 dark:bg-secondary-800 dark:text-gray-400'
}

export default function Collaborations() {
  const { t } = useTranslation()
  const [selectedSession, setSelectedSession] = useState<CollaborationSession | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [showInfo, setShowInfo] = useState(false)
  const [newSession, setNewSession] = useState({
    goal: '',
    mode: 'hybrid',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Use case examples with i18n
  const useCaseExamples = [
    {
      title: t('collaborations.useCase1Title'),
      description: t('collaborations.useCase1Desc'),
      scenario: t('collaborations.useCase1Scenario'),
      outcome: t('collaborations.useCase1Outcome'),
    },
    {
      title: t('collaborations.useCase2Title'),
      description: t('collaborations.useCase2Desc'),
      scenario: t('collaborations.useCase2Scenario'),
      outcome: t('collaborations.useCase2Outcome'),
    },
    {
      title: t('collaborations.useCase3Title'),
      description: t('collaborations.useCase3Desc'),
      scenario: t('collaborations.useCase3Scenario'),
      outcome: t('collaborations.useCase3Outcome'),
    },
  ]

  // Fetch collaboration sessions from API
  const { data: sessions, isLoading, error, refetch } = useQuery<CollaborationSession[]>({
    queryKey: ['collaborations'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/collaborations`)
      if (!response.ok) throw new Error('Failed to fetch collaborations')
      return response.json()
    },
  })

  // Calculate stats from real data
  const stats = {
    active: sessions?.filter(s => ['analyzing', 'organizing', 'executing', 'integrating'].includes(s.status)).length || 0,
    completed: sessions?.filter(s => s.status === 'completed').length || 0,
    failed: sessions?.filter(s => s.status === 'failed').length || 0,
  }

  const handleCreateSession = async () => {
    if (!newSession.goal.trim()) return
    setIsSubmitting(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 1000))
      toast.success(t('collaborations.createSession') + ' ' + t('common.success').toLowerCase() + '!')
      setIsCreating(false)
      setNewSession({ goal: '', mode: 'hybrid' })
    } catch (error) {
      console.error('Failed to create session:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Concept card component
  const renderConceptCard = () => (
    <div className="card bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/30 dark:to-indigo-900/30 border border-purple-200 dark:border-purple-700">
      <button
        onClick={() => setShowInfo(!showInfo)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 dark:bg-purple-800 rounded-lg flex items-center justify-center">
            <Lightbulb className="text-purple-600 dark:text-purple-400" size={20} />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-secondary-900">{t('collaborations.whatIsCollaboration')}</h3>
            <p className="text-sm text-secondary-600">{t('collaborations.clickToLearn')}</p>
          </div>
        </div>
        {showInfo ? <ChevronUp size={20} className="text-secondary-400" /> : <ChevronDown size={20} className="text-secondary-400" />}
      </button>

      {showInfo && (
        <div className="mt-6 space-y-6">
          {/* Concept Definition */}
          <div>
            <h4 className="font-medium text-secondary-900 mb-2 flex items-center gap-2">
              <Info size={16} className="text-purple-500" />
              {t('collaborations.conceptDefinition')}
            </h4>
            <p className="text-secondary-700 leading-relaxed">
              {t('collaborations.conceptDescription')}
            </p>
          </div>

          {/* Use Cases */}
          <div>
            <h4 className="font-medium text-secondary-900 mb-2 flex items-center gap-2">
              <TrendingUp size={16} className="text-purple-500" />
              {t('collaborations.useCases')}
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {useCaseExamples.map((example, idx) => (
                <div key={idx} className="p-4 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700">
                  <h5 className="font-medium text-secondary-900 dark:text-secondary-100 mb-2">{example.title}</h5>
                  <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-3">{example.description}</p>
                  <div className="text-xs space-y-1">
                    <div className="flex gap-2">
                      <span className="text-secondary-500 dark:text-secondary-400">{t('collaborations.scenario')}:</span>
                      <span className="text-secondary-700 dark:text-secondary-300">{example.scenario}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-secondary-500 dark:text-secondary-400">{t('collaborations.outcome')}:</span>
                      <span className="text-green-600 dark:text-green-400">{example.outcome}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Role Types */}
          <div>
            <h4 className="font-medium text-secondary-900 mb-2 flex items-center gap-2">
              <Target size={16} className="text-purple-500" />
              {t('collaborations.roleTypes')}
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('collaborations.coordinator')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('collaborations.taskDistribution')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('collaborations.primaryExecutor')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('collaborations.coreTaskProcessing')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('collaborations.specialist')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('collaborations.expertSupport')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('collaborations.supportAssistant')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('collaborations.secondaryTaskSupport')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('collaborations.validator')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('collaborations.qualityValidation')}</p>
              </div>
            </div>
          </div>

          {/* Workflow */}
          <div>
            <h4 className="font-medium text-secondary-900 dark:text-secondary-100 mb-2 flex items-center gap-2">
              <GitBranch size={16} className="text-purple-500 dark:text-purple-400" />
              {t('collaborations.workflow')}
            </h4>
            <div className="flex items-center gap-2 text-sm flex-wrap">
              <div className="flex items-center gap-1 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-full">
                <span className="font-medium text-blue-700 dark:text-blue-300">{t('collaborations.stepAnalyze')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-yellow-100 dark:bg-yellow-900/30 rounded-full">
                <span className="font-medium text-yellow-700 dark:text-yellow-300">{t('collaborations.stepPlan')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-full">
                <span className="font-medium text-purple-700 dark:text-purple-300">{t('collaborations.stepAssign')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-indigo-100 dark:bg-indigo-900/30 rounded-full">
                <span className="font-medium text-indigo-700 dark:text-indigo-300">{t('collaborations.stepExecute')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-green-100 dark:bg-green-900/30 rounded-full">
                <span className="font-medium text-green-700 dark:text-green-300">{t('collaborations.stepIntegrate')}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-secondary-900 dark:text-secondary-100">{t('collaborations.title')}</h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">
            {t('collaborations.createSession')}
          </p>
        </div>
        <button
          className="btn btn-primary flex items-center gap-2"
          onClick={() => setIsCreating(true)}
        >
          <Plus size={18} />
          <span className="hidden sm:inline">{t('collaborations.createSession')}</span>
          <span className="sm:hidden">{t('common.create')}</span>
        </button>
      </div>

      {renderConceptCard()}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-800 rounded-lg flex items-center justify-center">
              <GitBranch className="text-blue-600 dark:text-blue-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">{stats.active}</p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('collaborations.activeSessions')}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-800 rounded-lg flex items-center justify-center">
              <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">{stats.completed}</p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('collaborations.completedSessions')}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 dark:bg-red-800 rounded-lg flex items-center justify-center">
              <XCircle className="text-red-600 dark:text-red-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">{stats.failed}</p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('collaborations.failed')}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Sessions List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h2 className="font-semibold text-secondary-900 dark:text-secondary-100">{t('collaborations.sessionDetails')}</h2>
          {isLoading ? (
            <div className="card flex items-center justify-center py-12">
              <RefreshCw className="animate-spin text-primary-500" size={24} />
              <span className="ml-2 text-secondary-500 dark:text-secondary-400">{t('collaborations.loadingSessions')}</span>
            </div>
          ) : error ? (
            <div className="card bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700">
              <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
                <AlertCircle size={18} />
                <span>{t('collaborations.failedToLoad')}</span>
              </div>
              <button
                onClick={() => refetch()}
                className="btn btn-secondary btn-sm mt-3"
              >
                {t('collaborations.retry')}
              </button>
            </div>
          ) : !sessions || sessions.length === 0 ? (
            <div className="card text-center py-12">
              <Users size={48} className="mx-auto mb-3 text-secondary-300 dark:text-secondary-600" />
              <p className="text-secondary-500 dark:text-secondary-400">{t('collaborations.noSessions')}</p>
              <p className="text-sm text-secondary-400 dark:text-secondary-500">{t('collaborations.createFirstSession')}</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.session_id}
                className={`card cursor-pointer transition-all ${
                  selectedSession?.session_id === session.session_id
                    ? 'ring-2 ring-primary-500'
                    : 'hover:shadow-md'
                }`}
                onClick={() => setSelectedSession(session)}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-purple-100 dark:bg-purple-800 rounded-lg flex items-center justify-center">
                      <Users className="text-purple-600 dark:text-purple-400" size={20} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-secondary-900 dark:text-secondary-100">{session.goal.name}</h3>
                      <p className="text-xs text-secondary-500 dark:text-secondary-400">
                        {session.participants.length} {t('collaborations.participants')}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(session.status)}`}>
                    {session.status}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-sm text-secondary-600">
                  <GitBranch size={14} />
                  <span className="capitalize">{session.plan.mode}</span>
                  <span className="text-secondary-400">•</span>
                  <span>{session.plan.roles.length} {t('collaborations.roles')}</span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Session Detail */}
        <div className="card">
          <h2 className="font-semibold text-secondary-900 mb-4">{t('collaborations.sessionDetails')}</h2>
          {selectedSession ? (
            <div className="space-y-4">
              <div>
                <label className="text-sm text-secondary-500">{t('collaborations.goal')}</label>
                <p className="font-medium text-secondary-900">{selectedSession.goal.description}</p>
              </div>

              <div>
                <label className="text-sm text-secondary-500 mb-2 block">{t('collaborations.roles')}</label>
                <div className="space-y-2">
                  {selectedSession.plan.roles.map((role) => (
                    <div
                      key={role.role_id}
                      className="flex items-center justify-between p-3 bg-secondary-50 dark:bg-secondary-700 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 rounded-full text-xs ${getRoleTypeColor(role.role_type)}`}>
                          {role.role_type}
                        </span>
                        <span className="text-sm text-secondary-700">
                          {role.required_skills.join(', ')}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {role.assigned_agent_name ? (
                          <>
                            <span className="text-sm text-secondary-600">{role.assigned_agent_name}</span>
                            <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(role.status)}`}>
                              {role.status}
                            </span>
                          </>
                        ) : (
                          <span className="text-sm text-secondary-400">{t('collaborations.pendingAssignment')}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {selectedSession.status === 'executing' && (
                <div className="flex gap-2">
                  <button className="btn btn-secondary flex-1">
                    <Pause size={16} />
                    {t('collaborations.pause')}
                  </button>
                  <button className="btn btn-primary flex-1">
                    <ArrowRight size={16} />
                    {t('collaborations.viewProgress')}
                  </button>
                </div>
              )}

              {selectedSession.status === 'completed' && selectedSession.result && (
                <div className="p-4 bg-green-50 dark:bg-green-900/30 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
                    <span className="font-medium text-green-700 dark:text-green-400">{t('collaborations.completedSuccess')}</span>
                  </div>
                  <p className="text-sm text-green-600 dark:text-green-300">
                    {t('collaborations.finalOutputAvailable')}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-secondary-400">
              {t('collaborations.selectSession')}
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {isCreating && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="create-collaboration-title">
          <div className="card w-full max-w-lg">
            <h3 id="create-collaboration-title" className="font-semibold text-secondary-900 mb-4">{t('collaborations.createCollaboration')}</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">
                  {t('collaborations.goalDescription')}
                </label>
                <textarea
                  className="input min-h-[100px]"
                  placeholder={t('collaborations.goalPlaceholder')}
                  value={newSession.goal}
                  onChange={(e) => setNewSession({ ...newSession, goal: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">
                  {t('collaborations.collaborationMode')}
                </label>
                <select
                  className="input"
                  value={newSession.mode}
                  onChange={(e) => setNewSession({ ...newSession, mode: e.target.value })}
                >
                  <option value="hybrid">{t('collaborations.modeHybrid')}</option>
                  <option value="parallel">{t('collaborations.modeParallel')}</option>
                  <option value="sequential">{t('collaborations.modeSequential')}</option>
                </select>
              </div>

              <div className="flex gap-2">
                <button
                  className="btn btn-secondary flex-1"
                  onClick={() => setIsCreating(false)}
                >
                  {t('collaborations.cancel')}
                </button>
                <button
                  className="btn btn-primary flex-1"
                  onClick={handleCreateSession}
                  disabled={isSubmitting || !newSession.goal.trim()}
                >
                  {isSubmitting ? (
                    <RefreshCw size={16} className="animate-spin" />
                  ) : (
                    <RefreshCw size={16} />
                  )}
                  {t('collaborations.analyzeAndCreate')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
