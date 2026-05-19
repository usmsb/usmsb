// TimeAgo.tsx - 相对时间显示（自动刷新）
import { useState, useEffect } from 'react'

interface TimeAgoProps {
  timestamp: number | string | Date
  refresh?: boolean // 是否自动刷新，默认 true
  className?: string
}

function getTimeAgo(date: Date): string {
  const now = Date.now()
  const diff = now - date.getTime()
  const secs = Math.floor(diff / 1000)
  if (secs < 60) return `${secs}秒前`
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}天前`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months}月前`
  return `${Math.floor(months / 12)}年前`
}

export default function TimeAgo({ timestamp, refresh = true, className = '' }: TimeAgoProps) {
  const [label, setLabel] = useState(() => {
    const d = timestamp instanceof Date ? timestamp : new Date(timestamp)
    return getTimeAgo(d)
  })

  useEffect(() => {
    if (!refresh) return
    const interval = setInterval(() => {
      const d = timestamp instanceof Date ? timestamp : new Date(timestamp)
      setLabel(getTimeAgo(d))
    }, 30000)
    return () => clearInterval(interval)
  }, [timestamp, refresh])

  return <span className={className}>{label}</span>
}
