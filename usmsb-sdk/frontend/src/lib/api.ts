import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type {
  Agent,
  AgentCreate,
  GoalCreate,
  Environment,
  EnvironmentCreate,
  Prediction,
  PredictionRequest,
  Workflow,
  WorkflowCreate,
  WorkflowResult,
  HealthResponse,
  Metrics,
  Opportunity,
  NegotiationSession,
  NegotiationProposal,
  MatchingStats,
  NetworkAgent,
  AgentNetworkStats,
  AgentRecommendation,
  Demand,
  DemandCreate,
  Service,
  ServiceCreate,
} from '@/types'

// API Configuration
export const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Error types for better error handling
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code?: string,
    public details?: Record<string, unknown>
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export type ErrorHandler = (error: ApiError) => void

// Global error handlers
const errorHandlers: Set<ErrorHandler> = new Set()

export function addErrorHandler(handler: ErrorHandler): () => void {
  errorHandlers.add(handler)
  return () => errorHandlers.delete(handler)
}

function notifyErrorHandlers(error: ApiError): void {
  errorHandlers.forEach((handler) => {
    try {
      handler(error)
    } catch {
      // Ignore handler errors
    }
  })
}

// Response interceptor - handle success responses
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    const statusCode = error.response?.status ?? 0
    let message = 'An unexpected error occurred'
    let code = 'UNKNOWN_ERROR'

    if (error.response) {
      // Server responded with error
      const data = error.response.data as Record<string, unknown>
      message = (data?.message as string) || (data?.error as string) || error.message
      code = (data?.code as string) || `HTTP_${statusCode}`
    } else if (error.request) {
      // Request made but no response
      message = 'Unable to connect to server. Please check your connection.'
      code = 'NETWORK_ERROR'
    } else {
      // Request setup error
      message = error.message || 'Failed to make request'
      code = 'REQUEST_ERROR'
    }

    const apiError = new ApiError(message, statusCode, code, {
      url: (error.config as InternalAxiosRequestConfig)?.url,
      method: (error.config as InternalAxiosRequestConfig)?.method,
      originalError: error.message,
    })

    notifyErrorHandlers(apiError)
    return Promise.reject(apiError)
  }
)

// Request interceptor - add auth token if available
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add any auth token here if needed
    // const token = localStorage.getItem('auth_token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => Promise.reject(error)
)

// ============ Health & Metrics ============

export const getHealth = async (): Promise<HealthResponse> => {
  const response = await api.get<HealthResponse>('/health')
  return response.data
}

export const getMetrics = async (): Promise<Metrics> => {
  const response = await api.get<Metrics>('/metrics')
  return response.data
}

// ============ Agents ============

export const getAgents = async (type?: string, limit = 100): Promise<Agent[]> => {
  const params = new URLSearchParams()
  if (type) params.append('type', type)
  params.append('limit', String(limit))
  const response = await api.get<Agent[]>(`/agents?${params}`)
  return response.data
}

export const getAgent = async (id: string): Promise<Agent> => {
  const response = await api.get<Agent>(`/agents/${id}`)
  return response.data
}

export const createAgent = async (data: AgentCreate): Promise<Agent> => {
  const response = await api.post<Agent>('/agents', data)
  return response.data
}

export const deleteAgent = async (id: string): Promise<void> => {
  await api.delete(`/agents/${id}`)
}

export const addGoalToAgent = async (
  agentId: string,
  goal: GoalCreate
): Promise<{ goal_id: string; status: string }> => {
  const response = await api.post(`/agents/${agentId}/goals`, goal)
  return response.data
}

// ============ Environments ============

export const getEnvironments = async (limit = 100): Promise<Environment[]> => {
  const response = await api.get<Environment[]>(`/environments?limit=${limit}`)
  return response.data
}

export const getEnvironment = async (id: string): Promise<Environment> => {
  const response = await api.get<Environment>(`/environments/${id}`)
  return response.data
}

export const createEnvironment = async (data: EnvironmentCreate): Promise<Environment> => {
  const response = await api.post<Environment>('/environments', data)
  return response.data
}

