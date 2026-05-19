/**
 * Admin API Client
 * 所有 /api/admin/* 请求的 axios 实例
 */
import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

export const adminApi = axios.create({
  baseURL: '/api/admin',
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：注入 accessToken
adminApi.interceptors.request.use((config) => {
  const authData = localStorage.getItem('usmsb-auth')
  if (authData) {
    const { state } = JSON.parse(authData)
    if (state?.accessToken) {
      config.headers.Authorization = `Bearer ${state.accessToken}`
    }
  }
  return config
})

// 响应拦截器：错误处理
adminApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status

    // Token 过期，重新获取 token
    if (status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        // 从 localStorage 获取最新 token
        const authData = localStorage.getItem('usmsb-auth')
        if (authData) {
          const { state } = JSON.parse(authData)
          if (state?.accessToken) {
            originalRequest.headers.Authorization = `Bearer ${state.accessToken}`
            return adminApi(originalRequest)
          }
        }
      } catch {
        // 失败，登出
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }

    // 403：无权限
    if (status === 403) {
      console.warn('[AdminAPI] 无权限访问:', originalRequest.url)
    }

    return Promise.reject(error)
  }
)

// ==================== Dashboard ====================

export interface DashboardStats {
  // Agent 统计
  totalAgents: number
  onlineAgents: number
  busyAgents: number
  offlineAgents: number
  newAgentsToday: number
  agentTrend: { time: string; online: number; busy: number; offline: number }[]

  // 用户统计
  totalUsers: number
  newUsersToday: number

  // 质押统计
  totalStake: string
  totalStakeUsd: number

  // 业务统计
  activeDemands: number
  activeServices: number
  activeOrders: number
  pendingOrders: number
  totalTransactions: number
  todayTransactionCount: number
  todayTransactionVolume: string
  platformRevenue: string

  // 实时
  lastBlockNumber: number
  lastBlockTimestamp: number
  vibePriceUsd: number
  stakeDistribution: {
    none: number
    bronze: number
    silver: number
    gold: number
    platinum: number
  }
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const { data } = await adminApi.get<DashboardStats>('/dashboard/stats')
  return data
}

// ==================== Agents ====================

export interface Agent {
  agentId: string
  name: string
  agentType: 'ai' | 'human' | 'system'
  status: 'online' | 'busy' | 'offline'
  stake: string
  reputation: number
  capabilities: string[]
  lastHeartbeat: number
  createdAt: number
  ownerWallet: string
  bindingStatus: 'wallet' | 'manual' | 'agent'
}

export interface AgentsResponse {
  agents: Agent[]
  total: number
}

export async function fetchAgents(params?: {
  page?: number
  pageSize?: number
  status?: string
  type?: string
  tier?: string
  search?: string
}): Promise<AgentsResponse> {
  const { data } = await adminApi.get<AgentsResponse>('/agents', { params })
  return data
}

export async function freezeAgent(agentId: string, reason: string): Promise<void> {
  await adminApi.post(`/agents/${agentId}/freeze`, { reason })
}

export async function unfreezeAgent(agentId: string): Promise<void> {
  await adminApi.post(`/agents/${agentId}/unfreeze`)
}

// ==================== Users ====================

export interface User {
  walletAddress: string
  did?: string
  role: string
  stake: string
  reputation: number
  vibeBalance: string
  stakeStatus: 'none' | 'staked' | 'unstaking' | 'unlocked'
  agentId?: string
  createdAt: number
}

export interface UsersResponse {
  users: User[]
  total: number
}

export async function fetchUsers(params?: {
  page?: number
  pageSize?: number
  role?: string
  stakeStatus?: string
  search?: string
}): Promise<UsersResponse> {
  const { data } = await adminApi.get<UsersResponse>('/users', { params })
  return data
}

export async function changeUserRole(
  wallet: string,
  role: string,
  reason: string
): Promise<void> {
  await adminApi.put(`/users/${wallet}/role`, { role, reason })
}

// ==================== Transactions ====================

export interface Transaction {
  id: string
  buyerId: string
  sellerId: string
  amount: string
  status: 'pending' | 'completed' | 'failed' | 'refunded'
  transactionType: 'payment' | 'stake' | 'reward' | 'refund' | 'governance'
  escrowTxHash?: string
  rating?: number
  createdAt: number
  completedAt?: number
}

export interface TransactionsResponse {
  transactions: Transaction[]
  total: number
  summary?: {
    todayVolume: string
    todayCount: number
    avgAmount: string
    successRate: number
  }
}

