/**
 * StatCard - 统计数字卡片
 * 核心组件，Dashboard/Command Center 共用
 */
import { TrendingUp, TrendingDown, type LucideIcon } from 'lucide-react'
import clsx from 'clsx'
import { Sparkline } from '../charts/Sparkline'

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
    if (value >= 1_000) return value.toLocaleString(decimals > 0 ? decimals : 0)
    return value.toFixed(decimals)
  }
  return String(value)
}

const colorClasses = {
  primary: { bg: 'bg-primary/10', text: 'text-primary', border: 'border-primary/20' },
  success: { bg: 'bg-success/10', text: 'text-success', border: 'border-success/20' },
  danger: { bg: 'bg-danger/10', text: 'text-danger', border: 'border-danger/20' },
  warning: { bg: 'bg-warning/10', text: 'text-warning', border: 'border-warning/20' },
  info: { bg: 'bg-info/10', text: 'text-info', border: 'border-info/20' },
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
        'bg-bg-secondary rounded-xl border border-border-primary p-5 animate-pulse',
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
        'bg-bg-secondary rounded-xl border border-border-primary p-5',
        'hover:border-border-active transition-all duration-200',
        onClick && 'cursor-pointer',
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-text-muted text-sm font-rajdhani truncate">{title}</p>
          <p className={clsx(
            'font-orbitron font-bold mt-1 text-text-primary',
            'text-2xl md:text-xl lg:text-2xl',
          )}>
            {prefix}
            {formatValue(value, decimals)}
            {suffix && <span className="text-lg text-text-muted ml-1">{suffix}</span>}
          </p>

          {change !== undefined && (
            <div className={clsx(
              'flex items-center gap-1 mt-2 text-sm',
              change >= 0 ? 'text-success' : 'text-danger',
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
            'p-3 rounded-lg shrink-0 ml-4',
            colorClass.bg,
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
  )
}
