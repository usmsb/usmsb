import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Play, Pause, Plus, Settings, BarChart3, Clock, CheckCircle, XCircle, Info, Lightbulb, TrendingUp, Target, ChevronDown, ChevronUp } from 'lucide-react'
import { getWorkflows, createWorkflow, executeWorkflow, getAgents } from '@/lib/api'
import clsx from 'clsx'
import { getStatusColor } from '@/utils/statusColors'

// 应用场景数据 - Use i18n for dynamic content
const getUseCaseExamples = (t: (key: string) => string) => [
  {
    title: t('simulations.useCase1Title'),
    description: t('simulations.useCase1Desc'),
    scenario: t('simulations.useCase1Scenario'),
    outcome: t('simulations.useCase1Outcome'),
  },
  {
    title: t('simulations.useCase2Title'),
    description: t('simulations.useCase2Desc'),
    scenario: t('simulations.useCase2Scenario'),
    outcome: t('simulations.useCase2Outcome'),
  },
  {
    title: t('simulations.useCase3Title'),
    description: t('simulations.useCase3Desc'),
    scenario: t('simulations.useCase3Scenario'),
    outcome: t('simulations.useCase3Outcome'),
  },
]

export default function Simulations() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showInfo, setShowInfo] = useState(false)
  const [newWorkflow, setNewWorkflow] = useState({
    task_description: '',
    agent_id: '',
    available_tools: '',
  })

  const { data: workflows, isLoading: workflowsLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: getWorkflows,
  })

  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => getAgents(undefined, 50),
  })

  const createMutation = useMutation({
    mutationFn: createWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
    },
  })

  const executeMutation = useMutation({
    mutationFn: ({ workflowId, agentId }: { workflowId: string; agentId: string }) =>
      executeWorkflow(workflowId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
    },
  })

  const handleCreate = () => {
    if (!newWorkflow.task_description || !newWorkflow.agent_id) return
    createMutation.mutate({
      task_description: newWorkflow.task_description,
      agent_id: newWorkflow.agent_id,
      available_tools: newWorkflow.available_tools.split(',').map((t) => t.trim()).filter(Boolean),
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="text-green-500" size={20} />
      case 'failed':
      case 'cancelled':
        return <XCircle className="text-red-500" size={20} />
      case 'running':
        return <Play className="text-blue-500" size={20} />
      case 'paused':
        return <Pause className="text-yellow-500" size={20} />
      default:
        return <Clock className="text-secondary-400" size={20} />
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-light-text-primary dark:text-secondary-100">{t('simulations.title')}</h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">{t('simulations.newSimulation')}</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus size={20} />
          <span className="hidden sm:inline">{t('simulations.newSimulation')}</span>
          <span className="sm:hidden">{t('common.create')}</span>
        </button>
      </div>

      {/* 概念说明卡片 */}
      <div className="card bg-gradient-to-r from-orange-50 to-yellow-50 dark:from-orange-900/20 dark:to-yellow-900/20 border border-orange-200 dark:border-orange-800">
        <button
          onClick={() => setShowInfo(!showInfo)}
          className="w-full flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
              <Lightbulb className="text-orange-600 dark:text-orange-400" size={20} />
            </div>
            <div className="text-left">
              <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">{t('simulations.whatIsSimulation')}</h3>
              <p className="text-sm text-secondary-600 dark:text-secondary-400">{t('simulations.clickToLearnConcepts')}</p>
            </div>
          </div>
          {showInfo ? <ChevronUp size={20} className="text-secondary-400" /> : <ChevronDown size={20} className="text-secondary-400" />}
        </button>

        {showInfo && (
          <div className="mt-6 space-y-6">
            <div>
              <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
                <Info size={16} className="text-orange-500" />
                {t('simulations.conceptDefinition')}
              </h4>
              <p className="text-secondary-700 dark:text-secondary-300 leading-relaxed">
                {t('simulations.conceptDefinitionText')}
              </p>
            </div>

            <div>
              <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
                <TrendingUp size={16} className="text-orange-500" />
                {t('simulations.useCases')}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {getUseCaseExamples(t).map((example, idx) => (
                  <div key={idx} className="p-4 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700">
                    <h5 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2">{example.title}</h5>
                    <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-3">{example.description}</p>
                    <div className="text-xs space-y-1">
                      <div className="flex gap-2">
                        <span className="text-secondary-500 dark:text-secondary-400">{t('simulations.scenario')}:</span>
                        <span className="text-secondary-700 dark:text-secondary-300">{example.scenario}</span>
                      </div>
                      <div className="flex gap-2">
                        <span className="text-secondary-500 dark:text-secondary-400">{t('simulations.outcome')}:</span>
                        <span className="text-green-600 dark:text-green-400">{example.outcome}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
                <Target size={16} className="text-orange-500" />
                {t('simulations.simulationProcess')}
              </h4>
              <div className="flex items-center gap-2 text-sm flex-wrap">
                <div className="flex items-center gap-1 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-full">
                  <span className="font-medium text-blue-700 dark:text-blue-400">{t('simulations.stepCreateTask')}</span>
                </div>
                <span className="text-secondary-400">→</span>
                <div className="flex items-center gap-1 px-3 py-1.5 bg-yellow-100 dark:bg-yellow-900/30 rounded-full">
                  <span className="font-medium text-yellow-700 dark:text-yellow-400">{t('simulations.stepSelectAgent')}</span>
                </div>
                <span className="text-secondary-400">→</span>
                <div className="flex items-center gap-1 px-3 py-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-full">
                  <span className="font-medium text-purple-700 dark:text-purple-400">{t('simulations.stepExecuteSim')}</span>
                </div>
                <span className="text-secondary-400">→</span>
                <div className="flex items-center gap-1 px-3 py-1.5 bg-green-100 dark:bg-green-900/30 rounded-full">
                  <span className="font-medium text-green-700 dark:text-green-400">{t('simulations.stepAnalyzeResult')}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Play className="text-blue-600 dark:text-blue-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('simulations.running')}</p>
              <p className="text-xl font-bold text-light-text-primary dark:text-secondary-100">
                {workflows?.filter((w) => w.status === 'running').length || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('simulations.completed')}</p>
              <p className="text-xl font-bold text-light-text-primary dark:text-secondary-100">
                {workflows?.filter((w) => w.status === 'completed').length || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
              <XCircle className="text-red-600 dark:text-red-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('simulations.failed')}</p>
              <p className="text-xl font-bold text-light-text-primary dark:text-secondary-100">
                {workflows?.filter((w) => w.status === 'failed').length || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-secondary-100 dark:bg-secondary-700 rounded-lg flex items-center justify-center">
              <Clock className="text-secondary-600 dark:text-secondary-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('simulations.pending')}</p>
              <p className="text-xl font-bold text-light-text-primary dark:text-secondary-100">
                {workflows?.filter((w) => w.status === 'pending').length || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Workflows list */}
      <div className="card">
        <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4">{t('simulations.recentSimulations')}</h2>
        {workflowsLoading ? (
          <div className="flex items-center justify-center h-40">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 dark:border-primary-400" />
          </div>
        ) : workflows && workflows.length > 0 ? (
          <div className="space-y-3">
            {workflows.map((workflow) => (
              <div
                key={workflow.id}
                className="flex items-center justify-between p-4 bg-secondary-50 dark:bg-secondary-700/50 rounded-lg"
              >
                <div className="flex items-center gap-4">
                  {getStatusIcon(workflow.status)}
                  <div>
                    <p className="font-medium text-light-text-primary dark:text-secondary-100">{workflow.name}</p>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">
                      {workflow.steps_count} steps
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={clsx(
                      'px-3 py-1 rounded-full text-sm font-medium',
                      getStatusColor(workflow.status)
                    )}
                  >
                    {workflow.status}
                  </span>
                  {workflow.status === 'pending' && (
                    <button
                      onClick={() =>
                        executeMutation.mutate({
                          workflowId: workflow.id,
                          agentId: agents?.[0]?.id || '',
                        })
                      }
                      disabled={executeMutation.isPending}
                      className="btn btn-primary py-1.5 px-3 text-sm"
                    >
                      Execute
                    </button>
                  )}
                  <button aria-label="View analytics" className="p-2 rounded-lg hover:bg-secondary-200 dark:hover:bg-secondary-600 text-secondary-500 dark:text-secondary-400">
                    <BarChart3 size={18} />
                  </button>
                  <button aria-label="Settings" className="p-2 rounded-lg hover:bg-secondary-200 dark:hover:bg-secondary-600 text-secondary-500 dark:text-secondary-400">
                    <Settings size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-secondary-500 dark:text-secondary-400">
            <Play size={48} className="mx-auto mb-4 opacity-50" />
            <p>{t('simulations.noSimulations')}</p>
            <p className="text-sm">{t('simulations.createFirstSimulation')}</p>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="create-simulation-title">
          <div className="bg-white dark:bg-secondary-800 rounded-xl p-6 w-full max-w-lg">
            <h2 id="create-simulation-title" className="text-xl font-bold text-light-text-primary dark:text-secondary-100 mb-4">{t('simulations.newSimulation')}</h2>
            <div className="space-y-4">
              <div>
                <label className="label">{t('simulations.taskDescription')}</label>
                <textarea
                  value={newWorkflow.task_description}
                  onChange={(e) =>
                    setNewWorkflow({ ...newWorkflow, task_description: e.target.value })
                  }
                  className="input"
                  rows={3}
                  placeholder={t('simulations.createFirstSimulation')}
                />
              </div>
              <div>
                <label className="label">{t('simulations.agent')}</label>
                <select
                  value={newWorkflow.agent_id}
                  onChange={(e) => setNewWorkflow({ ...newWorkflow, agent_id: e.target.value })}
                  className="input"
                >
                  <option value="">{t('simulations.selectAgent')}</option>
                  {agents?.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">{t('simulations.availableTools')}</label>
                <input
                  type="text"
                  value={newWorkflow.available_tools}
                  onChange={(e) =>
                    setNewWorkflow({ ...newWorkflow, available_tools: e.target.value })
                  }
                  className="input"
                  placeholder="web_search, calculator, data_analysis"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowCreateModal(false)} className="btn btn-secondary">
                {t('common.cancel')}
              </button>
              <button
                onClick={handleCreate}
                disabled={!newWorkflow.task_description || !newWorkflow.agent_id || createMutation.isPending}
                className="btn btn-primary disabled:opacity-50"
              >
                {createMutation.isPending ? t('simulations.creating') : t('simulations.createSimulation')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
