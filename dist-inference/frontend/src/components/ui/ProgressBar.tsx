import { pct } from '@/lib/utils'

interface Props {
  used: number
  total: number
  showLabel?: boolean
  label?: string
  color?: 'blue' | 'green' | 'purple' | 'red'
  height?: 'sm' | 'md'
}

export default function ProgressBar({
  used,
  total,
  showLabel = true,
  label,
  color = 'blue',
  height = 'sm',
}: Props) {
  const percentage = pct(used, total)
  const colorClass = {
    blue: 'progress-neon',
    green: 'bg-neon-green shadow-neon-green',
    purple: 'bg-neon-purple',
    red: 'bg-neon-red',
  }[color]
  const h = height === 'sm' ? 'h-2' : 'h-3'

  return (
    <div className="w-full">
      <div className={`w-full bg-black/40 rounded-full ${h} overflow-hidden`}>
        <div
          className={`${colorClass} rounded-full transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-between mt-1 text-xs font-mono text-text-secondary">
          <span>{label || `${used} / ${total}`}</span>
          <span>{percentage}%</span>
        </div>
      )}
    </div>
  )
}
