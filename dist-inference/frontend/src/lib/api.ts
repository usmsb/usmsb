import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — attach wallet address from localStorage
apiClient.interceptors.request.use((config) => {
  try {
    const auth = JSON.parse(localStorage.getItem('usmsb-auth') || '{}')
    if (auth.state?.walletAddress) {
      config.headers['X-Wallet-Address'] = auth.state.walletAddress
    }
  } catch {}
  return config
})

// Response interceptor — handle errors
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.message || err.message || 'Network error'
    return Promise.reject(new Error(message))
  }
)

// GPU Pool
export const fetchGpuPool = () => apiClient.get('/gpu-pool').then(r => r.data)
export const fetchNode = (nodeId: string) => apiClient.get(`/nodes/${nodeId}`).then(r => r.data)

// Models
export const fetchModels = () => apiClient.get('/models').then(r => r.data)

// Requests
export const fetchRequests = (params?: { page?: number; page_size?: number; status?: string }) =>
  apiClient.get('/requests', { params }).then(r => r.data)
export const fetchRequest = (id: string) => apiClient.get(`/requests/${id}`).then(r => r.data)

// Revenue
export const fetchRevenueStats = () => apiClient.get('/revenue/stats').then(r => r.data)
export const fetchRevenueTrend = (days = 30) =>
  apiClient.get('/revenue/trend', { params: { days } }).then(r => r.data)
export const fetchNodeRankings = () => apiClient.get('/revenue/nodes').then(r => r.data)
export const fetchWithdrawals = (params?: { page?: number; page_size?: number }) =>
  apiClient.get('/revenue/withdrawals', { params }).then(r => r.data)

// Users
export const fetchUsers = (params?: { page?: number; page_size?: number; search?: string }) =>
  apiClient.get('/users', { params }).then(r => r.data)
export const fetchUser = (wallet: string) => apiClient.get(`/users/${wallet}`).then(r => r.data)

// Node Executor
export const fetchNodeStatus = () => apiClient.get('/node/status').then(r => r.data)
export const fetchNodeEarnings = (params?: { days?: number }) =>
  apiClient.get('/node/earnings', { params }).then(r => r.data)
export const fetchNodeModels = () => apiClient.get('/node/models').then(r => r.data)
export const loadModel = (modelId: string) => apiClient.post('/node/models/load', { model_id: modelId }).then(r => r.data)
export const unloadModel = (modelId: string) => apiClient.post('/node/models/unload', { model_id: modelId }).then(r => r.data)
export const fetchNodeHistory = (params?: { page?: number; page_size?: number }) =>
  apiClient.get('/node/history', { params }).then(r => r.data)
export const updateNodeSettings = (settings: Record<string, unknown>) =>
  apiClient.put('/node/settings', settings).then(r => r.data)

// Platform settings
export const fetchSettings = () => apiClient.get('/settings').then(r => r.data)
export const updateSettings = (settings: Record<string, unknown>) =>
  apiClient.put('/settings', settings).then(r => r.data)
