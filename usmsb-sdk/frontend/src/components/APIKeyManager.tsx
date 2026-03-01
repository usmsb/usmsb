import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Key,
  Plus,
  Trash2,
  RefreshCw,
  Copy,
  Check,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  Clock,
  Calendar,
} from 'lucide-react'
import {
  listAPIKeys,
  createAPIKey,
  revokeAPIKey,
  renewAPIKey,
} from '@/lib/api'
import type { APIKeyInfo } from '@/types'
import clsx from 'clsx'

interface APIKeyManagerProps {
  agentId: string
}

export function APIKeyManager({ agentId }: APIKeyManagerProps) {
  const { t } = useTranslation()
  const [keys, setKeys] = useState<APIKeyInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyExpiry, setNewKeyExpiry] = useState(365)
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null)
  const [actionKeyId, setActionKeyId] = useState<string | null>(null)

  useEffect(() => {
    loadKeys()
  }, [agentId])

  const loadKeys = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await listAPIKeys(agentId)
      setKeys(response.keys || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load API keys')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      setError('Key name is required')
      return
    }

    setActionKeyId('new')
    setError(null)
    try {
      const response = await createAPIKey(agentId, newKeyName, newKeyExpiry)
      setCreatedKey(response.api_key)
      setNewKeyName('')
      setNewKeyExpiry(365)
      await loadKeys()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create API key')
    } finally {
      setActionKeyId(null)
    }
  }

  const handleRevokeKey = async (keyId: string) => {
    if (!confirm(t('apiKey.confirmRevoke', 'Are you sure you want to revoke this key? This action cannot be undone.'))) {
      return
    }

    setActionKeyId(keyId)
    setError(null)
    try {
      await revokeAPIKey(agentId, keyId)
      await loadKeys()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke API key')
    } finally {
      setActionKeyId(null)
    }
  }

  const handleRenewKey = async (keyId: string) => {
    setActionKeyId(keyId)
    setError(null)
    try {
      await renewAPIKey(agentId, keyId, 365)
      await loadKeys()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to renew API key')
    } finally {
      setActionKeyId(null)
    }
  }

  const copyToClipboard = async (text: string, keyId?: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKeyId(keyId || 'created')
      setTimeout(() => setCopiedKeyId(null), 2000)
    } catch {
      setError('Failed to copy to clipboard')
    }
  }

  const formatDate = (timestamp?: number) => {
    if (!timestamp) return t('apiKey.never', 'Never')
    return new Date(timestamp * 1000).toLocaleDateString()
  }

  const isExpired = (expiresAt?: number) => {
    if (!expiresAt) return false
    return expiresAt * 1000 < Date.now()
  }

  const getExpiryStatus = (expiresAt?: number) => {
    if (!expiresAt) return { color: 'text-gray-400', label: t('apiKey.noExpiry', 'No expiry') }
    const expires = expiresAt * 1000
    const now = Date.now()
    const daysLeft = Math.floor((expires - now) / (1000 * 60 * 60 * 24))

    if (daysLeft < 0) {
      return { color: 'text-red-400', label: t('apiKey.expired', 'Expired') }
    } else if (daysLeft < 30) {
      return { color: 'text-yellow-400', label: t('apiKey.expiringSoon', `${daysLeft} days left`) }
    } else {
      return { color: 'text-green-400', label: t('apiKey.daysLeft', `${daysLeft} days left`) }
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-neon-blue" />
        <span className="ml-2 text-gray-400">{t('common.loading', 'Loading...')}</span>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Key className="w-5 h-5 text-neon-blue" />
          <h3 className="text-lg font-semibold text-white">{t('apiKey.title', 'API Keys')}</h3>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-neon-blue hover:bg-neon-blue/80 text-gray-900 rounded-lg font-medium transition-all"
        >
          <Plus className="w-4 h-4" />
          {t('apiKey.create', 'Create Key')}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Keys List */}
      {keys.length === 0 ? (
        <div className="text-center py-8 bg-gray-800/50 rounded-lg border border-gray-700">
          <Key className="w-12 h-12 mx-auto text-gray-600 mb-2" />
          <p className="text-gray-400">{t('apiKey.noKeys', 'No API keys yet')}</p>
          <p className="text-sm text-gray-500 mt-1">
            {t('apiKey.noKeysDesc', 'Create an API key to authenticate your agent')}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {keys.map((key) => {
            const expiryStatus = getExpiryStatus(key.expires_at)
            const expired = isExpired(key.expires_at)

            return (
              <div
                key={key.id}
                className={clsx(
                  'p-4 rounded-lg border transition-all',
                  expired
                    ? 'bg-red-900/10 border-red-500/30'
                    : 'bg-gray-800/50 border-gray-700 hover:border-gray-600'
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{key.name}</span>
                      {expired && (
                        <span className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 rounded">
                          {t('apiKey.revoked', 'Revoked')}
                        </span>
                      )}
                      {key.revoked && (
                        <span className="px-2 py-0.5 text-xs bg-gray-500/20 text-gray-400 rounded">
                          {t('apiKey.revoked', 'Revoked')}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-4 mt-2 text-sm">
                      <div className="flex items-center gap-1 text-gray-400">
                        <span className="font-mono text-xs bg-gray-700 px-2 py-0.5 rounded">
                          {key.prefix}...
                        </span>
                        <button
                          onClick={() => copyToClipboard(key.prefix, key.id)}
                          className="p-1 hover:bg-gray-700 rounded transition-colors"
                          title={t('common.copy', 'Copy')}
                        >
                          {copiedKeyId === key.id ? (
                            <Check className="w-3 h-3 text-green-400" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>

                      <div className={clsx('flex items-center gap-1', expiryStatus.color)}>
                        <Clock className="w-3 h-3" />
                        <span>{expiryStatus.label}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        <span>{t('apiKey.created', 'Created')}: {formatDate(key.created_at)}</span>
                      </div>
                      {key.last_used_at && (
                        <span>{t('apiKey.lastUsed', 'Last used')}: {formatDate(key.last_used_at)}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {!expired && !key.revoked && (
                      <>
                        <button
                          onClick={() => handleRenewKey(key.id)}
                          disabled={actionKeyId === key.id}
                          className={clsx(
                            'p-2 rounded-lg transition-all',
                            'hover:bg-gray-700 text-gray-400 hover:text-white',
                            'disabled:opacity-50 disabled:cursor-not-allowed'
                          )}
                          title={t('apiKey.renew', 'Renew for 1 year')}
                        >
                          {actionKeyId === key.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <RefreshCw className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => handleRevokeKey(key.id)}
                          disabled={actionKeyId === key.id}
                          className={clsx(
                            'p-2 rounded-lg transition-all',
                            'hover:bg-red-500/20 text-gray-400 hover:text-red-400',
                            'disabled:opacity-50 disabled:cursor-not-allowed'
                          )}
                          title={t('apiKey.revoke', 'Revoke key')}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Create Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-white mb-4">
              {t('apiKey.createTitle', 'Create New API Key')}
            </h3>

            {createdKey ? (
              <div className="space-y-4">
                <div className="p-4 bg-green-900/30 border border-green-500/50 rounded-lg">
                  <div className="flex items-center gap-2 text-green-400 mb-2">
                    <Check className="w-5 h-5" />
                    <span className="font-medium">{t('apiKey.createdSuccess', 'Key Created!')}</span>
                  </div>
                  <p className="text-sm text-gray-300 mb-3">
                    {t('apiKey.copyWarning', 'Copy your API key now. You won\'t be able to see it again.')}
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 p-2 bg-gray-900 rounded text-sm font-mono text-neon-green break-all">
                      {createdKey}
                    </code>
                    <button
                      onClick={() => copyToClipboard(createdKey)}
                      className={clsx(
                        'p-2 rounded-lg transition-all',
                        copiedKeyId === 'created'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-gray-700 text-gray-400 hover:text-white'
                      )}
                    >
                      {copiedKeyId === 'created' ? (
                        <Check className="w-5 h-5" />
                      ) : (
                        <Copy className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setShowCreateModal(false)
                    setCreatedKey(null)
                  }}
                  className="w-full py-2 bg-neon-blue hover:bg-neon-blue/80 text-gray-900 rounded-lg font-medium transition-all"
                >
                  {t('common.done', 'Done')}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    {t('apiKey.keyName', 'Key Name')}
                  </label>
                  <input
                    type="text"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder={t('apiKey.keyNamePlaceholder', 'e.g., Production Server')}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:border-neon-blue focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    {t('apiKey.expiry', 'Expires After')}
                  </label>
                  <select
                    value={newKeyExpiry}
                    onChange={(e) => setNewKeyExpiry(Number(e.target.value))}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white focus:border-neon-blue focus:outline-none"
                  >
                    <option value={30}>{t('apiKey.30days', '30 days')}</option>
                    <option value={90}>{t('apiKey.90days', '90 days')}</option>
                    <option value={180}>{t('apiKey.180days', '180 days')}</option>
                    <option value={365}>{t('apiKey.365days', '1 year')}</option>
                    <option value={0}>{t('apiKey.neverExpire', 'Never expire')}</option>
                  </select>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-all"
                  >
                    {t('common.cancel', 'Cancel')}
                  </button>
                  <button
                    onClick={handleCreateKey}
                    disabled={actionKeyId === 'new' || !newKeyName.trim()}
                    className={clsx(
                      'flex-1 py-2 bg-neon-blue hover:bg-neon-blue/80 text-gray-900 rounded-lg font-medium transition-all',
                      'disabled:opacity-50 disabled:cursor-not-allowed'
                    )}
                  >
                    {actionKeyId === 'new' ? (
                      <span className="flex items-center justify-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {t('common.creating', 'Creating...')}
                      </span>
                    ) : (
                      t('apiKey.createButton', 'Create Key')
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default APIKeyManager
