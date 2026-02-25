import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import {
  ArrowLeft,
  Target,
  Activity,
  Link2,
  Bot,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  Send,
  Trash2,
  Heart,
  MessageSquare,
  TestTube,
  Wallet,
  TrendingUp,
  Package,
  ShoppingCart,
  ArrowUpRight,
  ArrowDownLeft,
  Star,
} from 'lucide-react'
import clsx from 'clsx'
import { getStatusColor } from '@/utils/statusColors'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

interface AIAgent {
  agent_id: string
  name: string
  agent_type: string
  capabilities: string[]
  skills: Array<{ name: string; level?: string }>
  endpoint: string
  protocol: string
  stake: number
  balance: number
  description: string
  metadata: Record<string, unknown>
  status: string
  reputation: number
  registered_at: number
  last_heartbeat: number
}

interface Demand {
  id: string
  title: string
  description: string
  category: string
  budget: number
  status: string
  created_at: number
}

interface Service {
  id: string
  service_name: string
  description: string
  category: string
  price: number
  price_type: string
  status: string
}

interface Transaction {
  id: string
  type: 'income' | 'expense'
  amount: number
  description: string
  counterparty: string
  created_at: number
}

export default function AgentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [testInput, setTestInput] = useState('')
  const [testResult, setTestResult] = useState<{ success: boolean; output: string; time: number } | null>(null)
  const [isTesting, setIsTesting] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'demands' | 'services' | 'transactions'>('overview')

  // Fetch AI agent data
  const { data: agent, isLoading, error, refetch } = useQuery({
    queryKey: ['ai-agent', id],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/agents/${id}`)
      if (!response.ok) throw new Error('Agent not found')
      return response.json() as Promise<AIAgent>
    },
    enabled: !!id,
  })

  // Fetch agent's demands
  const { data: demands } = useQuery({
    queryKey: ['agent-demands', id],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/demands?agent_id=${id}`)
      if (!response.ok) return []
      return response.json() as Promise<Demand[]>
    },
    enabled: !!id,
  })

  // Fetch agent's services
  const { data: services } = useQuery({
    queryKey: ['agent-services', id],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/services?agent_id=${id}`)
      if (!response.ok) return []
      return response.json() as Promise<Service[]>
    },
    enabled: !!id,
  })

  // Fetch behavior prediction
  const { data: prediction, mutate: predictBehavior, isPending: isPredicting } = useMutation({
    mutationFn: async () => {
      const response = await fetch(`${API_BASE}/predict/behavior`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: id }),
      })
      if (!response.ok) throw new Error('Prediction failed')
      return response.json()
    },
  })

  // Fetch transactions from API - must be before any conditional returns
  const { data: transactions } = useQuery({
    queryKey: ['agent-transactions', id],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/agents/${id}/transactions`)
      if (!response.ok) return []
      return response.json() as Promise<Transaction[]>
    },
    enabled: !!id,
  })

  // Test agent endpoint - P2P direct communication
  const handleTestAgent = async () => {
    if (!agent || !testInput.trim()) return

    setIsTesting(true)
    setTestResult(null)
    const startTime = Date.now()

    try {
      // P2P: Call agent's endpoint directly
      const agentEndpoint = agent.endpoint

      if (!agentEndpoint) {
        setTestResult({
          success: false,
          output: 'Agent endpoint not configured',
          time: 0,
        })
        return
      }

      // Try direct P2P call to agent
      const response = await fetch(`${agentEndpoint}/invoke`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          method: 'chat',
          params: {
            message: testInput,
            context: {},
          },
        }),
      })

      const latency = Date.now() - startTime
      const data = await response.json()

      if (response.ok) {
        setTestResult({
          success: true,
          output: typeof data.result === 'string' ? data.result : JSON.stringify(data.result || data, null, 2),
          time: latency,
        })
      } else {
        setTestResult({
          success: false,
          output: data.error || `HTTP ${response.status}: ${response.statusText}`,
          time: latency,
        })
      }
    } catch (err) {
      const latency = Date.now() - startTime
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'

      // Check if it's a CORS error
      if (errorMessage.includes('CORS') || errorMessage.includes('fetch')) {
        setTestResult({
          success: false,
          output: `P2P连接失败: 无法直接连接到Agent (${agent.endpoint})。\n可能原因:\n1. Agent服务未启动\n2. CORS跨域限制\n3. 网络不可达\n\n请确保Agent服务正在运行并支持CORS。`,
          time: latency,
        })
      } else {
        setTestResult({
          success: false,
          output: `请求失败: ${errorMessage}`,
          time: latency,
        })
      }
    } finally {
      setIsTesting(false)
    }
  }

  // Send heartbeat - P2P direct communication
  const handleHeartbeat = async () => {
    if (!agent) return

    try {
      const agentEndpoint = agent.endpoint

      if (!agentEndpoint) {
        console.error('Agent endpoint not configured')
        return
      }

      // P2P: Call agent's heartbeat endpoint directly
      const response = await fetch(`${agentEndpoint}/heartbeat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          timestamp: Date.now(),
          status: 'online',
        }),
      })

      if (response.ok) {
        console.log('P2P Heartbeat successful')
        // Also notify the platform
        await fetch(`${API_BASE}/agent-auth/agents/${id}/heartbeat`, {
          method: 'POST',
        })
        refetch()
      } else {
        console.error('P2P Heartbeat failed:', response.status)
      }
    } catch (err) {
      console.error('P2P Heartbeat error:', err)
      // Fallback: notify platform only
      try {
        await fetch(`${API_BASE}/agent-auth/agents/${id}/heartbeat`, {
          method: 'POST',
        })
        refetch()
      } catch (fallbackErr) {
        console.error('Fallback heartbeat also failed:', fallbackErr)
      }
    }
  }

  // Delete agent
  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this agent?')) return

    try {
      const response = await fetch(`${API_BASE}/agents/${id}`, {
        method: 'DELETE',
      })
      if (response.ok) {
        navigate('/app/agents')
      }
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const getProtocolIcon = (protocol: string | undefined) => {
    const proto = (protocol || 'standard').toLowerCase()
    switch (proto) {
      case 'mcp':
        return Link2
      case 'a2a':
        return MessageSquare
      case 'skill_md':
        return Bot
      default:
        return Bot
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin text-primary-500" size={32} />
      </div>
    )
  }

  if (error || !agent) {
    return (
      <div className="text-center py-12">
        <AlertCircle size={48} className="mx-auto mb-4 text-red-400" />
        <p className="text-secondary-500 mb-4">Agent not found</p>
        <button onClick={() => navigate('/app/agents')} className="btn btn-primary">
          Back to Agents
        </button>
      </div>
    )
  }

  const ProtocolIcon = getProtocolIcon(agent.protocol)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/app/agents')}
            aria-label="Go back to agents"
            className="p-2 rounded-lg hover:bg-secondary-100 text-secondary-500"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <h1 className="text-xl md:text-2xl font-bold text-secondary-900">{agent.name}</h1>
              <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', getStatusColor(agent.status))}>
                {agent.status || 'offline'}
              </span>
            </div>
            <p className="text-sm md:text-base text-secondary-500 flex items-center gap-2">
              <ProtocolIcon size={16} />
              {agent.protocol?.toUpperCase() || 'STANDARD'} Protocol
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 ml-10 sm:ml-0">
          <button
            onClick={handleHeartbeat}
            className="btn btn-secondary flex items-center gap-2 text-sm md:text-base"
          >
            <Heart size={18} />
            <span className="hidden sm:inline">Heartbeat</span>
          </button>
          <button
            onClick={() => predictBehavior()}
            disabled={isPredicting}
            className="btn btn-secondary flex items-center gap-2 text-sm md:text-base"
          >
            {isPredicting ? <RefreshCw className="animate-spin" size={18} /> : <Activity size={18} />}
            <span className="hidden sm:inline">Predict</span>
          </button>
          <button
            onClick={handleDelete}
            className="btn bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50 flex items-center gap-2"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 md:gap-4">
        <div className="card text-center">
          <div className="flex items-center justify-center mb-2">
            <Wallet className="text-green-600 dark:text-green-400" size={20} />
          </div>
          <div className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{agent.balance || agent.stake || 0}</div>
          <div className="text-xs text-secondary-500 dark:text-secondary-400">VIBE Balance</div>
        </div>
        <div className="card text-center">
          <div className="flex items-center justify-center mb-2">
            <TrendingUp className="text-blue-600 dark:text-blue-400" size={20} />
          </div>
          <div className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{agent.stake || 0}</div>
          <div className="text-xs text-secondary-500 dark:text-secondary-400">Staked</div>
        </div>
        <div className="card text-center">
          <div className="flex items-center justify-center mb-2">
            <ShoppingCart className="text-purple-600 dark:text-purple-400" size={20} />
          </div>
          <div className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{demands?.length || 0}</div>
          <div className="text-xs text-secondary-500 dark:text-secondary-400">Demands</div>
        </div>
        <div className="card text-center">
          <div className="flex items-center justify-center mb-2">
            <Package className="text-orange-600 dark:text-orange-400" size={20} />
          </div>
          <div className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{services?.length || 0}</div>
          <div className="text-xs text-secondary-500 dark:text-secondary-400">Services</div>
        </div>
        <div className="card text-center">
          <div className="flex items-center justify-center mb-2">
            <Star className="text-yellow-500 dark:text-yellow-400" size={20} />
          </div>
          <div className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{((agent.reputation || 0.5) * 100).toFixed(0)}%</div>
          <div className="text-xs text-secondary-500 dark:text-secondary-400">Reputation</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-secondary-200 overflow-x-auto">
        <div className="flex gap-2 sm:gap-4 min-w-max">
          {[
            { id: 'overview', label: 'Overview', icon: Bot },
            { id: 'demands', label: 'Demands', icon: ShoppingCart },
            { id: 'services', label: 'Services', icon: Package },
            { id: 'transactions', label: 'Transactions', icon: TrendingUp },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={clsx(
                'flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-2 border-b-2 transition-colors text-sm sm:text-base',
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-secondary-500 hover:text-secondary-700'
              )}
            >
              <tab.icon size={16} className="sm:w-[18px] sm:h-[18px]" />
              <span className="hidden xs:inline">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Test Agent */}
            <div className="card">
              <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4 flex items-center gap-2">
                <TestTube size={20} />
                Test Agent
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                    Test Input
                  </label>
                  <textarea
                    className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                    rows={3}
                    placeholder="Enter a test message or task for the agent..."
                    value={testInput}
                    onChange={(e) => setTestInput(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleTestAgent}
                  disabled={isTesting || !testInput.trim()}
                  className="btn btn-primary flex items-center gap-2"
                >
                  {isTesting ? (
                    <>
                      <RefreshCw className="animate-spin" size={18} />
                      Testing...
                    </>
                  ) : (
                    <>
                      <Send size={18} />
                      Send Test
                    </>
                  )}
                </button>

                {testResult && (
                  <div className={clsx(
                    'p-4 rounded-lg',
                    testResult.success ? 'bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700' : 'bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700'
                  )}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {testResult.success ? (
                          <CheckCircle className="text-green-600 dark:text-green-400" size={18} />
                        ) : (
                          <XCircle className="text-red-600 dark:text-red-400" size={18} />
                        )}
                        <span className={testResult.success ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}>
                          {testResult.success ? 'Success' : 'Failed'}
                        </span>
                      </div>
                      <span className="text-sm text-secondary-500 dark:text-secondary-400">{testResult.time}ms</span>
                    </div>
                    <pre className="text-sm overflow-auto whitespace-pre-wrap text-secondary-700 dark:text-secondary-300">
                      {testResult.output}
                    </pre>
                  </div>
                )}
              </div>
            </div>

            {/* Capabilities */}
            <div className="card">
              <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Capabilities</h2>
              <div className="flex flex-wrap gap-2">
                {agent.capabilities?.length > 0 ? (
                  agent.capabilities.map((cap) => (
                    <span
                      key={cap}
                      className="px-3 py-1.5 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 rounded-full text-sm font-medium"
                    >
                      {cap}
                    </span>
                  ))
                ) : (
                  <span className="text-secondary-500 dark:text-secondary-400">No capabilities defined</span>
                )}
              </div>
            </div>

            {/* Skills */}
            <div className="card">
              <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Skills</h2>
              {agent.skills && agent.skills.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {agent.skills.map((skill, idx) => (
                    <div key={idx} className="p-3 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
                      <p className="font-medium text-light-text-primary dark:text-secondary-100">{skill.name}</p>
                      {skill.level && (
                        <p className="text-xs text-secondary-500 dark:text-secondary-400">{skill.level}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-secondary-500 dark:text-secondary-400">No skills defined</span>
              )}
            </div>

            {/* Prediction Result */}
            {prediction && (
              <div className="card">
                <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4 flex items-center gap-2">
                  <Activity size={20} />
                  Behavior Prediction
                </h2>
                <pre className="bg-secondary-50 dark:bg-secondary-700 p-4 rounded-lg overflow-auto text-sm text-secondary-700 dark:text-secondary-300">
                  {JSON.stringify(prediction, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Connection Info */}
            <div className="card">
              <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Connection</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-secondary-500 dark:text-secondary-400 uppercase">Protocol</label>
                  <p className="font-medium text-light-text-primary dark:text-secondary-100">{agent.protocol?.toUpperCase() || 'STANDARD'}</p>
                </div>
                <div>
                  <label className="text-xs text-secondary-500 dark:text-secondary-400 uppercase">Endpoint</label>
                  <p className="font-mono text-sm text-secondary-700 dark:text-secondary-300 break-all">{agent.endpoint}</p>
                </div>
                <div>
                  <label className="text-xs text-secondary-500 dark:text-secondary-400 uppercase">Agent ID</label>
                  <p className="font-mono text-sm text-secondary-700 dark:text-secondary-300">{agent.agent_id}</p>
                </div>
              </div>
            </div>

            {/* Timeline */}
            <div className="card">
              <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4 flex items-center gap-2">
                <Clock size={18} />
                Timeline
              </h2>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-secondary-500 dark:text-secondary-400">Registered</span>
                  <span className="text-secondary-700 dark:text-secondary-300">
                    {agent.registered_at ? new Date(agent.registered_at * 1000).toLocaleString() : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-secondary-500 dark:text-secondary-400">Last Heartbeat</span>
                  <span className="text-secondary-700 dark:text-secondary-300">
                    {agent.last_heartbeat ? new Date(agent.last_heartbeat * 1000).toLocaleString() : 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="card">
              <h2 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Quick Actions</h2>
              <div className="space-y-2">
                <button
                  onClick={() => navigate(`/publish/demand?agent=${agent.agent_id}`)}
                  className="btn btn-secondary w-full flex items-center justify-center gap-2"
                >
                  <ShoppingCart size={18} />
                  Publish Demand
                </button>
                <button
                  onClick={() => navigate(`/publish/service?agent=${agent.agent_id}`)}
                  className="btn btn-secondary w-full flex items-center justify-center gap-2"
                >
                  <Package size={18} />
                  Offer Service
                </button>
                <button
                  onClick={() => navigate(`/matching?agent=${agent.agent_id}`)}
                  className="btn btn-secondary w-full flex items-center justify-center gap-2"
                >
                  <Target size={18} />
                  Start Matching
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Demands Tab */}
      {activeTab === 'demands' && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-secondary-900">Published Demands</h2>
            <button
              onClick={() => navigate(`/publish/demand?agent=${agent.agent_id}`)}
              className="btn btn-primary btn-sm flex items-center gap-2"
            >
              <ShoppingCart size={16} />
              New Demand
            </button>
          </div>
          {demands && demands.length > 0 ? (
            <div className="space-y-3">
              {demands.map((demand) => (
                <div key={demand.id} className="p-4 bg-secondary-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium text-secondary-900">{demand.title}</h3>
                      <p className="text-sm text-secondary-500">{demand.category}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-secondary-900">{demand.budget} VIBE</p>
                      <span className={clsx('text-xs px-2 py-1 rounded-full', getStatusColor(demand.status))}>
                        {demand.status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-secondary-500">
              <ShoppingCart size={48} className="mx-auto mb-3 text-secondary-300" />
              <p>No demands published yet</p>
              <button
                onClick={() => navigate(`/publish/demand?agent=${agent.agent_id}`)}
                className="btn btn-primary btn-sm mt-4"
              >
                Publish First Demand
              </button>
            </div>
          )}
        </div>
      )}

      {/* Services Tab */}
      {activeTab === 'services' && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-secondary-900">Offered Services</h2>
            <button
              onClick={() => navigate(`/publish/service?agent=${agent.agent_id}`)}
              className="btn btn-primary btn-sm flex items-center gap-2"
            >
              <Package size={16} />
              New Service
            </button>
          </div>
          {services && services.length > 0 ? (
            <div className="space-y-3">
              {services.map((service) => (
                <div key={service.id} className="p-4 bg-secondary-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium text-secondary-900">{service.service_name}</h3>
                      <p className="text-sm text-secondary-500">{service.category}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-secondary-900">{service.price} VIBE/{service.price_type}</p>
                      <span className={clsx('text-xs px-2 py-1 rounded-full', getStatusColor(service.status))}>
                        {service.status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-secondary-500">
              <Package size={48} className="mx-auto mb-3 text-secondary-300" />
              <p>No services offered yet</p>
              <button
                onClick={() => navigate(`/publish/service?agent=${agent.agent_id}`)}
                className="btn btn-primary btn-sm mt-4"
              >
                Offer First Service
              </button>
            </div>
          )}
        </div>
      )}

      {/* Transactions Tab */}
      {activeTab === 'transactions' && (
        <div className="card">
          <h2 className="text-lg font-semibold text-secondary-900 mb-4">Transaction History</h2>
          {transactions && transactions.length > 0 ? (
            <div className="space-y-3">
              {transactions.map((tx) => (
                <div key={tx.id} className="flex items-center justify-between p-4 bg-secondary-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className={clsx(
                      'w-10 h-10 rounded-full flex items-center justify-center',
                      tx.type === 'income' ? 'bg-green-100' : 'bg-red-100'
                    )}>
                      {tx.type === 'income' ? (
                        <ArrowDownLeft className="text-green-600" size={20} />
                      ) : (
                        <ArrowUpRight className="text-red-600" size={20} />
                      )}
                    </div>
                    <div>
                      <p className="font-medium text-secondary-900">{tx.description}</p>
                      <p className="text-sm text-secondary-500">with {tx.counterparty}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={clsx(
                      'font-semibold',
                      tx.type === 'income' ? 'text-green-600' : 'text-red-600'
                    )}>
                      {tx.type === 'income' ? '+' : '-'}{tx.amount} VIBE
                    </p>
                    <p className="text-xs text-secondary-500">
                      {new Date(tx.created_at * 1000).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-secondary-500">
              <TrendingUp size={48} className="mx-auto mb-3 text-secondary-300" />
              <p>No transactions yet</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
