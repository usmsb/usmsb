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

export default api
