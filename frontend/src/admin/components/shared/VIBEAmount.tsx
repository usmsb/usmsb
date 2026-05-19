// VIBEAmount.tsx - VIBE 金额显示（自动格式化大数）
interface VIBEAmountProps {
  value: string | number
  suffix?: string
  decimals?: number
  className?: string
}

function formatVIBE(value: string | number, decimals = 2): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '0'
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(decimals) + 'B'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(decimals) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(decimals) + 'K'
  return n.toFixed(decimals)
}

export default function VIBEAmount({ value, suffix = 'VIBE', decimals = 2, className = '' }: VIBEAmountProps) {
  return (
    <span className={`font-mono ${className}`}>
      {formatVIBE(value, decimals)}
      {suffix && <span className="text-text-muted text-xs ml-1">{suffix}</span>}
    </span>
  )
}
