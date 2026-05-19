// WebSocketStatus.tsx - WebSocket 连接状态指示器
import { useEffect, useState } from 'react'

type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

interface WebSocketStatusProps {
  url?: string
  className?: string
}

export default function WebSocketStatus({ className = '' }: WebSocketStatusProps) {
  const [status, setStatus] = useState<WsStatus>('disconnected')

  const config: Record<WsStatus, { label: string; color: string; dot: string }> = {
    connecting: { label: '连接中', color: 'text-warning', dot: 'bg-warning animate-pulse' },
    connected: { label: '实时已连接', color: 'text-success', dot: 'bg-success' },
    disconnected: { label: '实时已断开', color: 'text-text-muted', dot: 'bg-text-muted' },
    error: { label: '实时连接错误', color: 'text-danger', dot: 'bg-danger animate-pulse' },
  }

  const { label, color, dot } = config[status]

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`w-2 h-2 rounded-full ${dot}`} />
      <span className={`text-xs ${color}`}>{label}</span>
    </div>
  )
}