// ============ Predictions ============

export const predictBehavior = async (request: PredictionRequest): Promise<Prediction> => {
  const response = await api.post<{ prediction: Prediction }>('/predict/behavior', request)
  return response.data.prediction
}

// ============ Workflows ============

export const getWorkflows = async (): Promise<Workflow[]> => {
  try {
    const response = await api.get<Workflow[]>('/workflows')
    return response.data
  } catch {
    // Return empty array if service is unavailable
    return []
  }
}

export const createWorkflow = async (data: WorkflowCreate): Promise<Workflow> => {
  const response = await api.post<Workflow>('/workflows', data)
  return response.data
}

export const executeWorkflow = async (
  workflowId: string,
  agentId: string
): Promise<WorkflowResult> => {
  const response = await api.post<WorkflowResult>(
    `/workflows/${workflowId}/execute?agent_id=${agentId}`
  )
  return response.data
}

// ============ Active Matching API ============

export const searchDemands = async (
  agentId: string,
  capabilities: string[],
  budgetMin?: number,
  budgetMax?: number
): Promise<Opportunity[]> => {
  const response = await api.post<Opportunity[]>('/matching/search-demands', {
    agent_id: agentId,
    capabilities,
    budget_min: budgetMin,
    budget_max: budgetMax,
  })
  return response.data
}

export const searchSuppliers = async (
  agentId: string,
  requiredSkills: string[],
  budgetMin?: number,
  budgetMax?: number
): Promise<Opportunity[]> => {
  const response = await api.post<Opportunity[]>('/matching/search-suppliers', {
    agent_id: agentId,
    required_skills: requiredSkills,
    budget_min: budgetMin,
    budget_max: budgetMax,
  })
  return response.data
}

export const initiateNegotiation = async (
  agentId: string,
  counterpartId: string,
  context: Record<string, unknown>
): Promise<NegotiationSession> => {
  const response = await api.post<NegotiationSession>('/matching/negotiate', {
    initiator_id: agentId,
    counterpart_id: counterpartId,
    context,
  })
  return response.data
}

export const submitProposal = async (
  sessionId: string,
  proposal: NegotiationProposal
): Promise<NegotiationSession> => {
  const response = await api.post<NegotiationSession>(
    `/matching/negotiations/${sessionId}/proposal`,
    proposal
  )
  return response.data
}

export const getNegotiations = async (agentId: string): Promise<NegotiationSession[]> => {
  const response = await api.get<NegotiationSession[]>(`/matching/negotiations?agent_id=${agentId}`)
  return response.data
}

export const getOpportunities = async (agentId: string): Promise<Opportunity[]> => {
  const response = await api.get<Opportunity[]>(`/matching/opportunities?agent_id=${agentId}`)
  return response.data
}

export const getMatchingStats = async (agentId: string): Promise<MatchingStats> => {
  const response = await api.get<MatchingStats>(`/matching/stats?agent_id=${agentId}`)
  return response.data
}

// ============ Network Explorer API ============

export const exploreNetwork = async (
  agentId: string,
  targetCapabilities?: string[],
  depth?: number
): Promise<NetworkAgent[]> => {
  const response = await api.post<NetworkAgent[]>('/network/explore', {
    agent_id: agentId,
    target_capabilities: targetCapabilities,
    exploration_depth: depth,
  })
  return response.data
}

export const requestRecommendations = async (
  agentId: string,
  targetCapability: string
): Promise<AgentRecommendation[]> => {
  const response = await api.post<AgentRecommendation[]>('/network/recommendations', {
    agent_id: agentId,
    target_capability: targetCapability,
  })
  return response.data
}

export const getNetworkStats = async (agentId: string): Promise<AgentNetworkStats> => {
  const response = await api.get<AgentNetworkStats>(`/network/stats?agent_id=${agentId}`)
  return response.data
}

// ============ Demand API ============

export const createDemand = async (data: DemandCreate): Promise<Demand> => {
  const response = await api.post<Demand>('/demands', data)
  return response.data
}

