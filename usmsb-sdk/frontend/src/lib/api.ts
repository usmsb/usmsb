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

// Helper to get auth data from zustand persisted storage
function getAuthFromStorage() {
  try {
    const stored = localStorage.getItem('usmsb-auth')
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        accessToken: parsed?.state?.accessToken,
        agentId: parsed?.state?.agentId,
        apiKey: parsed?.state?.apiKey,
      }
    }
  } catch {
    // Ignore parsing errors
  }
  return { accessToken: null, agentId: null, apiKey: null }
}

/**
 * Authenticated fetch helper that automatically adds auth headers
 * Use this instead of raw fetch for API calls that need authentication
 */
export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const auth = getAuthFromStorage()

  // Clone headers to avoid mutating the original
  const headers = new Headers(options.headers || {})

  // Add Bearer token for wallet authentication if available
  if (auth.accessToken) {
    headers.set('Authorization', `Bearer ${auth.accessToken}`)
  }

  // Add API Key and Agent ID for agent authentication
  if (auth.apiKey && auth.agentId) {
    headers.set('X-API-Key', auth.apiKey)
    headers.set('X-Agent-ID', auth.agentId)
  }

  // Set Content-Type if not already set and body is present
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  return fetch(url, {
    ...options,
    headers,
  })
}

/**
 * Authenticated fetch with JSON parsing
 * Combines authFetch with JSON response handling
 */
export async function authFetchJson<T = unknown>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await authFetch(url, options)
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new ApiError(
      errorData.message || errorData.error || `HTTP ${response.status}`,
      response.status,
      errorData.code,
      errorData
    )
  }
  return response.json()
}

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
    const auth = getAuthFromStorage()

    // Add API Key and Agent ID for agent authentication
    if (auth.apiKey && auth.agentId) {
      config.headers['X-API-Key'] = auth.apiKey
      config.headers['X-Agent-ID'] = auth.agentId
    }

    // Add Bearer token for wallet authentication if available
    if (auth.accessToken) {
      config.headers.Authorization = `Bearer ${auth.accessToken}`
    }

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

