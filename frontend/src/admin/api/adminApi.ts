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

    if (status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const authData = localStorage.getItem('usmsb-auth')
        if (authData) {
          const { state } = JSON.parse(authData)
          if (state?.accessToken) {
            originalRequest.headers.Authorization = `Bearer ${state.accessToken}`
            return adminApi(originalRequest)
          }
        }
        useAuthStore.getState().logout()
        window.location.href = '/login'
      } catch {
        useAuthStore.getState().logout()
        window.location.href = '/login'
      }
    }

    if (status === 403) {
      console.warn('[AdminAPI] 无权限访问:', originalRequest.url)
    }

    return Promise.reject(error)
  }
)

// ==================== Dashboard ====================

export interface DashboardData {
  total_agents: number
  online_agents: number
  total_users: number
  total_transactions: number
  total_transaction_volume: number
  total_orders: number
  pending_orders: number
  completed_orders: number
  total_volume_24h: number
  tx_count_24h: number
  active_negotiations: number
  active_proposals: number
  agent_growth: number[]
  tx_volume_growth: number[]
  top_agents: Array<{
    agent_id: string
    name: string
    stake: number
    status: string
    reputation: number
  }>
  recent_transactions: Array<{
    tx_id: string
    type: string
    amount: number
    status: string
    from_address: string
    to_address: string
    created_at: number
  }>
}

export const fetchDashboard = (): Promise<DashboardData> =>
  adminApi.get<DashboardData>('/dashboard').then(r => r.data)

// Legacy alias
export const fetchDashboardStats = fetchDashboard

// ==================== Agents ====================

export interface AgentListData {
  agents: Array<{
    agent_id: string
    name: string
    agent_type: string
    status: string
    stake: number
    balance: number
    reputation: number
    capabilities: string[]
    endpoint: string
    protocol: string
    created_at: number
    last_heartbeat: number
  }>
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const fetchAgents = (params?: {
  page?: number
  page_size?: number
  status?: string
  agent_type?: string
  search?: string
}): Promise<AgentListData> =>
  adminApi.get<AgentListData>('/agents', { params }).then(r => r.data)

export const fetchAgentDetail = (agentId: string) =>
  adminApi.get(`/agents/${agentId}`).then(r => r.data)

// ==================== Users ====================

export interface UserListData {
  users: Array<{
    user_id: string
    address: string
    did: string
    user_role: string
    stake_amount: number
    balance: number
    status: string
    created_at: number
    last_active: number
  }>
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const fetchUsers = (params?: {
  page?: number
  page_size?: number
  role?: string
  search?: string
}): Promise<UserListData> =>
  adminApi.get<UserListData>('/users', { params }).then(r => r.data)

export const updateUserRole = (userId: string, newRole: string) =>
  adminApi.patch(`/users/${userId}/role`, null, { params: { new_role: newRole } }).then(r => r.data)

// ==================== Transactions ====================

export interface TransactionListData {
  transactions: Array<{
    tx_id: string
    type: string
    amount: number
    fee: number
    status: string
    from_address: string
    to_address: string
    tx_hash: string
    created_at: number
  }>
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const fetchTransactions = (params?: {
  page?: number
  page_size?: number
  status?: string
  tx_type?: string
  address?: string
}): Promise<TransactionListData> =>
  adminApi.get<TransactionListData>('/transactions', { params }).then(r => r.data)

// ==================== Orders ====================

export interface OrderListData {
  orders: Array<{
    order_id: string
    creator: string
    service_type: string
    total_budget: number
    spent: number
    status: string
    matched_agents: string
    created_at: number
    updated_at: number
  }>
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const fetchOrders = (params?: {
  page?: number
  page_size?: number
  status?: string
  service_type?: string
}): Promise<OrderListData> =>
  adminApi.get<OrderListData>('/orders', { params }).then(r => r.data)

// ==================== Nodes ====================

export interface NodeListData {
  nodes: Array<{
    node_id: string
    name: string
    status: string
    agent_count: number
    cpu_percent: number
    memory_percent: number
    region: string
    version: string
    last_heartbeat: number
  }>
  total: number
  online: number
  offline: number
}

export const fetchNodes = (): Promise<NodeListData> =>
  adminApi.get<NodeListData>('/nodes').then(r => r.data)

// ==================== Matching ====================

export interface MatchingData {
  funnel: {
    published: number
    negotiating: number
    matched: number
    completed: number
  }
  avg_match_time: number
  success_rate: number
  top_services: Array<{ service_type: string; count: number }>
  recent_matches: Record<string, unknown>[]
}

export const fetchMatching = (): Promise<MatchingData> =>
  adminApi.get<MatchingData>('/matching').then(r => r.data)

// ==================== Gene Capsules ====================

export interface GeneCapsuleListData {
  capsules: Record<string, unknown>[]
  total: number
}

export const fetchGeneCapsules = (params?: { page?: number; page_size?: number }): Promise<GeneCapsuleListData> =>
  adminApi.get<GeneCapsuleListData>('/gene-capsules', { params }).then(r => r.data)

// ==================== Intelligence ====================

export interface IntelligenceData {
  llm_calls_total: number
  token_usage: Record<string, number>
  active_sessions: number
  avg_response_time: number
  top_capabilities: Array<{ capability: string; count: number }>
}

export const fetchIntelligence = (): Promise<IntelligenceData> =>
  adminApi.get<IntelligenceData>('/intelligence').then(r => r.data)

// ==================== Governance ====================

export interface GovernanceData {
  proposals: Record<string, unknown>[]
  active_proposals: number
  total_votes: number
  participation_rate: number
}

export const fetchGovernance = (): Promise<GovernanceData> =>
  adminApi.get<GovernanceData>('/governance').then(r => r.data)

// ==================== System ====================

export interface SystemHealthData {
  status: string
  uptime_seconds: number
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  db_size_mb: number
  api_response_time_ms: number
  components: Record<string, string>
}

export const fetchSystemHealth = (): Promise<SystemHealthData> =>
  adminApi.get<SystemHealthData>('/system/health').then(r => r.data)

export const fetchSystemConfig = (): Promise<Record<string, string>> =>
  adminApi.get<Record<string, string>>('/system/config').then(r => r.data)

export interface SystemLogsData {
  logs: Array<Record<string, unknown>>
  total: number
}

export const fetchSystemLogs = (params?: {
  page?: number
  page_size?: number
  level?: string
  search?: string
}): Promise<SystemLogsData> =>
  adminApi.get<SystemLogsData>('/system/logs', { params }).then(r => r.data)

// ==================== Permissions ====================

export interface PermissionMatrixData {
  matrix: Array<Record<string, unknown>>
  roles: string[]
}

export const fetchPermissions = (): Promise<PermissionMatrixData> =>
  adminApi.get<PermissionMatrixData>('/permissions').then(r => r.data)
