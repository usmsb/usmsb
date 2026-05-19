// WalletInputModal.tsx - 钱包地址输入弹窗
import { useState } from 'react'
import { Wallet, X, AlertCircle } from 'lucide-react'

interface WalletInputModalProps {
  isOpen: boolean
  title?: string
  description?: string
  placeholder?: string
  onSubmit: (address: string) => void
  onCancel: () => void
  isLoading?: boolean
}

function isValidEthAddress(addr: string): boolean {
  return /^0x[a-fA-F0-9]{40}$/.test(addr)
}

export default function WalletInputModal({
  isOpen,
  title = '输入钱包地址',
  description,
  placeholder = '0x...',
  onSubmit,
  onCancel,
  isLoading,
}: WalletInputModalProps) {
  const [address, setAddress] = useState('')
  const [error, setError] = useState('')

  if (!isOpen) return null

  const handleSubmit = () => {
    const trimmed = address.trim()
    if (!isValidEthAddress(trimmed)) {
      setError('请输入有效的 Ethereum 地址（0x 开头，40位十六进制）')
      return
    }
    setError('')
    onSubmit(trimmed)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
      />
      <div className="relative bg-bg-secondary border border-border-primary rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Wallet className="w-5 h-5 text-primary" />
            </div>
            <h2 className="text-lg font-bold text-text-primary font-rajdhani">{title}</h2>
          </div>
          <button onClick={onCancel} className="text-text-muted hover:text-text-primary transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-3">
          {description && (
            <p className="text-text-secondary text-sm">{description}</p>
          )}
          <input
            type="text"
            value={address}
            onChange={e => { setAddress(e.target.value); setError('') }}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            placeholder={placeholder}
            className="w-full bg-bg-tertiary text-text-primary border border-border-primary rounded-lg px-4 py-3 text-sm font-mono outline-none placeholder-text-muted focus:border-primary transition-colors"
            autoFocus
          />
          {error && (
            <div className="flex items-center gap-2 text-danger text-xs">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border-primary bg-bg-tertiary/50">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary text-sm transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || !address.trim()}
            className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isLoading ? '查询中...' : '查询'}
          </button>
        </div>
      </div>
    </div>
  )
}
