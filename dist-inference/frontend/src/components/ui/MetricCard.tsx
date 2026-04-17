import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'
import { formatNumber } from '@/lib/utils'

interface Props {
  label: string
  value: string | number
  trend?: number // percent change, positive = up, negative = down
  subValue?: string
  icon?: React.ReactNode
  accent?: 'blue' | 'green' | 'purple' | 'red'
}

export default function MetricCard({ label, value, trend, subValue, icon, accent = 'blue' }: Props) {
  const accentClass = {
    blue: 'border-neon-blue/30 hover:border-neon-blue/60',
    green: 'border-neon-green/30 hover:border-neon-green/60',
    purple: 'border-neon-purple/30 hover:border-neon-purple/60',
    red: 'border-neon-red/30 hover:border-neon-red/60',
  }[accent]

  const textClass = {
    blue: 'neon-text-blue',
    green: 'neon-text-green',
    purple: 'neon-text-purple',
    red: 'text-neon-red',
  }[accent]

  const displayValue = typeof value === 'number' ? formatNumber(value) : value

  return (
    <div className={`cyber-card p-4 border ${accentClass} transition-all`}>
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-rajdhani text-text-secondary uppercase tracking-widest">
          {label}
        </span>
        {icon && <span className={textClass}>{icon}</span>}
      </div>
      <div className={`text-2xl font-orbitron font-bold ${textClass} mb-1`}>
        {displayValue}
      </div>
      {subValue && (
        <div className="text-xs font-mono text-text-secondary mb-2">{subValue}</div>
      )}
      {trend !== undefined && (
        <div className="flex items-center gap-1">
          {trend > 0 ? (
            <TrendingUp size={12} className="text-neon-green" />
          ) : trend < 0 ? (
            <TrendingDown size={12} className="text-neon-red" />
          ) : (
            <Minus size={12} className="text-text-secondary" />
          )}
          <span
            className={clsx(
              'text-xs font-mono',
              trend > 0 ? 'text-neon-green' : trend < 0 ? 'text-neon-red' : 'text-text-secondary'
            )}
          >
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        </div>
      )}
    </div>
  )
}
