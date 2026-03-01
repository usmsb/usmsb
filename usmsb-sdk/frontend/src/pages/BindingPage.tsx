import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Wallet,
  Shield,
  AlertCircle,
  CheckCircle,
  Loader2,
  ChevronRight,
  Info,
} from 'lucide-react'
import { useAccount, useConnect, useDisconnect, useSignMessage } from 'wagmi'
import { useAuthStore } from '@/stores/authStore'
import { completeBinding, getSystemStatus, getAuthNonce, verifyAuth } from '@/lib/api'
import clsx from 'clsx'

type BindingStep = 'connect' | 'sign' | 'stake' | 'complete'

const STAKE_TIERS = [
  { tier: 'BRONZE', min: 100, max: 999, label: 'Bronze', agents: 1, discount: '0%' },
  { tier: 'SILVER', min: 1000, max: 4999, label: 'Silver', agents: 3, discount: '5%' },
  { tier: 'GOLD', min: 5000, max: 9999, label: 'Gold', agents: 10, discount: '10%' },
  { tier: 'PLATINUM', min: 10000, max: Infinity, label: 'Platinum', agents: 50, discount: '20%' },
]

export default function BindingPage() {
  const { bindingCode } = useParams<{ bindingCode: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const { address, isConnected } = useAccount()
  const { connect, connectors, isPending: isConnecting } = useConnect()
  const { disconnect } = useDisconnect()
  const { signMessageAsync } = useSignMessage()

  const { setWallet, setUserRole, setPermissions, updateStakeInfo } = useAuthStore()

  const [step, setStep] = useState<BindingStep>('connect')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedAmount, setSelectedAmount] = useState(1000)
  const [agentInfo, setAgentInfo] = useState<{
    agent_id?: string
    agent_name?: string
  }>({})
  const [bindingResult, setBindingResult] = useState<{
    success: boolean
    agent_id: string
    stake_tier: string
    message: string
  } | null>(null)

  // Check if wallet is already connected
  useEffect(() => {
    if (isConnected && address) {
      setWallet(address, 1) // Default to chainId 1 (Ethereum mainnet)
      if (step === 'connect') {
        setStep('sign')
      }
    }
  }, [isConnected, address, setWallet, step])

  // Fetch agent info from binding code
  useEffect(() => {
    const fetchBindingInfo = async () => {
      if (!bindingCode) return

      try {
        // In a real implementation, we'd have an endpoint to get binding info
        // For now, we'll proceed with the code
        console.log('Binding code:', bindingCode)
      } catch (err) {
        setError('Invalid or expired binding code')
      }
    }

    fetchBindingInfo()
  }, [bindingCode])

  const handleConnectWallet = async (connectorIndex = 0) => {
    setError(null)
    const connector = connectors[connectorIndex]
    if (!connector) {
      setError('No wallet connector available')
      return
    }

    try {
      connect({ connector })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect wallet')
    }
  }

  const handleSignMessage = async () => {
    if (!address) {
      setError('Wallet not connected')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      // Step 1: Get nonce from backend
      const nonceResponse = await getAuthNonce(address)

      // Step 2: Create SIWE message
      const message = `usmsb.io wants you to sign in with your Ethereum account:
${address}

I accept the Terms of Service: https://usmsb.io/terms

Binding Agent with code: ${bindingCode}

URI: https://usmsb.io
Version: 1
Chain ID: 1
Nonce: ${nonceResponse.nonce}
Issued At: ${new Date().toISOString()}`

      // Step 3: Sign message
      const signature = await signMessageAsync({ message })

      // Step 4: Verify signature with backend
      const authResponse = await verifyAuth(message, signature, address)

      // Step 5: Save session to authStore
      const { setSession } = useAuthStore.getState()
      setSession(authResponse.sessionId, authResponse.accessToken)

      console.log('Auth successful:', authResponse)
      setStep('stake')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to sign message')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCompleteBinding = async () => {
    if (!bindingCode) {
      setError('Invalid binding code')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const result = await completeBinding(bindingCode, selectedAmount)

      setBindingResult({
        success: result.success,
        agent_id: result.agent_id,
        stake_tier: result.stake_tier,
        message: result.message,
      })

      // Update auth store
      setUserRole('ai_owner')
      setPermissions([], 0)
      updateStakeInfo({
        stakedAmount: selectedAmount,
        stakeStatus: 'staked',
        stakeRequired: false,
      })

      setStep('complete')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to complete binding'
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const getSelectedTier = () => {
    return STAKE_TIERS.find(t => selectedAmount >= t.min && selectedAmount <= t.max) || STAKE_TIERS[0]
  }

  // Neon color mapping
  const neonColorMap = {
    'neon-blue': { color: '#00f5ff', textClass: 'text-neon-blue', borderClass: 'border-neon-blue/50' },
    'neon-purple': { color: '#bf00ff', textClass: 'text-neon-purple', borderClass: 'border-neon-purple/50' },
    'neon-green': { color: '#00ff88', textClass: 'text-neon-green', borderClass: 'border-neon-green/50' },
    'neon-pink': { color: '#ff00ff', textClass: 'text-neon-pink', borderClass: 'border-neon-pink/50' },
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            {t('binding.title', 'Bind Agent')}
          </h1>
          <p className="text-gray-400">
            {t('binding.subtitle', 'Complete the binding process to stake VIBE for your agent')}
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex justify-center mb-8">
          {(['connect', 'sign', 'stake', 'complete'] as BindingStep[]).map((s, i) => (
            <div key={s} className="flex items-center">
              <div
                className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                  step === s || (['connect', 'sign', 'stake', 'complete'].indexOf(step) > i)
                    ? 'bg-neon-blue text-gray-900'
                    : 'bg-gray-700 text-gray-400'
                )}
              >
                {i + 1}
              </div>
              {i < 3 && (
                <div
                  className={clsx(
                    'w-12 h-0.5 mx-1',
                    ['connect', 'sign', 'stake', 'complete'].indexOf(step) > i
                      ? 'bg-neon-blue'
                      : 'bg-gray-700'
                  )}
                />
              )}
            </div>
          ))}
        </div>

        {/* Main Card */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
          {/* Error Display */}
          {error && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-400">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {/* Step 1: Connect Wallet */}
          {step === 'connect' && (
            <div className="space-y-4">
              <div className="text-center">
                <Wallet className="w-16 h-16 mx-auto mb-4 text-neon-blue" />
                <h2 className="text-xl font-semibold text-white mb-2">
                  {t('binding.connectWallet', 'Connect Your Wallet')}
                </h2>
                <p className="text-gray-400 text-sm">
                  {t('binding.connectWalletDesc', 'Connect your wallet to proceed with binding')}
                </p>
              </div>

              <div className="space-y-2">
                {connectors.map((connector, index) => (
                  <button
                    key={connector.id}
                    onClick={() => handleConnectWallet(index)}
                    disabled={isConnecting}
                    className={clsx(
                      'w-full py-3 px-4 rounded-lg flex items-center justify-center gap-2',
                      'bg-neon-blue hover:bg-neon-blue/80 text-gray-900 font-medium',
                      'transition-all duration-200',
                      'disabled:opacity-50 disabled:cursor-not-allowed'
                    )}
                  >
                    {isConnecting ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        {t('binding.connecting', 'Connecting...')}
                      </>
                    ) : (
                      <>
                        <Wallet className="w-5 h-5" />
                        {connector.name}
                      </>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Sign Message */}
          {step === 'sign' && (
            <div className="space-y-4">
              <div className="text-center">
                <Shield className="w-16 h-16 mx-auto mb-4 text-neon-purple" />
                <h2 className="text-xl font-semibold text-white mb-2">
                  {t('binding.verifyOwnership', 'Verify Ownership')}
                </h2>
                <p className="text-gray-400 text-sm">
                  {t('binding.verifyOwnershipDesc', 'Sign a message to prove wallet ownership')}
                </p>
              </div>

              <div className="bg-gray-700/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-sm text-gray-300">
                  <Info className="w-4 h-4" />
                  <span>{t('binding.walletAddress', 'Connected wallet')}:</span>
                </div>
                <p className="mt-1 text-neon-blue font-mono text-sm truncate">
                  {address}
                </p>
              </div>

              <button
                onClick={handleSignMessage}
                disabled={isLoading}
                className={clsx(
                  'w-full py-3 px-4 rounded-lg flex items-center justify-center gap-2',
                  'bg-neon-purple hover:bg-neon-purple/80 text-white font-medium',
                  'transition-all duration-200',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    {t('binding.signing', 'Signing...')}
                  </>
                ) : (
                  <>
                    <Shield className="w-5 h-5" />
                    {t('binding.signMessage', 'Sign Message')}
                  </>
                )}
              </button>

              <button
                onClick={() => {
                  disconnect()
                  setStep('connect')
                }}
                className="w-full py-2 text-gray-400 hover:text-white text-sm"
              >
                {t('binding.useDifferentWallet', 'Use a different wallet')}
              </button>
            </div>
          )}

          {/* Step 3: Select Stake Amount */}
          {step === 'stake' && (
            <div className="space-y-4">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-white mb-2">
                  {t('binding.selectStake', 'Select Stake Amount')}
                </h2>
                <p className="text-gray-400 text-sm">
                  {t('binding.selectStakeDesc', 'Choose how much VIBE to stake for this agent')}
                </p>
              </div>

              {/* Tier Selection */}
              <div className="space-y-2">
                {STAKE_TIERS.map((tier) => (
                  <button
                    key={tier.tier}
                    onClick={() => setSelectedAmount(tier.min)}
                    className={clsx(
                      'w-full p-4 rounded-lg border text-left transition-all',
                      selectedAmount >= tier.min && selectedAmount <= tier.max
                        ? 'bg-neon-blue/10 border-neon-blue'
                        : 'bg-gray-700/50 border-gray-600 hover:border-gray-500'
                    )}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-semibold text-white">{tier.label}</p>
                        <p className="text-sm text-gray-400">
                          {tier.min.toLocaleString()} - {tier.max === Infinity ? '∞' : tier.max.toLocaleString()} VIBE
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-300">{tier.agents} agents</p>
                        <p className="text-sm text-neon-green">{tier.discount} discount</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {/* Custom Amount */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  {t('binding.customAmount', 'Or enter custom amount')}
                </label>
                <input
                  type="number"
                  value={selectedAmount}
                  onChange={(e) => setSelectedAmount(Number(e.target.value))}
                  min={100}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white focus:border-neon-blue focus:outline-none"
                />
              </div>

              {/* Selected Tier Info */}
              <div className="bg-gray-700/50 rounded-lg p-4">
                <p className="text-sm text-gray-400 mb-1">{t('binding.selectedTier', 'Selected tier')}</p>
                <p className="text-lg font-semibold text-neon-blue">{getSelectedTier().label}</p>
                <p className="text-sm text-gray-300 mt-1">
                  {selectedAmount.toLocaleString()} VIBE • {getSelectedTier().agents} agents • {getSelectedTier().discount} discount
                </p>
              </div>

              <button
                onClick={handleCompleteBinding}
                disabled={isLoading || selectedAmount < 100}
                className={clsx(
                  'w-full py-3 px-4 rounded-lg flex items-center justify-center gap-2',
                  'bg-neon-green hover:bg-neon-green/80 text-gray-900 font-medium',
                  'transition-all duration-200',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    {t('binding.processing', 'Processing...')}
                  </>
                ) : (
                  <>
                    {t('binding.completeBinding', 'Complete Binding')} ({selectedAmount.toLocaleString()} VIBE)
                    <ChevronRight className="w-5 h-5" />
                  </>
                )}
              </button>
            </div>
          )}

          {/* Step 4: Complete */}
          {step === 'complete' && bindingResult && (
            <div className="space-y-4 text-center">
              <CheckCircle className="w-16 h-16 mx-auto text-neon-green" />
              <h2 className="text-xl font-semibold text-white">
                {t('binding.success', 'Binding Complete!')}
              </h2>
              <p className="text-gray-400">
                {bindingResult.message}
              </p>

              <div className="bg-gray-700/50 rounded-lg p-4 text-left space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">{t('binding.agentId', 'Agent ID')}</span>
                  <span className="text-white font-mono text-sm">{bindingResult.agent_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">{t('binding.stakeTier', 'Stake Tier')}</span>
                  <span className="text-neon-blue font-semibold">{bindingResult.stake_tier}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">{t('binding.stakedAmount', 'Staked Amount')}</span>
                  <span className="text-white">{selectedAmount.toLocaleString()} VIBE</span>
                </div>
              </div>

              <button
                onClick={() => navigate('/agents')}
                className="w-full py-3 px-4 rounded-lg bg-neon-blue hover:bg-neon-blue/80 text-gray-900 font-medium transition-all"
              >
                {t('binding.viewAgent', 'View Agent')}
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-gray-500 text-sm">
          {t('binding.footer', 'By binding, you agree to the Terms of Service and staking rules')}
        </p>
      </div>
    </div>
  )
}
