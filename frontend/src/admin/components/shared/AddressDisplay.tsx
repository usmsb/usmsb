// AddressDisplay.tsx - 地址显示（截断 + 可复制 + 可跳转）
import { useState } from 'react'
import { ExternalLink, Copy, Check } from 'lucide-react'

interface AddressDisplayProps {
  address: string
  truncate?: boolean // 截断显示，默认 true
  explorer?: string  // 区块浏览器前缀，默认 sepolia.basescan.org
  className?: string
  textClassName?: string
}

export default function AddressDisplay({
  address,
  truncate = true,
  explorer = 'https://sepolia.basescan.org/address/',
  className = '',
  textClassName = 'text-text-secondary font-mono text-xs',
}: AddressDisplayProps) {
  const [copied, setCopied] = useState(false)

  const shortAddr = truncate
    ? `${address.slice(0, 6)}...${address.slice(-4)}`
    : address

  const handleCopy = async () => {
    await navigator.clipboard.writeText(address)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      <span className={textClassName}>{shortAddr}</span>
      <button
        onClick={handleCopy}
        className="text-text-muted hover:text-text-primary transition-colors"
        title="复制地址"
      >
        {copied ? (
          <Check className="w-3.5 h-3.5 text-success" />
        ) : (
          <Copy className="w-3.5 h-3.5" />
        )}
      </button>
      {explorer && (
        <a
          href={`${explorer}${address}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-text-muted hover:text-primary transition-colors"
          title="在区块浏览器中查看"
        >
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      )}
    </div>
  )
}
