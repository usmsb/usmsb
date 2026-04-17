import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  walletAddress: string | null
  isConnected: boolean
  isConnecting: boolean
  role: 'platform_admin' | 'node_owner' | 'api_user' | 'guest'
  setWallet: (address: string) => void
  setConnecting: (v: boolean) => void
  setRole: (role: AuthState['role']) => void
  disconnect: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      walletAddress: null,
      isConnected: false,
      isConnecting: false,
      role: 'guest',
      setWallet: (address) => set({ walletAddress: address, isConnected: true, isConnecting: false }),
      setConnecting: (v) => set({ isConnecting: v }),
      setRole: (role) => set({ role }),
      disconnect: () => set({ walletAddress: null, isConnected: false, role: 'guest' }),
    }),
    { name: 'usmsb-auth' }
  )
)
