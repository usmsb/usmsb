/**
 * ProgressBar - 进度条
 */
import clsx from 'clsx'

interface ProgressBarProps {
  percent: number
  warning?: number
  critical?: number
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function ProgressBar({
  percent,
  warning = 70,
  critical = 85,
  showLabel = false,
  size = 'md',
  className = '',
}: ProgressBarProps) {
  const color = percent >= critical ? 'bg-danger' :
                percent >= warning ? 'bg-warning' : 'bg-success'

  const heights = { sm: 'h-1.5', md: 'h-2.5', lg: 'h-4' }

  return (
    <div className={clsx('flex items-center gap-2', className)}>
      <div className={clsx('flex-1 bg-bg-tertiary rounded-full overflow-hidden', heights[size])}>
        <div
          className={clsx('h-full rounded-full transition-all duration-500', color)}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      {showLabel && (
        <span className={clsx(
          'text-xs font-mono w-10 text-right shrink-0',
          percent >= critical ? 'text-danger' :
          percent >= warning ? 'text-warning' : 'text-text-secondary',
        )}>
          {percent.toFixed(0)}%
        </span>
      )}
    </div>
  )
}
