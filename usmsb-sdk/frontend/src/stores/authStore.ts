import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface AuthState {
  // Wallet state
  address: string | null
  chainId: number | null
  isConnected: boolean

  // DID state
  did: string | null

  // Session state
  sessionId: string | null
  accessToken: string | null

  // User state
  agentId: string | null
  stake: number
  reputation: number
  role: 'supplier' | 'demander' | 'both' | null

  // Profile state
  name: string
  bio: string
  skills: string[]
  hourlyRate: number
  availability: string

  // Actions
  setWallet: (address: string, chainId: number) => void
  setDid: (did: string) => void
  setSession: (sessionId: string, accessToken: string) => void
  setAgent: (agentId: string, stake: number, reputation: number) => void
  setRole: (role: 'supplier' | 'demander' | 'both') => void
  setProfile: (profile: {
    name: string
    bio: string
    skills: string[]
    hourlyRate: number
    availability: string
  }) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      // Initial state
      address: null,
      chainId: null,
      isConnected: false,
      did: null,
      sessionId: null,
      accessToken: null,
      agentId: null,
      stake: 0,
      reputation: 0,
      role: null,
      name: '',
      bio: '',
      skills: [],
      hourlyRate: 0,
      availability: 'full-time',

      // Actions
      setWallet: (address, chainId) =>
        set({
          address,
          chainId,
          isConnected: true,
        }),

      setDid: (did) => set({ did }),

      setSession: (sessionId, accessToken) =>
        set({
          sessionId,
          accessToken,
        }),

      setAgent: (agentId, stake, reputation) =>
        set({
          agentId,
          stake,
          reputation,
        }),

      setRole: (role) => set({ role }),

      setProfile: (profile) =>
        set({
          name: profile.name,
          bio: profile.bio,
          skills: profile.skills,
          hourlyRate: profile.hourlyRate,
          availability: profile.availability,
        }),

      logout: () =>
        set({
          address: null,
          chainId: null,
          isConnected: false,
          did: null,
          sessionId: null,
          accessToken: null,
          agentId: null,
          stake: 0,
          reputation: 0,
          role: null,
          name: '',
          bio: '',
          skills: [],
          hourlyRate: 0,
          availability: 'full-time',
        }),
    }),
    {
      name: 'usmsb-auth',
      partialize: (state) => ({
        address: state.address,
        chainId: state.chainId,
        isConnected: state.isConnected,
        did: state.did,
        sessionId: state.sessionId,
        accessToken: state.accessToken,
        agentId: state.agentId,
        stake: state.stake,
        reputation: state.reputation,
        role: state.role,
        name: state.name,
        bio: state.bio,
        skills: state.skills,
        hourlyRate: state.hourlyRate,
        availability: state.availability,
      }),
    }
  )
)
