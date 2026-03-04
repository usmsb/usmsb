/**
 * 区块链状态组件
 *
 * 显示区块链连接状态和代币信息
 */

import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, ExternalLink, Wallet, Coins, TrendingUp, AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { getBlockchainStatus, getTaxBreakdown } from '@/lib/api'
import { useAppStore } from '@/store'

export function BlockchainStatusCard() {
  const { t } = useTranslation()
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

  const { data: status, isLoading: statusLoading, error: statusError } = useQuery({
    queryKey: ['blockchain-status'],
    queryFn: getBlockchainStatus,
    refetchInterval: 30000, // 每30秒刷新
  })

  const { data: tax1000, isLoading: taxLoading } = useQuery({
    queryKey: ['tax-breakdown', 1000],
    queryFn: () => getTaxBreakdown(1000),
  })

  if (statusLoading) {
    return (
      <div className="card">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
        </div>
      </div>
    )
  }

  if (statusError) {
    return (
      <div className="card border-red-200 dark:border-red-800">
        <div className="flex items-center gap-3 text-red-500">
          <AlertCircle size={20} />
          <div>
            <p className="font-medium">{t('blockchain.connectionError', '区块链连接失败')}</p>
            <p className="text-sm opacity-75">{(statusError as Error).message}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={clsx(
      'card',
      isDark && 'hover:border-neon-green/50'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className={clsx(
          'text-lg font-semibold flex items-center gap-2',
          'text-light-text-primary',
          isDark && 'text-neon-green font-cyber'
        )}>
          <Link size={20} className={isDark ? 'text-neon-green' : 'text-green-500'} />
          {t('blockchain.title', '区块链状态')}
        </h3>
        {status?.connected && (
          <span className="flex items-center gap-1.5 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-xs font-medium rounded-full">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            {t('blockchain.connected', '已连接')}
          </span>
        )}
      </div>

      {/* Network Info */}
      <div className="space-y-3">
        {/* Network */}
        <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800">
          <span className={clsx(
            'text-sm',
            'text-light-text-muted',
            isDark && 'text-gray-400'
          )}>{t('blockchain.network', '网络')}</span>
          <span className={clsx(
            'text-sm font-medium',
            'text-light-text-primary',
            isDark && 'text-white font-mono'
          )}>{status?.network_name}</span>
        </div>

        {/* Chain ID */}
        <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800">
          <span className={clsx(
            'text-sm',
            'text-light-text-muted',
            isDark && 'text-gray-400'
          )}>{t('blockchain.chainId', '链ID')}</span>
          <span className={clsx(
            'text-sm font-mono',
            'text-light-text-primary',
            isDark && 'text-neon-blue'
          )}>{status?.chain_id}</span>
        </div>

        {/* Block Number */}
        <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800">
          <span className={clsx(
            'text-sm',
            'text-light-text-muted',
            isDark && 'text-gray-400'
          )}>{t('blockchain.blockNumber', '区块高度')}</span>
          <span className={clsx(
            'text-sm font-mono',
            'text-light-text-primary',
            isDark && 'text-neon-purple'
          )}>{status?.block_number?.toLocaleString()}</span>
        </div>

        {/* Token Info */}
        <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800">
          <span className={clsx(
            'text-sm flex items-center gap-1.5',
            'text-light-text-muted',
            isDark && 'text-gray-400'
          )}>
            <Coins size={14} />
            {t('blockchain.token', '代币')}
          </span>
          <span className={clsx(
            'text-sm font-medium',
            'text-light-text-primary',
            isDark && 'text-white'
          )}>{status?.token_name} ({status?.token_symbol})</span>
        </div>

        {/* Tax Info */}
        {!taxLoading && tax1000 && (
          <div className="flex items-center justify-between py-2">
            <span className={clsx(
              'text-sm flex items-center gap-1.5',
              'text-light-text-muted',
              isDark && 'text-gray-400'
            )}>
              <TrendingUp size={14} />
              {t('blockchain.taxRate', '交易税率')}
            </span>
            <span className={clsx(
              'text-sm font-medium',
              'text-light-text-primary',
              isDark && 'text-neon-pink'
            )}>{(tax1000.tax_rate * 100).toFixed(1)}%</span>
          </div>
        )}

        {/* Explorer Link */}
        <a
          href={`https://sepolia.basescan.org/address/${status?.token_address}`}
          target="_blank"
          rel="noopener noreferrer"
          className={clsx(
            'flex items-center justify-center gap-2 mt-4 py-2 px-4 rounded-lg text-sm font-medium transition-all',
            'bg-gray-100 hover:bg-gray-200 text-gray-700',
            isDark && 'bg-neon-blue/10 hover:bg-neon-blue/20 text-neon-blue border border-neon-blue/30'
          )}
        >
          <ExternalLink size={16} />
          {t('blockchain.viewOnExplorer', '在区块浏览器中查看')}
        </a>
      </div>
    </div>
  )
}

export function TokenBalanceChecker() {
  const { t } = useTranslation()
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

  const [address, setAddress] = useState('')
  const [searchAddress, setSearchAddress] = useState('')

  const { data: balance, isLoading, error, refetch } = useQuery({
    queryKey: ['token-balance', searchAddress],
    queryFn: () => getTokenBalance(searchAddress),
    enabled: !!searchAddress,
  })

  const handleSearch = () => {
    if (address) {
      setSearchAddress(address)
    }
  }

  return (
    <div className={clsx(
      'card',
      isDark && 'hover:border-neon-blue/50'
    )}>
      <h3 className={clsx(
        'text-lg font-semibold mb-4 flex items-center gap-2',
        'text-light-text-primary',
        isDark && 'text-neon-blue font-cyber'
      )}>
        <Wallet size={20} />
        {t('blockchain.balanceChecker', '代币余额查询')}
      </h3>

      {/* Search Input */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="0x..."
          className={clsx(
            'flex-1 px-3 py-2 rounded-lg text-sm',
            'border border-gray-200 dark:border-gray-700',
            'bg-white dark:bg-gray-800',
            'focus:outline-none focus:ring-2 focus:ring-primary-500',
            isDark && 'font-mono'
          )}
        />
        <button
          onClick={handleSearch}
          disabled={!address}
          className={clsx(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all',
            'bg-primary-500 text-white hover:bg-primary-600',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          {t('common.search', '查询')}
        </button>
      </div>

      {/* Results */}
      {isLoading && (
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-2"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
      )}

      {error && (
        <div className="text-red-500 text-sm">
          {(error as Error).message}
        </div>
      )}

      {balance && (
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className={clsx('text-sm', isDark && 'text-gray-400')}>
              {t('blockchain.address', '地址')}
            </span>
            <span className={clsx('text-sm font-mono', isDark && 'text-white')}>
              {balance.address.slice(0, 6)}...{balance.address.slice(-4)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className={clsx('text-sm', isDark && 'text-gray-400')}>
              {t('blockchain.balance', '余额')}
            </span>
            <span className={clsx(
              'text-lg font-bold',
              isDark && 'text-neon-green'
            )}>
              {balance.balance_vibe.toLocaleString()} {balance.symbol}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

// 需要导入useState
import { useState } from 'react'
import { getTokenBalance } from '@/lib/api'
