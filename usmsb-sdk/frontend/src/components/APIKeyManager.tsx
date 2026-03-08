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
    } catch (err: any) {
      const errorMessage = err?.message || err?.response?.data?.message || err?.response?.data?.error || 'Failed to load API keys'
      setError(typeof errorMessage === 'string' ? errorMessage : 'Failed to load API keys')
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
    } catch (err: any) {
      const errorMessage = err?.message || err?.response?.data?.message || err?.response?.data?.error || 'Failed to create API key'
      setError(typeof errorMessage === 'string' ? errorMessage : 'Failed to create API key')
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
    } catch (err: any) {
      const errorMessage = err?.message || err?.response?.data?.message || err?.response?.data?.error || 'Failed to revoke API key'
      setError(typeof errorMessage === 'string' ? errorMessage : 'Failed to revoke API key')
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
    } catch (err: any) {
      const errorMessage = err?.message || err?.response?.data?.message || err?.response?.data?.error || 'Failed to renew API key'
      setError(typeof errorMessage === 'string' ? errorMessage : 'Failed to renew API key')
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
    if (!expiresAt) return { color: 'text-secondary-500 dark:text-secondary-400', label: t('apiKey.noExpiry', 'No expiry') }
    const expires = expiresAt * 1000
    const now = Date.now()
    const daysLeft = Math.floor((expires - now) / (1000 * 60 * 60 * 24))

    if (daysLeft < 0) {
      return { color: 'text-red-600 dark:text-red-400', label: t('apiKey.expired', 'Expired') }
    } else if (daysLeft < 30) {
      return { color: 'text-yellow-600 dark:text-yellow-400', label: t('apiKey.expiringSoon', `${daysLeft} days left`) }
    } else {
      return { color: 'text-green-600 dark:text-green-400', label: t('apiKey.daysLeft', `${daysLeft} days left`) }
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        <span className="ml-2 text-secondary-500 dark:text-secondary-400">{t('common.loading', 'Loading...')}</span>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
            <Key className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <h3 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100">{t('apiKey.title', 'API Keys')}</h3>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          {t('apiKey.create', 'Create Key')}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-600 dark:text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">
            {typeof error === 'string' ? error : JSON.stringify(error)}
          </span>
        </div>
      )}

      {/* Keys List */}
      {keys.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 px-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-light-border dark:border-gray-700">
          <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700/50 flex items-center justify-center mb-4">
            <Key className="w-8 h-8 text-secondary-400" />
          </div>
          <h4 className="text-lg font-medium text-light-text-primary dark:text-secondary-100 mb-2">
            {t('apiKey.noKeys', 'No API Keys Yet')}
          </h4>
          <p className="text-sm text-secondary-500 dark:text-secondary-400 text-center max-w-sm mb-4">
            {t('apiKey.noKeysDesc', 'Create an API key to authenticate your agent with external services')}
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
          >
            <Plus className="w-4 h-4" />
            {t('apiKey.createFirst', 'Create Your First Key')}
          </button>
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
                    ? 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800'
                    : 'bg-white dark:bg-gray-800/50 border-light-border dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700'
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-light-text-primary dark:text-secondary-100">{key.name}</span>
                      {expired && (
                        <span className="px-2 py-0.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded">
                          {t('apiKey.revoked', 'Revoked')}
                        </span>
                      )}
                      {key.revoked && (
                        <span className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-800 text-secondary-500 dark:text-secondary-400 rounded">
                          {t('apiKey.revoked', 'Revoked')}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-4 mt-2 text-sm">
                      <div className="flex items-center gap-1 text-secondary-500 dark:text-secondary-400">
                        <span className="font-mono text-xs bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                          {key.prefix}...
                        </span>
                        <button
                          onClick={() => copyToClipboard(key.prefix, key.id)}
                          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                          title={t('common.copy', 'Copy')}
                        >
                          {copiedKeyId === key.id ? (
                            <Check className="w-3 h-3 text-green-500" />
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

                    <div className="flex items-center gap-4 mt-2 text-xs text-secondary-400 dark:text-secondary-500">
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
                            'hover:bg-gray-100 dark:hover:bg-gray-700 text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-200',
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
                            'hover:bg-red-50 dark:hover:bg-red-900/20 text-secondary-400 hover:text-red-600 dark:hover:text-red-400',
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
          <div className="w-full max-w-md bg-white dark:bg-gray-800 rounded-xl border border-light-border dark:border-gray-700 p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-4">
              {t('apiKey.createTitle', 'Create New API Key')}
            </h3>

            {createdKey ? (
              <div className="space-y-4">
                <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <div className="flex items-center gap-2 text-green-600 dark:text-green-400 mb-2">
                    <Check className="w-5 h-5" />
                    <span className="font-medium">{t('apiKey.createdSuccess', 'Key Created!')}</span>
                  </div>
                  <p className="text-sm text-secondary-600 dark:text-secondary-300 mb-3">
                    {t('apiKey.copyWarning', 'Copy your API key now. You won\'t be able to see it again.')}
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 p-2 bg-gray-100 dark:bg-gray-900 rounded text-sm font-mono text-green-600 dark:text-green-400 break-all">
                      {createdKey}
                    </code>
                    <button
                      onClick={() => copyToClipboard(createdKey)}
                      className={clsx(
                        'p-2 rounded-lg transition-all',
                        copiedKeyId === 'created'
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
                          : 'bg-gray-100 dark:bg-gray-700 text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-200'
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
                  className="w-full btn btn-primary"
                >
                  {t('common.done', 'Done')}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-secondary-600 dark:text-secondary-400 mb-1">
                    {t('apiKey.keyName', 'Key Name')}
                  </label>
                  <input
                    type="text"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder={t('apiKey.keyNamePlaceholder', 'e.g., Production Server')}
                    className="w-full bg-white dark:bg-gray-700 border border-light-border dark:border-gray-600 rounded-lg px-4 py-2 text-light-text-primary dark:text-secondary-100 placeholder-secondary-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm text-secondary-600 dark:text-secondary-400 mb-1">
                    {t('apiKey.expiry', 'Expires After')}
                  </label>
                  <select
                    value={newKeyExpiry}
                    onChange={(e) => setNewKeyExpiry(Number(e.target.value))}
                    className="w-full bg-white dark:bg-gray-700 border border-light-border dark:border-gray-600 rounded-lg px-4 py-2 text-light-text-primary dark:text-secondary-100 focus:border-blue-500 focus:outline-none"
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
                    className="flex-1 btn btn-secondary"
                  >
                    {t('common.cancel', 'Cancel')}
                  </button>
                  <button
                    onClick={handleCreateKey}
                    disabled={actionKeyId === 'new' || !newKeyName.trim()}
                    className="flex-1 btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
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
