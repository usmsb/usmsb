/**
 * StatCard - 统计数字卡片
 * 核心组件，Dashboard/Command Center 共用
 */
import { TrendingUp, TrendingDown, type LucideIcon } from 'lucide-react'
import clsx from 'clsx'
import Sparkline from '../charts/Sparkline'

interface StatCardProps {
  title: string
  value: string | number
  change?: number
  changeLabel?: string
  icon?: LucideIcon
  color?: 'primary' | 'success' | 'danger' | 'warning' | 'info'
  loading?: boolean
  prefix?: string
  suffix?: string
  decimals?: number
  sparklineData?: number[]
  className?: string
  onClick?: () => void
}

function formatValue(value: string | number, decimals: number): string {
  if (typeof value === 'string') {
    // 处理大数，格式化为 K/M/B
    const num = parseFloat(value)
    if (isNaN(num)) return value
    if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(1) + 'B'
    if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
    if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K'
    return num.toFixed(decimals)
  }
  if (typeof value === 'number') {
    if (value >= 1_000_000_000) return (value / 1_000_000_000).toFixed(1) + 'B'
    if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + 'M'
    if (value >= 1_000) return value.toLocaleString(undefined, { minimumFractionDigits: decimals > 0 ? decimals : 0 })
    return value.toFixed(decimals)
  }
  return String(value)
}

const colorClasses = {
  primary: { bg: 'bg-neon-blue/10', text: 'text-neon-blue', border: 'border-neon-blue/20', glow: 'shadow-neon-blue/30' },
  success: { bg: 'bg-neon-green/10', text: 'text-neon-green', border: 'border-neon-green/20', glow: 'shadow-neon-green/30' },
  danger: { bg: 'bg-neon-red/10', text: 'text-neon-red', border: 'border-neon-red/20', glow: 'shadow-neon-red/30' },
  warning: { bg: 'bg-neon-yellow/10', text: 'text-neon-yellow', border: 'border-neon-yellow/20', glow: 'shadow-neon-yellow/30' },
  info: { bg: 'bg-neon-purple/10', text: 'text-neon-purple', border: 'border-neon-purple/20', glow: 'shadow-neon-purple/30' },
}

export default function StatCard({
  title,
  value,
  change,
  icon: Icon,
  color = 'primary',
  loading = false,
  prefix = '',
  suffix = '',
  decimals = 0,
  sparklineData,
  className = '',
  onClick,
}: StatCardProps) {
  if (loading) {
    return (
      <div className={clsx(
        'card animate-pulse',
        className,
      )}>
        <div className="h-4 w-24 bg-bg-tertiary rounded mb-3" />
        <div className="h-8 w-32 bg-bg-tertiary rounded mb-2" />
        <div className="h-3 w-16 bg-bg-tertiary rounded" />
      </div>
    )
  }

  const colorClass = colorClasses[color]

  return (
    <div
      onClick={onClick}
      className={clsx(
        'card group relative overflow-hidden',
        'hover:border-neon-blue/40 transition-all duration-300',
        onClick && 'cursor-pointer',
        className,
      )}
    >
      {/* Glow effect on hover */}
      <div className={clsx(
        'absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500',
        'bg-gradient-to-br from-neon-blue/5 via-transparent to-neon-purple/5',
      )} />

      <div className="relative z-10">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <p className={clsx(
              'text-sm font-cyber tracking-wider truncate',
              colorClass.text,
            )}>{title}</p>
            <p className={clsx(
              'font-orbitron font-bold mt-1',
              'text-2xl md:text-xl lg:text-2xl',
              colorClass.text,
            )}
              style={{
                textShadow: `0 0 10px currentColor`,
              }}
            >
              {prefix}
              {formatValue(value, decimals)}
              {suffix && <span className="text-lg text-gray-500 ml-1">{suffix}</span>}
            </p>

            {change !== undefined && (
              <div className={clsx(
                'flex items-center gap-1 mt-2 text-sm',
                change >= 0 ? 'text-neon-green' : 'text-neon-red',
              )}>
                {change >= 0 ? (
                  <TrendingUp className="w-4 h-4" />
                ) : (
                  <TrendingDown className="w-4 h-4" />
                )}
                <span className="font-mono">
                  {change >= 0 ? '+' : ''}{change.toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          {Icon && (
            <div className={clsx(
              'p-3 rounded-lg shrink-0 ml-4 border',
              colorClass.bg,
              colorClass.border,
            )}>
              <Icon className={clsx('w-6 h-6', colorClass.text)} />
            </div>
          )}
        </div>

        {/* 迷你趋势线 */}
        {sparklineData && sparklineData.length > 0 && (
          <div className="mt-3">
            <Sparkline data={sparklineData} color={color} height={32} />
          </div>
        )}
      </div>
    </div>
  )
}
