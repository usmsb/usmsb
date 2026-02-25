import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const authData = localStorage.getItem('usmsb-auth')
  if (authData) {
    const { state } = JSON.parse(authData)
    if (state?.accessToken) {
      config.headers.Authorization = `Bearer ${state.accessToken}`
    }
  }
  return config
})

export interface NonceResponse {
  nonce: string
  expiresAt: number
}

export interface VerifyRequest {
  message: string
  signature: string
  address: string
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

export interface StakeResponse {
  success: boolean
  transactionHash: string
  newStake: number
  newReputation: number
  skipped?: boolean
}

export interface StakeConfigResponse {
  stakeRequired: boolean
  minStakeAmount: number
  defaultBalance: number
  unstakingPeriodDays: number
}

export interface BalanceResponse {
  balance: number
  stakedAmount: number
  lockedAmount: number
  totalBalance: number
  stakeStatus: 'none' | 'staked' | 'unstaking' | 'unlocked'
  unlockAvailableAt?: number
}

export interface UnstakeResponse {
  success: boolean
  lockedAmount: number
  unlockAvailableAt: number
  message: string
}

export interface ProfileCreateRequest {
  name: string
  bio: string
  skills: string[]
  hourlyRate: number
  availability: string
  role: 'supplier' | 'demander' | 'both'
}

export interface ProfileResponse {
  success: boolean
  agentId: string
}

// Get nonce for wallet signature
export const getNonce = async (address: string): Promise<NonceResponse> => {
  const response = await api.get<NonceResponse>(`/auth/nonce/${address}`)
  return response.data
}

// Verify wallet signature and create session
export const verifySignature = async (data: VerifyRequest): Promise<VerifyResponse> => {
  const response = await api.post<VerifyResponse>('/auth/verify', data)
  return response.data
}

// Get current session
export const getSession = async (): Promise<SessionResponse> => {
  const response = await api.get<SessionResponse>('/auth/session')
  return response.data
}

// Logout
export const logout = async (): Promise<void> => {
  await api.delete('/auth/session')
}

// Stake tokens
export const stakeTokens = async (amount: number): Promise<StakeResponse> => {
  const response = await api.post<StakeResponse>('/auth/stake', { amount })
  return response.data
}

// Create profile
export const createProfile = async (data: ProfileCreateRequest): Promise<ProfileResponse> => {
  const response = await api.post<ProfileResponse>('/auth/profile', data)
  return response.data
}

// Get stake config
export const getStakeConfig = async (): Promise<StakeConfigResponse> => {
  const response = await api.get<StakeConfigResponse>('/auth/config')
  return response.data
}

// Get balance info
export const getBalance = async (): Promise<BalanceResponse> => {
  const response = await api.get<BalanceResponse>('/auth/balance')
  return response.data
}

// Request unstake
export const requestUnstake = async (amount?: number): Promise<UnstakeResponse> => {
  const response = await api.post<UnstakeResponse>('/auth/unstake', { amount })
  return response.data
}

// Cancel unstake
export const cancelUnstake = async (): Promise<{ success: boolean; message: string }> => {
  const response = await api.post<{ success: boolean; message: string }>('/auth/unstake/cancel')
  return response.data
}

// Confirm unstake
export const confirmUnstake = async (): Promise<{ success: boolean; unlockedAmount: number; message: string }> => {
  const response = await api.post<{ success: boolean; unlockedAmount: number; message: string }>('/auth/unstake/confirm')
  return response.data
}

// ==================== Agent Wallet APIs ====================

export interface CreateAgentWalletRequest {
  agent_id: string
  agent_address: string
}

export interface AgentWalletResponse {
  success: boolean
  agentId: string
  walletAddress: string
  agentAddress: string
  balance: number
  stakedAmount: number
  stakeStatus: string
}

export interface AgentWalletInfo {
  agentId: string
  walletAddress: string
  agentAddress: string
  balance: number
  stakedAmount: number
  stakeStatus: string
  maxPerTx: number
  dailyLimit: number
  dailySpent: number
  remainingDailyLimit: number
  isRegistered: boolean
  unlockAvailableAt?: number | null
}

export interface AgentWalletListResponse {
  wallets: AgentWalletInfo[]
}

export interface AgentDepositRequest {
  amount: number
}

export interface AgentDepositResponse {
  success: boolean
  agentId: string
  newBalance: number
  newStakedAmount: number
  message: string
}

export interface AgentTransferRequest {
  to_address: string
  amount: number
}

export interface AgentTransferResponse {
  success: boolean
  agentId: string
  toAddress: string
  amount: number
  newBalance: number
  message: string
}

export interface AgentLimitsRequest {
  max_per_tx: number
  daily_limit: number
}

// Create agent wallet (方案A: 单独创建)
export const createAgentWallet = async (data: CreateAgentWalletRequest): Promise<AgentWalletResponse> => {
  const response = await api.post<AgentWalletResponse>('/auth/agent/wallet', data)
  return response.data
}

// Get agent wallet info
export const getAgentWallet = async (agentId: string): Promise<AgentWalletInfo> => {
  const response = await api.get<AgentWalletInfo>(`/auth/agent/wallet/${agentId}`)
  return response.data
}

// Get all agent wallets for current user
export const getAgentWallets = async (): Promise<AgentWalletListResponse> => {
  const response = await api.get<AgentWalletListResponse>('/auth/agent/wallets')
  return response.data
}

// Deposit to agent wallet (充值)
export const depositToAgentWallet = async (agentId: string, amount: number): Promise<AgentDepositResponse> => {
  const response = await api.post<AgentDepositResponse>(`/auth/agent/wallet/${agentId}/deposit`, { amount })
  return response.data
}

// Transfer from agent wallet
export const transferFromAgentWallet = async (agentId: string, toAddress: string, amount: number): Promise<AgentTransferResponse> => {
  const response = await api.post<AgentTransferResponse>(`/auth/agent/wallet/${agentId}/transfer`, {
    to_address: toAddress,
    amount
  })
  return response.data
}

// Stake from agent wallet
export const stakeAgentWallet = async (agentId: string, amount: number): Promise<{ success: boolean; newBalance: number; newStakedAmount: number }> => {
  const response = await api.post(`/auth/agent/wallet/${agentId}/stake`, { amount })
  return response.data
}

// Unstake from agent wallet
export const unstakeAgentWallet = async (agentId: string, amount: number): Promise<{ success: boolean; unlockedAmount: number; unlockAvailableAt: number }> => {
  const response = await api.post(`/auth/agent/wallet/${agentId}/unstake`, { amount })
  return response.data
}

// Update agent wallet limits
export const updateAgentWalletLimits = async (agentId: string, maxPerTx: number, dailyLimit: number): Promise<{ success: boolean }> => {
  const response = await api.post(`/auth/agent/wallet/${agentId}/limits`, {
    max_per_tx: maxPerTx,
    daily_limit: dailyLimit
  })
  return response.data
}

// Delete agent wallet
export const deleteAgentWallet = async (agentId: string): Promise<{ success: boolean }> => {
  const response = await api.delete(`/auth/agent/wallet/${agentId}`)
  return response.data
}

export default api
