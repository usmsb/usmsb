/**
 * AgentTrendChart - Agent 增长趋势图
 * 纯 CSS 条形图，无需 chart library
 */
import { useState } from 'react'

interface Props {
  data: number[]
}

export default function AgentTrendChart({ data }: Props) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  if (!data || data.length === 0) {
    return (
      <div className="h-40 flex items-center justify-center text-text-muted text-sm">
        暂无趋势数据
      </div>
    )
  }

  const maxVal = Math.max(...data, 1)
  const labels = ['6天前', '5天前', '4天前', '3天前', '2天前', '昨天', '今天']

  return (
    <div className="h-40 flex flex-col">
      {/* Bar chart */}
      <div className="flex-1 flex items-end gap-1">
        {data.map((val, i) => {
          const heightPct = (val / maxVal) * 100
          return (
            <div
              key={i}
              className="flex-1 flex flex-col items-center group cursor-pointer"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              {/* Tooltip */}
              {hoveredIndex === i && (
                <div className="mb-1 px-2 py-1 bg-bg-elevated border border-border-primary rounded text-xs text-text-primary whitespace-nowrap z-10">
                  {val} agents
                </div>
              )}
              {/* Bar */}
              <div className="w-full bg-primary/30 hover:bg-primary/60 rounded-t transition-all relative"
                style={{ height: `${Math.max(heightPct, 4)}%` }}>
                <div className="absolute inset-0 bg-primary rounded-t opacity-80"
                  style={{ height: `${(val / maxVal) * 100}%` }} />
              </div>
            </div>
          )
        })}
      </div>
      {/* X-axis labels */}
      <div className="flex gap-1 mt-2">
        {labels.map((label, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="text-text-muted text-xs">{i === data.length - 1 ? '今' : labels[data.length - 1 - i]?.slice(0, 1) || ''}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
