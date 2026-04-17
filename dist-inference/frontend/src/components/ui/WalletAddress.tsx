import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { truncateWallet } from '@/lib/utils'
import toast from 'react-hot-toast'

interface Props {
  address: string
  chars?: number
  className?: string
}

export default function WalletAddress({ address, chars = 4, className = '' }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(address)
    setCopied(true)
    toast.success('Copied!')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className={`flex items-center gap-1.5 font-mono text-xs text-neon-blue hover:text-neon-purple transition-colors ${className}`}
      title="Click to copy"
    >
      {truncateWallet(address, chars)}
      {copied ? <Check size={12} className="text-neon-green" /> : <Copy size={12} />}
    </button>
  )
}
