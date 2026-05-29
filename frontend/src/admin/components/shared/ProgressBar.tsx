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
  const color = percent >= critical ? 'bg-neon-red' :
                percent >= warning ? 'bg-neon-yellow' : 'bg-neon-green'

  const heights = { sm: 'h-1.5', md: 'h-2.5', lg: 'h-4' }

  return (
    <div className={clsx('flex items-center gap-2', className)}>
      <div className={clsx('flex-1 bg-cyber-dark rounded-full overflow-hidden border border-neon-blue/20', heights[size])}>
        <div
          className={clsx('h-full rounded-full transition-all duration-500', color)}
          style={{
            width: `${Math.min(percent, 100)}%`,
            boxShadow: `0 0 10px ${percent >= critical ? '#ff0040' : percent >= warning ? '#ffff00' : '#00ff88'}`
          }}
        />
      </div>
      {showLabel && (
        <span className={clsx(
          'text-xs font-mono w-10 text-right shrink-0',
          percent >= critical ? 'text-neon-red' :
          percent >= warning ? 'text-neon-yellow' : 'text-neon-green',
        )}>
          {percent.toFixed(0)}%
        </span>
      )}
    </div>
  )
}