export const getDemands = async (agentId?: string, category?: string): Promise<Demand[]> => {
  const params = new URLSearchParams()
  if (agentId) params.append('agent_id', agentId)
  if (category) params.append('category', category)
  const response = await api.get<Demand[]>(`/demands?${params}`)
  return response.data
}

export const deleteDemand = async (demandId: string): Promise<void> => {
  await api.delete(`/demands/${demandId}`)
}

// ============ Service API ============

export const createService = async (data: ServiceCreate): Promise<Service> => {
  const response = await api.post<Service>('/services', data)
  return response.data
}

export const getServices = async (agentId?: string, category?: string): Promise<Service[]> => {
  const params = new URLSearchParams()
  if (agentId) params.append('agent_id', agentId)
  if (category) params.append('category', category)
  const response = await api.get<Service[]>(`/services?${params}`)
  return response.data
}

export default api

// ============ Meta Agent Chat API ============

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface ChatRequest {
  message: string
  wallet_address?: string
  context?: Record<string, unknown>
}

export interface ChatResponse {
  response: string
  success: boolean
  tool_used?: string
  details?: Record<string, unknown>
}

export const sendChatMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/meta-agent/chat', request)
  return response.data
}

export const getAgentTools = async (): Promise<{ name: string; description: string }[]> => {
  const response = await api.get<{ name: string; description: string }[]>('/meta-agent/tools')
  return response.data
}

export interface HistoryMessage {
  id: string
  role: string
  content: string
  timestamp?: number
  tool_calls?: Array<{
    id?: string
    function: {
      name: string
      arguments: string | Record<string, unknown>
    }
  }>
}

export const getConversationHistory = async (
  walletAddress: string,
  limit: number = 50
): Promise<HistoryMessage[]> => {
  const response = await api.get<HistoryMessage[]>(`/meta-agent/history/${walletAddress}`, {
    params: { limit },
  })
  return response.data
}

// Get latest messages for polling
export const getLatestMessages = async (
  walletAddress: string,
  afterTimestamp: number = 0
): Promise<HistoryMessage[]> => {
  const response = await api.get<HistoryMessage[]>(`/meta-agent/history/${walletAddress}/latest`, {
    params: { after_timestamp: afterTimestamp },
  })
  return response.data
}

export interface EvolutionStats {
  total_evolutions: number
  by_type: Record<string, number>
  by_status: Record<string, number>
  capabilities: Record<string, { score: number; improvement_rate: number }>
}

export const getEvolutionStats = async (): Promise<EvolutionStats> => {
  const response = await api.get<EvolutionStats>('/meta-agent/evolution-stats')
  return response.data
}

// ============ Permission APIs ============

export interface UserInfo {
  wallet_address: string
  role: string
  permissions: string[]
  stake_amount: number
  token_balance: number
  voting_power: number
}

export const getUserInfo = async (walletAddress: string): Promise<UserInfo> => {
  const response = await api.get<UserInfo>(`/meta-agent/user/${walletAddress}`)
  return response.data
}

export const updateUserRole = async (
  walletAddress: string,
  newRole: string,
  reason?: string
): Promise<UserInfo> => {
  const response = await api.post<UserInfo>('/meta-agent/user/role', {
    wallet_address: walletAddress,
    new_role: newRole,
    reason,
  })
  return response.data
}

export const updateUserStake = async (
  walletAddress: string,
  stakeAmount: number
): Promise<UserInfo> => {
  const response = await api.post<UserInfo>('/meta-agent/user/stake', {
    wallet_address: walletAddress,
    stake_amount: stakeAmount,
  })
  return response.data
}

export interface PermissionStats {
  total_users: number
  users_by_role: Record<string, number>
  total_voting_power: number
  total_stake: number
}

export const getPermissionStats = async (): Promise<PermissionStats> => {
  const response = await api.get<PermissionStats>('/meta-agent/permission/stats')
  return response.data
}

export const checkToolPermission = async (
  walletAddress: string,
  toolName: string
): Promise<{ allowed: boolean; reason: string; user_role?: string }> => {
  const response = await api.get(
    `/meta-agent/permission/check-tool/${walletAddress}/${toolName}`
  )
  return response.data
}
