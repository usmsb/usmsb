/**
 * Sparkline - 迷你趋势线
 */
interface SparklineProps {
  data: number[]
  color?: 'primary' | 'success' | 'danger' | 'warning' | 'info'
  height?: number
  className?: string
}

const colorMap = {
  primary: '#6366f1',
  success: '#10b981',
  danger: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6',
}

export function Sparkline({
  data,
  color = 'primary',
  height = 32,
  className = '',
}: SparklineProps) {
  if (!data || data.length < 2) return null

  const stroke = colorMap[color]
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const width = 120
  const padding = 2

  const points = data.map((v, i) => {
    const x = padding + (i / (data.length - 1)) * (width - padding * 2)
    const y = height - padding - ((v - min) / range) * (height - padding * 2)
    return `${x},${y}`
  }).join(' ')

  // 填充区域
  const fillPoints = [
    `${padding},${height - padding}`,
    ...points.split(' '),
    `${width - padding},${height - padding}`,
  ].join(' ')

  return (
    <svg
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={`spark-${color}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity={0.3} />
          <stop offset="100%" stopColor={stroke} stopOpacity={0} />
        </linearGradient>
      </defs>

      {/* 填充区域 */}
      <polygon
        points={fillPoints}
        fill={`url(#spark-${color})`}
      />

      {/* 线条 */}
      <polyline
        points={points}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {/* 最后一个点 */}
      <circle
        cx={points.split(' ').pop()?.split(',')[0]}
        cy={points.split(' ').pop()?.split(',')[1]}
        r={2}
        fill={stroke}
      />
    </svg>
  )
}