export async function fetchTransactions(params?: {
  page?: number
  pageSize?: number
  type?: string
  status?: string
  startTime?: number
  endTime?: number
  minAmount?: number
  maxAmount?: number
  search?: string
}): Promise<TransactionsResponse> {
  const { data } = await adminApi.get<TransactionsResponse>('/transactions', { params })
  return data
}

// ==================== Orders ====================

export interface Order {
  orderId: string
  demandAgentId: string
  supplyAgentId?: string
  status: 'pending' | 'in_progress' | 'delivered' | 'completed' | 'cancelled' | 'disputed'
  priority: 'low' | 'medium' | 'high'
  vibeLocked: string
  chainOrderId?: string
  createdAt: number
  completedAt?: number
}

export interface OrdersResponse {
  orders: Order[]
  total: number
  stats?: {
    total: number
    inProgress: number
    completed: number
    disputed: number
  }
}

export async function fetchOrders(params?: {
  page?: number
  pageSize?: number
  status?: string
  priority?: string
}): Promise<OrdersResponse> {
  const { data } = await adminApi.get<OrdersResponse>('/orders', { params })
  return data
}

// ==================== Nodes ====================

export interface NodeHealth {
  nodeId: string
  name: string
  ip: string
  status: 'online' | 'warning' | 'critical' | 'maintenance'
  agentCount: number
  onlineCount: number
  cpuPercent: number
  memoryPercent: number
  diskPercent: number
  networkIn: number
  networkOut: number
  latency: number
  lastHeartbeat: number
  uptime: number
  version: string
  createdAt: number
}

export interface NodesResponse {
  nodes: NodeHealth[]
  total: number
}

export async function fetchNodes(params?: {
  page?: number
  pageSize?: number
  status?: string
  search?: string
}): Promise<NodesResponse> {
  const { data } = await adminApi.get<NodesResponse>('/nodes', { params })
  return data
}

// ==================== Contracts ====================

export interface ContractOverview {
  name: string
  address: string
  category: 'staking' | 'rewards' | 'governance' | 'market' | 'orders'
  balance: string
  status: 'ok' | 'warning' | 'error'
}

export async function fetchContractsOverview(): Promise<ContractOverview[]> {
  const { data } = await adminApi.get<ContractOverview[]>('/contracts/overview')
  return data
}

export interface StakingData {
  totalStaked: string
  currentAPY: number
  stakerCount: number
  totalRewardsDistributed: string
  dividendBalance: string
  vibePrice: number
  stakeDistribution: { bronze: number; silver: number; gold: number; platinum: number }
}

export async function fetchStakingData(): Promise<StakingData> {
  const { data } = await adminApi.get<StakingData>('/contracts/staking')
  return data
}

export interface StakeUserInfo {
  stakedAmount: string
  lockPeriod: number
  startTime: number
  tier: string
  timeMultiplier: number
  votingPower: string
  pendingReward: string
}

export async function fetchStakeUserInfo(address: string): Promise<StakeUserInfo> {
  const { data } = await adminApi.get<StakeUserInfo>(`/contracts/staking/user/${address}`)
  return data
}

// ==================== System ====================

export interface ServiceHealth {
  name: string
  status: 'ok' | 'degraded' | 'down'
  latencyMs: number
  message?: string
}

export interface HealthResponse {
  services: ServiceHealth[]
  lastCheck: number
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await adminApi.get<HealthResponse>('/system/health')
  return data
}

// ==================== Matching ====================

export interface MatchingFunnel {
  demands: number
  aiMatch: number
  negotiations: number
  agreements: number
  deliveries: number
  avgMatchTime: string
  avgNegotiationRounds: number
  agreementRate: number
  deliveryRate: number
}

export async function fetchMatchingFunnel(timeRange: '7d' | '30d' | '90d' = '7d'): Promise<MatchingFunnel> {
  const { data } = await adminApi.get<MatchingFunnel>('/matching/funnel', { params: { timeRange } })
  return data
}

// ==================== Governance ====================

export interface Proposal {
  id: number
  title: string
  proposalType: 'general' | 'incentive' | 'parameter' | 'emergency'
  status: 'active' | 'passed' | 'rejected' | 'expired'
  votesFor: string
  votesAgainst: string
  deadline: number
  proposerId: string
  description?: string
}

export interface ProposalsResponse {
  proposals: Proposal[]
  total: number
}

export async function fetchProposals(params?: {
  page?: number
  pageSize?: number
  status?: string
  type?: string
}): Promise<ProposalsResponse> {
  const { data } = await adminApi.get<ProposalsResponse>('/governance/proposals', { params })
  return data
}
