import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Wallet, User, Bot, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import { useAccount, useConnect, useDisconnect, useSignMessage } from 'wagmi'
import { useAuthStore, UserRole, USER_ROLE_LABELS } from '@/stores/authStore'
import { getUserInfo, updateUserRole, signInWithEthereum } from '@/lib/api'

interface WalletBindingModalProps {
  isOpen: boolean
  onClose: () => void
  defaultRole?: UserRole
}

export default function WalletBindingModal({ isOpen, onClose, defaultRole = 'human' }: WalletBindingModalProps) {
  const { t } = useTranslation()
  const { address: wagmiAddress, isConnected: wagmiConnected, chain } = useAccount()
  const { connect, connectors, isPending: isConnecting } = useConnect()
  const { disconnect } = useDisconnect()
  const { signMessageAsync } = useSignMessage()

  const { 
    address, 
    isConnected, 
    bindingType, 
    setWallet, 
    setManualIdentifier, 
    setAgentBinding,
    setUserRole,
    setPermissions,
  } = useAuthStore()

  const [mode, setMode] = useState<'select' | 'wallet' | 'manual' | 'agent'>('select')
  const [manualInput, setManualInput] = useState('')
  const [agentId, setAgentId] = useState('')
  const [selectedRole, setSelectedRole] = useState<UserRole>(defaultRole)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  if (!isOpen) return null

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

  const handleManualBind = async () => {
    if (!manualInput.trim()) {
      setError('Please enter an identifier')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      // Register with backend
      const info = await getUserInfo(manualInput.trim())
      setManualIdentifier(manualInput.trim())
      setUserRole(info.role as UserRole)
      setPermissions(info.permissions, info.voting_power)
      setSuccess(true)
      setTimeout(() => onClose(), 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to bind identifier')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAgentBind = async () => {
    if (!agentId.trim()) {
      setError('Please enter Agent ID')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const info = await getUserInfo(agentId.trim())
      setAgentBinding(agentId.trim())
      setUserRole('ai_agent')
      setPermissions(info.permissions, info.voting_power)
      setSuccess(true)
      setTimeout(() => onClose(), 1000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to bind Agent')
    } finally {
      setIsLoading(false)
    }
  }

  const handleWagmiWalletBind = async () => {
    if (!wagmiAddress) {
      setError('Wallet not connected')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      // Step 1: Complete SIWE authentication
      const authResponse = await signInWithEthereum(
        wagmiAddress,
        async (message: string) => {
          return await signMessageAsync({ message })
        },
        chain?.id || 1
      )

      // Step 2: Save session to authStore
      const { setSession } = useAuthStore.getState()
      setSession(authResponse.sessionId, authResponse.accessToken)
      setWallet(wagmiAddress, chain?.id || 1)

      // Step 3: Get user info
      try {
        const info = await getUserInfo(wagmiAddress)
        setUserRole(info.role as UserRole)
        setPermissions(info.permissions, info.voting_power)
      } catch {
        // If getUserInfo fails, set default role
        setUserRole('human')
        setPermissions([], 0)
      }

      setSuccess(true)
      setTimeout(() => onClose(), 1000)
    } catch (err) {
      console.error('Wallet binding error:', err)
      setError(err instanceof Error ? err.message : 'Failed to bind wallet')
    } finally {
      setIsLoading(false)
    }
  }

  const handleRoleChange = async (newRole: UserRole) => {
    setSelectedRole(newRole)
    if (address) {
      try {
        const info = await updateUserRole(address, newRole)
        setUserRole(info.role as UserRole)
        setPermissions(info.permissions, info.voting_power)
      } catch (err) {
        console.error('Failed to update role:', err)
      }
    }
  }

  const generateRandomId = () => {
    const randomId = `user_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
    setManualInput(randomId)
  }

  const renderContent = () => {
    if (success) {
      return (
        <div className="flex flex-col items-center justify-center py-8">
          <CheckCircle className="w-16 h-16 text-green-500 mb-4" />
          <p className="text-lg font-medium text-gray-900 dark:text-white">
            {t('walletBinding.success', '绑定成功！')}
          </p>
          <p className="text-sm text-gray-500 mt-2">
            {t('walletBinding.successDesc', '你现在可以开始使用平台了')}
          </p>
        </div>
      )
    }

    if (mode === 'select') {
      return (
        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 text-center mb-6">
            {t('walletBinding.selectMode', '选择绑定方式')}
          </p>

          {/* Already connected */}
          {isConnected && address && (
            <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg mb-4">
              <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                <CheckCircle className="w-4 h-4" />
                <span className="text-sm font-medium">
                  {t('walletBinding.alreadyBound', '已绑定')}: {address.slice(0, 8)}...{address.slice(-6)}
                </span>
              </div>
              <p className="text-xs text-green-600 dark:text-green-500 mt-1">
                {t('walletBinding.bindingType', '绑定方式')}: {bindingType === 'wallet' ? t('walletBinding.realWallet', '真实钱包') : bindingType === 'manual' ? t('walletBinding.identifier', '标识符') : t('walletBinding.agent', 'AI Agent')}
              </p>
            </div>
          )}

          {/* Human options */}
          <div className="space-y-3">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('walletBinding.forHumans', '人类用户')}
            </p>
            
            <button
              onClick={() => setMode('wallet')}
              className="w-full flex items-center gap-3 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Wallet className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="text-left">
                <p className="font-medium text-gray-900 dark:text-white">
                  {t('walletBinding.connectWallet', '连接真实钱包')}
                </p>
                <p className="text-xs text-gray-500">
                  {t('walletBinding.connectWalletDesc', 'MetaMask、WalletConnect 等')}
                </p>
              </div>
            </button>

            <button
              onClick={() => setMode('manual')}
              className="w-full flex items-center gap-3 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                <User className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="text-left">
                <p className="font-medium text-gray-900 dark:text-white">
                  {t('walletBinding.useIdentifier', '使用临时标识符')}
                </p>
                <p className="text-xs text-gray-500">
                  {t('walletBinding.useIdentifierDesc', '无需钱包，快速体验')}
                </p>
              </div>
            </button>
          </div>

          {/* AI Agent options */}
          <div className="space-y-3 mt-6">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('walletBinding.forAgents', 'AI Agent')}
            </p>

            <button
              onClick={() => setMode('agent')}
              className="w-full flex items-center gap-3 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                <Bot className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div className="text-left">
                <p className="font-medium text-gray-900 dark:text-white">
                  {t('walletBinding.bindAgent', '绑定 AI Agent')}
                </p>
                <p className="text-xs text-gray-500">
                  {t('walletBinding.bindAgentDesc', '使用 Agent ID 进行绑定')}
                </p>
              </div>
            </button>
          </div>
        </div>
      )
    }

    if (mode === 'wallet') {
      return (
        <div className="space-y-4">
          <button onClick={() => setMode('select')} className="text-sm text-gray-500 hover:text-gray-700">
            ← {t('common.back', '返回')}
          </button>

          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {t('walletBinding.connectWallet', '连接真实钱包')}
          </h3>

          {wagmiConnected && wagmiAddress ? (
            <div className="space-y-4">
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <p className="text-sm text-green-700 dark:text-green-400">
                  {t('walletBinding.walletConnected', '钱包已连接')}: {wagmiAddress.slice(0, 8)}...{wagmiAddress.slice(-6)}
                </p>
              </div>
              <button
                onClick={handleWagmiWalletBind}
                disabled={isLoading}
                className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                {t('walletBinding.confirmBind', '确认绑定')}
              </button>
              <button
                onClick={() => disconnect()}
                className="w-full py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                {t('walletBinding.disconnect', '断开钱包')}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {connectors.map((connector, index) => (
                <button
                  key={connector.id}
                  onClick={() => handleConnectWallet(index)}
                  disabled={isConnecting}
                  className="w-full flex items-center gap-3 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
                >
                  <Wallet className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <span className="font-medium text-gray-900 dark:text-white">
                    {connector.name}
                  </span>
                  {isConnecting && <Loader2 className="w-4 h-4 animate-spin ml-auto" />}
                </button>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (mode === 'manual') {
      return (
        <div className="space-y-4">
          <button onClick={() => setMode('select')} className="text-sm text-gray-500 hover:text-gray-700">
            ← {t('common.back', '返回')}
          </button>

          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {t('walletBinding.useIdentifier', '使用临时标识符')}
          </h3>

          <p className="text-sm text-gray-600 dark:text-gray-400">
            {t('walletBinding.identifierDesc', '输入一个唯一标识符，或生成一个随机标识符')}
          </p>

          <div className="space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
                placeholder={t('walletBinding.identifierPlaceholder', '例如: alice_2024')}
                className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-800"
              />
              <button
                onClick={generateRandomId}
                className="px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
              >
                {t('walletBinding.generate', '随机生成')}
              </button>
            </div>

            <button
              onClick={handleManualBind}
              disabled={isLoading || !manualInput.trim()}
              className="w-full py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
              {t('walletBinding.confirmBind', '确认绑定')}
            </button>
          </div>
        </div>
      )
    }

    if (mode === 'agent') {
      return (
        <div className="space-y-4">
          <button onClick={() => setMode('select')} className="text-sm text-gray-500 hover:text-gray-700">
            ← {t('common.back', '返回')}
          </button>

          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {t('walletBinding.bindAgent', '绑定 AI Agent')}
          </h3>

          <p className="text-sm text-gray-600 dark:text-gray-400">
            {t('walletBinding.agentDesc', '输入您的 Agent ID 进行绑定')}
          </p>

          <div className="space-y-3">
            <input
              type="text"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              placeholder={t('walletBinding.agentIdPlaceholder', 'Agent ID')}
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-800"
            />

            <button
              onClick={handleAgentBind}
              disabled={isLoading || !agentId.trim()}
              className="w-full py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
              {t('walletBinding.confirmBind', '确认绑定')}
            </button>
          </div>
        </div>
      )
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-md mx-4 bg-white dark:bg-gray-900 rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {t('walletBinding.title', '身份绑定')}
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{error}</span>
            </div>
          )}
          {renderContent()}
        </div>

        {/* Role Selection (if connected) */}
        {isConnected && address && mode === 'select' && (
          <div className="p-6 border-t border-gray-200 dark:border-gray-700">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('walletBinding.selectRole', '选择角色')}
            </label>
            <select
              value={selectedRole}
              onChange={(e) => handleRoleChange(e.target.value as UserRole)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-800"
            >
              {Object.entries(USER_ROLE_LABELS).map(([role, label]) => (
                <option key={role} value={role}>{label}</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  )
}
