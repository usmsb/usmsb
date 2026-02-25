import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAgentWallet } from '@/hooks/useAgentWallet'
import AgentWalletCard from './AgentWalletCard'
import { Button } from './Button'
import { Input } from './Input'
import { EmptyState } from './EmptyState'

interface AgentWalletManagerProps {
  onSelectWallet?: (wallet: any) => void
}

export default function AgentWalletManager({ onSelectWallet }: AgentWalletManagerProps) {
  const { t } = useTranslation()
  const {
    agentWallets,
    isLoading,
    error,
    createWallet,
    selectWallet,
  } = useAgentWallet()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [agentId, setAgentId] = useState('')
  const [agentAddress, setAgentAddress] = useState('')

  const handleCreateWallet = async () => {
    if (agentId && agentAddress) {
      const wallet = await createWallet(agentId, agentAddress)
      if (wallet) {
        setAgentId('')
        setAgentAddress('')
        setShowCreateModal(false)
      }
    }
  }

  const handleSelectWallet = (wallet: any) => {
    selectWallet(wallet)
    onSelectWallet?.(wallet)
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">{t('agentWallet.title', 'Agent Wallets')}</h2>
        <Button onClick={() => setShowCreateModal(true)}>
          {t('agentWallet.createWallet', 'Create Agent Wallet')}
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-3 rounded">
          {error}
        </div>
      )}

      {agentWallets.length === 0 ? (
        <EmptyState
          title={t('agentWallet.noWallets', 'No agent wallets yet')}
          description={t('agentWallet.createFirst', 'Create your first agent wallet to get started')}
          action={{
            label: t('agentWallet.createWallet', 'Create Agent Wallet'),
            onClick: () => setShowCreateModal(true),
          }}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {agentWallets.map((wallet) => (
            <AgentWalletCard
              key={wallet.agentId}
              wallet={wallet}
              onSelect={handleSelectWallet}
            />
          ))}
        </div>
      )}

      {/* Create Wallet Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">
              {t('agentWallet.createWallet', 'Create Agent Wallet')}
            </h3>
            <label className="block text-sm text-gray-500 mb-1">{t('agentWallet.agentId', 'Agent ID')}</label>
            <Input
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              placeholder="agent-123"
            />
            <label className="block text-sm text-gray-500 mt-2 mb-1">{t('agentWallet.walletAddress', 'Wallet Address')}</label>
            <Input
              value={agentAddress}
              onChange={(e) => setAgentAddress(e.target.value)}
              placeholder="0x..."
            />
            <div className="flex gap-2 mt-4">
              <Button onClick={handleCreateWallet} disabled={isLoading || !agentId || !agentAddress}>
                {t('common.confirm', 'Confirm')}
              </Button>
              <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
                {t('common.cancel', 'Cancel')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
