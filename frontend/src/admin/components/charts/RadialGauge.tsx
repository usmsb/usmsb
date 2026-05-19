// RadialGauge.tsx - 环形进度仪表
interface RadialGaugeProps {
  value: number      // 0-100
  size?: number
  strokeWidth?: number
  color?: string
  label?: string
  sublabel?: string
  className?: string
}

export default function RadialGauge({
  value,
  size = 120,
  strokeWidth = 10,
  color = '#8b5cf6',
  label,
  sublabel,
  className = '',
}: RadialGaugeProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const progress = Math.min(Math.max(value, 0), 100)
  const offset = circumference - (progress / 100) * circumference

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          {/* 背景圆环 */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-bg-tertiary"
          />
          {/* 进度圆环 */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-700"
          />
        </svg>
        {/* 中心文字 */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold font-mono text-text-primary">
            {progress.toFixed(0)}%
          </span>
          {label && <span className="text-xs text-text-muted mt-0.5">{label}</span>}
        </div>
      </div>
      {sublabel && (
        <span className="text-xs text-text-muted mt-2">{sublabel}</span>
      )}
    </div>
  )
}