export const createService = async (agentId: string, data: ServiceCreate): Promise<Service> => {
  const response = await api.post<Service>(`/agents/${agentId}/services`, data)
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

// ============ SIWE Authentication ============

export interface NonceResponse {
  nonce: string
  expiresAt: number
}

export interface VerifyResponse {
  success: boolean
  sessionId: string
  accessToken: string
  expiresIn: number
  did: string
  isNewUser: boolean
}

export interface SessionResponse {
  valid: boolean
  agentId?: string
  address?: string
  did?: string
  stake?: number
  reputation?: number
}

/**
 * Get a nonce for SIWE authentication
 */
export const getAuthNonce = async (address: string): Promise<NonceResponse> => {
  const response = await api.get<NonceResponse>(`/auth/nonce/${address}`)
  return response.data
}

/**
 * Create a SIWE message
 */
export const createSiweMessage = (
  address: string,
  nonce: string,
  chainId: number = 1,
  statement?: string
): string => {
  const domain = window.location.host
  const origin = window.location.origin
  const message = `${domain} wants you to sign in with your Ethereum account:
${address}

${statement || 'Sign in to USMSB Platform'}

URI: ${origin}
Version: 1
Chain ID: ${chainId}
Nonce: ${nonce}
Issued At: ${new Date().toISOString()}`
  return message
}

/**
 * Verify SIWE signature and complete authentication
 */
export const verifyAuth = async (
  message: string,
  signature: string,
  address: string
): Promise<VerifyResponse> => {
  const response = await api.post<VerifyResponse>('/auth/verify', {
    message,
    signature,
    address,
  })
  return response.data
}

/**
 * Get current session info
 */
export const getSession = async (): Promise<SessionResponse> => {
  const response = await api.get<SessionResponse>('/auth/session')
  return response.data
}

/**
 * Logout and invalidate session
 */
export const logout = async (): Promise<void> => {
  await api.delete('/auth/session')
}

/**
 * Complete SIWE authentication flow
 * This function handles the entire auth flow: get nonce -> sign message -> verify
 */
export const signInWithEthereum = async (
  address: string,
  signMessage: (message: string) => Promise<string>,
  chainId: number = 1
): Promise<VerifyResponse> => {
  // Step 1: Get nonce
  const nonceResponse = await getAuthNonce(address)

  // Step 2: Create SIWE message
  const message = createSiweMessage(address, nonceResponse.nonce, chainId)

  // Step 3: Sign message
  const signature = await signMessage(message)

  // Step 4: Verify signature
  const verifyResponse = await verifyAuth(message, signature, address)

  return verifyResponse
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

// ============ Agent Registration v2 API ============

export const registerAgentV2 = async (data: {
  name: string
  description?: string
  capabilities?: string[]
}): Promise<{
  success: boolean
  agent_id: string
  api_key: string
  level: number
  binding_status: string
  message: string
}> => {
  const response = await api.post('/agents/v2/register', data)
  return response.data
}

export const requestBinding = async (
  agentId: string,
  message?: string
): Promise<{
  success: boolean
  binding_code: string
  binding_url: string
  expires_in: number
  message: string
}> => {
  const response = await api.post(`/agents/v2/${agentId}/request-binding`, { message })
  return response.data
}

export const getBindingStatus = async (
  agentId: string
): Promise<{
  bound: boolean
  binding_status: string
  owner_wallet?: string
  stake_tier: string
  staked_amount: number
  tier_benefits?: { max_agents: number; discount: number }
  pending_request?: {
    binding_code: string
    binding_url: string
    expires_at: number
    status: string
  }
}> => {
  const response = await api.get(`/agents/v2/${agentId}/binding-status`)
  return response.data
}

export const completeBinding = async (
  bindingCode: string,
  stakeAmount: number
): Promise<{
  success: boolean
  agent_id: string
  owner_wallet: string
  stake_amount: number
  stake_tier: string
  tier_benefits?: { max_agents: number; discount: number }
  completed_at: number
  message: string
}> => {
  const response = await api.post(`/agents/v2/complete-binding/${bindingCode}`, {
    stake_amount: stakeAmount,
  })
  return response.data
}

// ============ API Key Management API ============

export const listAPIKeys = async (
  agentId: string
): Promise<{
  success: boolean
  keys: Array<{
    id: string
    prefix: string
    name: string
    level: number
    expires_at?: number
    last_used_at?: number
    created_at: number
  }>
}> => {
  const response = await api.get(`/agents/v2/${agentId}/api-keys`)
  return response.data
}

export const createAPIKey = async (
  agentId: string,
  name: string,
  expiresInDays?: number
): Promise<{
  success: boolean
  key_id: string
  api_key: string
  name: string
  expires_at: number
  message: string
}> => {
  const response = await api.post(`/agents/v2/${agentId}/api-keys`, {
    name,
    expires_in_days: expiresInDays || 365,
  })
  return response.data
}

export const revokeAPIKey = async (
  agentId: string,
  keyId: string
): Promise<{ success: boolean; message: string }> => {
  const response = await api.post(`/agents/v2/${agentId}/api-keys/${keyId}/revoke`)
  return response.data
}

export const renewAPIKey = async (
  agentId: string,
  keyId: string,
  extendsDays?: number
): Promise<{
  success: boolean
  key_id: string
  new_expires_at: number
  message: string
}> => {
  const response = await api.post(`/agents/v2/${agentId}/api-keys/${keyId}/renew`, {
    extends_days: extendsDays || 365,
  })
  return response.data
}

// ============ Staking API ============

export const depositStake = async (amount: number): Promise<{
  success: boolean
  agent_id: string
  staked_amount: number
  stake_status: string
  stake_tier: string
  locked_stake: number
  pending_rewards: number
  apy: number
  tier_benefits: { max_agents: number; discount: number }
}> => {
  const response = await api.post('/staking/deposit', { amount })
  return response.data
}

export const withdrawStake = async (amount: number): Promise<{
  success: boolean
  agent_id: string
  staked_amount: number
  stake_status: string
  stake_tier: string
  pending_rewards: number
  apy: number
  tier_benefits: { max_agents: number; discount: number }
}> => {
  const response = await api.post('/staking/withdraw', { amount })
  return response.data
}

export const getStakingInfo = async (): Promise<{
  success: boolean
  agent_id: string
  staked_amount: number
  stake_status: string
  stake_tier: string
  locked_stake: number
  unlock_available_at?: number
  pending_rewards: number
  apy: number
  tier_benefits: { max_agents: number; discount: number }
}> => {
  const response = await api.get('/staking/info')
  return response.data
}

export const getStakingRewards = async (): Promise<{
  success: boolean
  agent_id: string
  pending_rewards: number
  total_claimed: number
  last_claim_at?: number
  apy: number
}> => {
  const response = await api.get('/staking/rewards')
  return response.data
}

export const claimRewards = async (): Promise<{
  success: boolean
  agent_id: string
  claimed_amount: number
  new_balance: number
  message: string
}> => {
  const response = await api.post('/staking/claim')
  return response.data
}

// ============ Reputation API ============

export const getReputation = async (): Promise<{
  success: boolean
  agent_id: string
  score: number
  tier: string
  total_transactions: number
  successful_transactions: number
  success_rate: number
  avg_rating: number
  total_ratings: number
}> => {
  const response = await api.get('/reputation')
  return response.data
}

export const getReputationHistory = async (
  limit?: number,
  offset?: number
): Promise<{
  success: boolean
  agent_id: string
  current_score: number
  history: Array<{
    timestamp: number
    event_type: string
    change: number
    reason: string
    related_id?: string
  }>
  total_events: number
}> => {
  const params = new URLSearchParams()
  if (limit) params.append('limit', String(limit))
  if (offset) params.append('offset', String(offset))
  const response = await api.get(`/reputation/history?${params}`)
  return response.data
}

// ============ Wallet API ============

export const getWalletBalance = async (): Promise<{
  success: boolean
  agent_id: string
  balance: number
  staked_amount: number
  locked_amount: number
  pending_rewards: number
  total_assets: number
  stake_tier: string
  tier_benefits: { max_agents: number; discount: number }
}> => {
  const response = await api.get('/wallet/balance')
  return response.data
}

export const getTransactions = async (
  type?: string,
  limit?: number,
  offset?: number
): Promise<{
  success: boolean
  agent_id: string
  transactions: Array<{
    id: string
    transaction_type: string
    amount: number
    status: string
    counterparty_id?: string
    title?: string
    description?: string
    created_at: number
    completed_at?: number
  }>
  total_count: number
  page: number
  page_size: number
}> => {
  const params = new URLSearchParams()
  if (type) params.append('type', type)
  if (limit) params.append('limit', String(limit))
  if (offset) params.append('offset', String(offset))
  const response = await api.get(`/wallet/transactions?${params}`)
  return response.data
}

// ============ Heartbeat API ============

export const sendHeartbeat = async (
  status: 'online' | 'busy' | 'offline' = 'online',
  metadata?: Record<string, unknown>
): Promise<{
  success: boolean
  agent_id: string
  status: string
  ttl_remaining: number
  last_heartbeat: number
  is_alive: boolean
  message: string
}> => {
  const response = await api.post('/heartbeat', { status, metadata })
  return response.data
}

export const getHeartbeatStatus = async (): Promise<{
  success: boolean
  agent_id: string
  status: string
  last_heartbeat: number
  ttl_remaining: number
  is_alive: boolean
  heartbeat_interval: number
  ttl: number
}> => {
  const response = await api.get('/heartbeat/status')
  return response.data
}

export const setOffline = async (): Promise<{
  success: boolean
  agent_id: string
  status: string
  ttl_remaining: number
  last_heartbeat: number
  is_alive: boolean
  message: string
}> => {
  const response = await api.post('/heartbeat/offline')
  return response.data
}

export const setBusy = async (): Promise<{
  success: boolean
  agent_id: string
  status: string
  ttl_remaining: number
  last_heartbeat: number
  is_alive: boolean
  message: string
}> => {
  const response = await api.post('/heartbeat/busy')
  return response.data
}

// ============ System Status API ============

export const getSystemStatus = async (): Promise<{
  version: string
  uptime: { seconds: number; hours: number; days: number }
  platform: { system: string; python: string }
  agents: { online: number; offline: number; busy: number }
  stake_distribution: Record<string, number>
  services: { llm: boolean; prediction: boolean; workflow: boolean; meta_agent: boolean }
  timestamp: number
}> => {
  const response = await api.get('/status')
  return response.data
}

export const getStatsSummary = async (): Promise<{
  total_agents: number
  online_agents: number
  bound_agents: number
  total_stake: number
  total_balance: number
  active_services: number
  active_demands: number
  active_collaborations: number
}> => {
  const response = await api.get('/stats/summary')
  return response.data
}

// ============ Agent Profile v2 API ============

export const getAgentProfileV2 = async (): Promise<{
  success: boolean
  result: {
    agent_id: string
    name: string
    description: string
    capabilities: string[]
    status: string
    reputation: number
    level: number
    binding_status: string
    owner_wallet?: string
    stake_tier: string
    staked_amount: number
    created_at: number
  }
}> => {
  const response = await api.get('/agents/v2/profile')
  return response.data
}

export const updateAgentProfileV2 = async (data: {
  name?: string
  description?: string
  capabilities?: string[]
}): Promise<{
  success: boolean
  result: {
    agent_id: string
    name: string
    updated_fields: string[]
  }
}> => {
  const response = await api.patch('/agents/v2/profile', data)
  return response.data
}

export const getOwnerInfo = async (): Promise<{
  success: boolean
  result: {
    owner_wallet: string
    staked_amount: number
    stake_status: string
    stake_tier: string
    bound_at: number
  }
}> => {
  const response = await api.get('/agents/v2/owner')
  return response.data
}

// ============ Blockchain API ============

export interface BlockchainStatus {
  connected: boolean
  chain_id: number
  network_name: string
  block_number: number
  token_address: string
  token_name: string
  token_symbol: string
}

export interface TokenBalance {
  address: string
  balance_wei: number
  balance_vibe: number
  symbol: string
  name: string
  decimals: number
}

export interface TaxBreakdown {
  amount_vibe: number
  tax_rate: number
  tax_vibe: number
  net_vibe: number
}

/**
 * 获取区块链连接状态
 */
export const getBlockchainStatus = async (): Promise<BlockchainStatus> => {
  const response = await api.get<BlockchainStatus>('/blockchain/status')
  return response.data
}

/**
 * 查询指定地址的VIBE代币余额
 */
export const getTokenBalance = async (address: string): Promise<TokenBalance> => {
  const response = await api.get<TokenBalance>(`/blockchain/balance/${address}`)
  return response.data
}

/**
 * 计算交易税明细
 */
export const getTaxBreakdown = async (amount: number): Promise<TaxBreakdown> => {
  const response = await api.get<TaxBreakdown>(`/blockchain/tax/${amount}`)
  return response.data
}

/**
 * 查询VIBE代币总供应量
 */
export const getTotalSupply = async (): Promise<{ total_supply_vibe: number }> => {
  const response = await api.get<{ total_supply_vibe: number }>('/blockchain/total-supply')
  return response.data
}
