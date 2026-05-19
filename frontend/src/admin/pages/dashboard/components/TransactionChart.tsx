/**
 * TransactionChart - 交易额趋势图
 * 纯 CSS 面积图
 */
import { useState } from 'react'

interface Props {
  data: number[]
}

export default function TransactionChart({ data }: Props) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  if (!data || data.length === 0) {
    return (
      <div className="h-40 flex items-center justify-center text-text-muted text-sm">
        暂无交易数据
      </div>
    )
  }

  const maxVal = Math.max(...data, 1)
  const labels = ['6天前', '5天前', '4天前', '3天前', '2天前', '昨天', '今天']

  return (
    <div className="h-40 flex flex-col">
      {/* Area chart */}
      <div className="flex-1 flex items-end gap-1 relative">
        {data.map((val, i) => {
          const heightPct = (val / maxVal) * 100
          return (
            <div
              key={i}
              className="flex-1 flex flex-col items-center group cursor-pointer"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              {hoveredIndex === i && (
                <div className="mb-1 px-2 py-1 bg-bg-elevated border border-border-primary rounded text-xs text-text-primary whitespace-nowrap z-10">
                  ¥{val.toFixed(2)}
                </div>
              )}
              <div className="w-full relative" style={{ height: `${Math.max(heightPct, 4)}%` }}>
                <div className="absolute bottom-0 inset-x-0 bg-success/30 group-hover:bg-success/50 rounded-t transition-all" />
                <div className="absolute bottom-0 inset-x-0 bg-success/60 rounded-t" style={{ height: '40%' }} />
              </div>
            </div>
          )
        })}
      </div>
      {/* X-axis */}
      <div className="flex gap-1 mt-2">
        {labels.map((_, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="text-text-muted text-xs">{i === data.length - 1 ? '今' : ''}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
