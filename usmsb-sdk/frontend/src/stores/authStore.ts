import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type UserRole = 'superadmin' | 'developer' | 'node_admin' | 'node_operator' | 'human' | 'ai_owner' | 'ai_agent'
export type BindingType = 'wallet' | 'manual' | 'agent'  // wallet=真实钱包, manual=手动输入, agent=AI Agent
export type StakeStatus = 'none' | 'staked' | 'unstaking' | 'unlocked'

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  'superadmin': '超级管理员',
  'developer': '开发人员',
  'node_admin': '节点管理员',
  'node_operator': '节点运营',
  'human': '普通用户',
  'ai_owner': 'AI主人',
  'ai_agent': 'AI Agent',
}

export interface StakeInfo {
  vibeBalance: number
  stakedAmount: number
  lockedAmount: number
  stakeStatus: StakeStatus
  unlockAvailableAt: number | null
  stakeRequired: boolean
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

export interface AuthState {
  // Wallet state
  address: string | null
  chainId: number | null
  isConnected: boolean

  // Binding type
  bindingType: BindingType | null

  // User role (permission system)
  userRole: UserRole

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

  // Permission info
  permissions: string[]
  votingPower: number

  // Staking state
  vibeBalance: number
  stakedAmount: number
  lockedAmount: number
  stakeStatus: StakeStatus
  unlockAvailableAt: number | null
  stakeRequired: boolean

  // Agent Wallet state (方案A: 单独创建的钱包)
  agentWallets: AgentWalletInfo[]
  currentAgentWallet: AgentWalletInfo | null

  // Actions
  setWallet: (address: string, chainId: number) => void
  setManualIdentifier: (identifier: string) => void
  setAgentBinding: (agentId: string) => void
  setBindingType: (type: BindingType) => void
  setUserRole: (role: UserRole) => void
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
  setPermissions: (permissions: string[], votingPower: number) => void
  updateStakeInfo: (info: Partial<StakeInfo>) => void
  setStakeRequired: (required: boolean) => void
  // Agent Wallet actions
  setAgentWallets: (wallets: AgentWalletInfo[]) => void
  setCurrentAgentWallet: (wallet: AgentWalletInfo | null) => void
  updateAgentWallet: (agentId: string, updates: Partial<AgentWalletInfo>) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      // Initial state
      address: null,
      chainId: null,
      isConnected: false,
      bindingType: null,
      userRole: 'human',
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
      permissions: [],
      votingPower: 0,
      // Staking state
      vibeBalance: 10000,
      stakedAmount: 0,
      lockedAmount: 0,
      stakeStatus: 'none',
      unlockAvailableAt: null,
      stakeRequired: true,

      // Agent Wallet state
      agentWallets: [],
      currentAgentWallet: null,

      // Actions
      setWallet: (address, chainId) =>
        set({
          address,
          chainId,
          isConnected: true,
          bindingType: 'wallet',
        }),

      setManualIdentifier: (identifier) =>
        set({
          address: identifier,
          chainId: null,
          isConnected: true,
          bindingType: 'manual',
        }),

      setAgentBinding: (agentId) =>
        set({
          address: agentId,
          chainId: null,
          isConnected: true,
          bindingType: 'agent',
          userRole: 'ai_agent',
        }),

      setBindingType: (type) => set({ bindingType: type }),

      setUserRole: (role) => set({ userRole: role }),

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

      setPermissions: (permissions, votingPower) =>
        set({ permissions, votingPower }),

      updateStakeInfo: (info) =>
        set((state) => ({
          vibeBalance: info.vibeBalance ?? state.vibeBalance,
          stakedAmount: info.stakedAmount ?? state.stakedAmount,
          lockedAmount: info.lockedAmount ?? state.lockedAmount,
          stakeStatus: info.stakeStatus ?? state.stakeStatus,
          unlockAvailableAt: info.unlockAvailableAt ?? state.unlockAvailableAt,
          stakeRequired: info.stakeRequired ?? state.stakeRequired,
        })),

      setStakeRequired: (required) => set({ stakeRequired: required }),

      // Agent Wallet actions
      setAgentWallets: (wallets) => set({ agentWallets: wallets }),

      setCurrentAgentWallet: (wallet) => set({ currentAgentWallet: wallet }),

      updateAgentWallet: (agentId, updates) =>
        set((state) => ({
          agentWallets: state.agentWallets.map((w) =>
            w.agentId === agentId ? { ...w, ...updates } : w
          ),
          currentAgentWallet: state.currentAgentWallet?.agentId === agentId
            ? { ...state.currentAgentWallet, ...updates }
            : state.currentAgentWallet,
        })),

      logout: () =>
        set({
          address: null,
          chainId: null,
          isConnected: false,
          bindingType: null,
          userRole: 'human',
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
          permissions: [],
          votingPower: 0,
          vibeBalance: 10000,
          stakedAmount: 0,
          lockedAmount: 0,
          stakeStatus: 'none',
          unlockAvailableAt: null,
          stakeRequired: true,
          agentWallets: [],
          currentAgentWallet: null,
        }),
    }),
    {
      name: 'usmsb-auth',
      partialize: (state) => ({
        address: state.address,
        chainId: state.chainId,
        isConnected: state.isConnected,
        bindingType: state.bindingType,
        userRole: state.userRole,
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
        permissions: state.permissions,
        votingPower: state.votingPower,
        vibeBalance: state.vibeBalance,
        stakedAmount: state.stakedAmount,
        lockedAmount: state.lockedAmount,
        stakeStatus: state.stakeStatus,
        unlockAvailableAt: state.unlockAvailableAt,
        stakeRequired: state.stakeRequired,
        agentWallets: state.agentWallets,
        currentAgentWallet: state.currentAgentWallet,
      }),
    }
  )
)
