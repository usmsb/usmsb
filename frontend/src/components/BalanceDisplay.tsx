import { useAccount, useChainId } from 'wagmi'
import { Loader2, Wallet, Copy, Check, ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { useToken } from '@/hooks/useToken'
import { useAppStore } from '@/store'
import clsx from 'clsx'

const BASESCAN_URL = 'https://sepolia.basescan.org'

export function BalanceDisplay() {
  const { address, isConnected } = useAccount()
  const chainId = useChainId()
  const { theme } = useAppStore()
  const isDark = theme === 'dark'
  const { formattedBalance, tokenSymbol, isLoading } = useToken()
  const [copied, setCopied] = useState(false)

  const truncatedAddress = address
    ? `${address.slice(0, 6)}...${address.slice(-4)}`
    : null

  const copyAddress = () => {
    if (address) {
      navigator.clipboard.writeText(address)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const getNetworkName = (id: number) => {
    switch (id) {
      case 84532:
        return 'Base Sepolia'
      case 8453:
        return 'Base'
      case 1:
        return 'Ethereum'
      case 11155111:
        return 'Sepolia'
      default:
        return `Chain ${id}`
    }
  }

  if (!isConnected) {
    return (
      <div className={clsx(
        'card',
        isDark && 'border-neon-blue/20'
      )}>
        <div className="flex items-center gap-3 mb-4">
          <div className={clsx(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            isDark ? 'bg-neon-blue/10' : 'bg-blue-50'
          )}>
            <Wallet size={20} className={isDark ? 'text-neon-blue' : 'text-blue-500'} />
          </div>
          <div>
            <h3 className={clsx(
              'font-semibold',
              isDark ? 'text-gray-100' : 'text-gray-900'
            )}>Wallet</h3>
            <p className={clsx(
              'text-sm',
              isDark ? 'text-gray-400' : 'text-gray-500'
            )}>Connect your wallet</p>
          </div>
        </div>
        <div className={clsx(
          'flex items-center justify-center py-6 rounded-lg',
          isDark ? 'bg-cyber-dark/50 border border-gray-700' : 'bg-gray-50 border border-gray-200'
        )}>
          <p className={clsx(
            'text-sm',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>Connect wallet to view balance</p>
        </div>
      </div>
    )
  }

  return (
    <div className={clsx(
      'card',
      isDark && 'hover:border-neon-blue/50 transition-colors'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={clsx(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            isDark ? 'bg-neon-blue/10' : 'bg-blue-50'
          )}>
            <Wallet size={20} className={isDark ? 'text-neon-blue' : 'text-blue-500'} />
          </div>
          <div>
            <h3 className={clsx(
              'font-semibold',
              isDark ? 'text-gray-100' : 'text-gray-900'
            )}>VIBE Balance</h3>
            <p className={clsx(
              'text-sm',
              isDark ? 'text-gray-400' : 'text-gray-500'
            )}>{getNetworkName(chainId)}</p>
          </div>
        </div>
        {/* Network badge */}
        <span className={clsx(
          'px-2 py-1 rounded-full text-xs font-medium',
          isDark
            ? 'bg-neon-blue/20 text-neon-blue border border-neon-blue/30'
            : 'bg-blue-50 text-blue-600 border border-blue-200'
        )}>
          {getNetworkName(chainId)}
        </span>
      </div>

      {/* Balance */}
      <div className="text-center py-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-2">
            <Loader2 className={clsx(
              'w-5 h-5 animate-spin',
              isDark ? 'text-neon-blue' : 'text-blue-500'
            )} />
          </div>
        ) : (
          <>
            <p className={clsx(
              'text-4xl font-bold',
              isDark ? 'text-white' : 'text-gray-900'
            )}>
              {parseFloat(formattedBalance).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
            <p className={clsx(
              'text-lg mt-1',
              isDark ? 'text-neon-blue' : 'text-blue-600'
            )}>
              {tokenSymbol || 'VIBE'}
            </p>
          </>
        )}
      </div>

      {/* Address */}
      <div className={clsx(
        'flex items-center justify-between rounded-lg px-4 py-3 mt-2',
        isDark ? 'bg-cyber-dark/50 border border-gray-700' : 'bg-gray-50 border border-gray-200'
      )}>
        <div className="flex items-center gap-2">
          <p className={clsx(
            'text-sm font-mono',
            isDark ? 'text-gray-300' : 'text-gray-700'
          )}>
            {truncatedAddress}
          </p>
          <button
            onClick={copyAddress}
            className={clsx(
              'p-1 rounded transition-colors',
              isDark ? 'hover:bg-neon-blue/10' : 'hover:bg-blue-50'
            )}
          >
            {copied ? (
              <Check size={14} className="text-green-500" />
            ) : (
              <Copy size={14} className={isDark ? 'text-gray-400' : 'text-gray-500'} />
            )}
          </button>
        </div>
        <a
          href={`${BASESCAN_URL}/address/${address}`}
          target="_blank"
          rel="noopener noreferrer"
          className={clsx(
            'p-1 rounded transition-colors',
            isDark ? 'hover:bg-neon-blue/10 text-gray-400 hover:text-neon-blue' : 'hover:bg-blue-50 text-gray-500 hover:text-blue-600'
          )}
        >
          <ExternalLink size={14} />
        </a>
      </div>
    </div>
  )
}

export default BalanceDisplay
