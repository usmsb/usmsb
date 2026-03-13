import { useState } from 'react'
import { useConnect, useAccount, useDisconnect } from 'wagmi'
import { Wallet, ChevronDown, CheckCircle } from 'lucide-react'
import { Button } from './ui/Button'

interface ConnectButtonProps {
  onConnected?: () => void
  className?: string
}

export function ConnectButton({ onConnected, className = '' }: ConnectButtonProps) {
  const { connectors, connect, isPending, error } = useConnect()
  const { address, isConnected } = useAccount()
  const { disconnect } = useDisconnect()
  const [showDropdown, setShowDropdown] = useState(false)

  // 过滤出可用的连接器 (去重)
  const availableConnectors = connectors.filter((connector, index, self) =>
    index === self.findIndex((c) => c.name === connector.name)
  )

  const handleConnect = async (connectorId: string) => {
    const connector = connectors.find((c) => c.id === connectorId)
    if (connector) {
      connect({ connector }, {
        onSuccess: () => {
          setShowDropdown(false)
          onConnected?.()
        }
      })
    }
  }

  if (isConnected && address) {
    return (
      <div className="relative">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          aria-expanded={showDropdown}
          aria-haspopup="true"
          aria-label={`Connected wallet: ${address.slice(0, 6)}...${address.slice(-4)}`}
          className={`flex items-center gap-2 px-4 py-2 bg-green-100 border border-green-300 rounded-lg hover:bg-green-200 transition-colors ${className}`}
        >
          <CheckCircle className="text-green-600" size={18} />
          <span className="font-mono text-sm text-green-800">
            {address.slice(0, 6)}...{address.slice(-4)}
          </span>
          <ChevronDown size={16} className="text-green-600" />
        </button>

        {showDropdown && (
          <div role="menu" aria-label="Wallet options" className="absolute top-full left-0 mt-2 w-48 bg-white border border-secondary-200 rounded-lg shadow-lg z-50">
            <button
              onClick={() => {
                disconnect()
                setShowDropdown(false)
              }}
              role="menuitem"
              className="w-full px-4 py-2 text-left text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              Disconnect
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="relative">
      <Button
        onClick={() => setShowDropdown(!showDropdown)}
        loading={isPending}
        className={className}
      >
        {isPending ? (
          <>
            Connecting...
          </>
        ) : (
          <>
            <Wallet size={20} />
            Connect Wallet
            <ChevronDown size={16} />
          </>
        )}
      </Button>

      {showDropdown && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowDropdown(false)}
          />

          {/* Dropdown */}
          <div role="menu" aria-label="Select wallet" className="absolute top-full left-0 mt-2 w-64 bg-white border border-secondary-200 rounded-lg shadow-lg z-50">
            <div className="p-2">
              <p className="px-3 py-2 text-xs font-medium text-secondary-500 uppercase">
                Select Wallet
              </p>
              {availableConnectors.map((connector) => (
                <button
                  key={connector.id}
                  onClick={() => handleConnect(connector.id)}
                  disabled={isPending}
                  role="menuitem"
                  className="w-full flex items-center gap-3 px-3 py-3 text-left hover:bg-secondary-50 rounded-lg transition-colors disabled:opacity-50"
                >
                  <div className="w-8 h-8 bg-secondary-100 rounded-lg flex items-center justify-center">
                    <Wallet size={18} className="text-secondary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-secondary-900">{connector.name}</p>
                    <p className="text-xs text-secondary-500">
                      {connector.type === 'injected' ? 'Browser Extension' : connector.type}
                    </p>
                  </div>
                </button>
              ))}

              {availableConnectors.length === 0 && (
                <div className="px-3 py-4 text-center text-secondary-500">
                  <p className="text-sm">No wallets detected</p>
                  <p className="text-xs mt-1">Please install MetaMask or another wallet extension</p>
                </div>
              )}
            </div>

            {error && (
              <div role="alert" className="p-3 border-t border-secondary-100">
                <p className="text-sm text-red-600">{error.message}</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

// 简化版本 - 单按钮直接连接
export function ConnectButtonSimple({ onConnected, className = '' }: ConnectButtonProps) {
  const { connectors, connect, isPending, error: _error } = useConnect()
  const { isConnected } = useAccount()

  // 优先使用 MetaMask 或 injected
  const preferredConnector = connectors.find((c) =>
    c.name.toLowerCase().includes('metamask')
  ) || connectors.find((c) => c.type === 'injected') || connectors[0]

  const handleConnect = () => {
    if (preferredConnector) {
      connect({ connector: preferredConnector }, {
        onSuccess: () => {
          onConnected?.()
        }
      })
    }
  }

  if (isConnected) {
    return null
  }

  return (
    <Button
      onClick={handleConnect}
      loading={isPending}
      disabled={!preferredConnector}
      className={className}
    >
      {isPending ? (
        <>
          Connecting...
        </>
      ) : (
        <>
          <Wallet size={20} />
          {preferredConnector ? `Connect with ${preferredConnector.name}` : 'Connect Wallet'}
        </>
      )}
    </Button>
  )
}
