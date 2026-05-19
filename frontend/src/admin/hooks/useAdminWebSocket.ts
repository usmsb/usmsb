// useAdminWebSocket.ts - WebSocket 实时推送 Hook
import { useEffect, useRef, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

interface WsMessage {
  type: string
  channel: string
  data: unknown
  timestamp: number
}

interface UseAdminWebSocketOptions {
  url?: string
  channels?: string[]
  onMessage?: (msg: WsMessage) => void
  reconnectInterval?: number // ms，默认 5000
  enabled?: boolean
}

export function useAdminWebSocket({
  url,
  channels = [],
  onMessage,
  reconnectInterval = 5000,
  enabled = true,
}: UseAdminWebSocketOptions = {}) {
  const [status, setStatus] = useState<WsStatus>('disconnected')
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const queryClient = useQueryClient()

  const invalidateQueries = useCallback((channel: string) => {
    // 根据 channel 失效对应的 query
    const queryKeys: Record<string, string[]> = {
      agents: ['admin', 'agents'],
      transactions: ['admin', 'transactions'],
      nodes: ['admin', 'nodes'],
      orders: ['admin', 'orders'],
      dashboard: ['admin', 'dashboard'],
      matching: ['admin', 'matching'],
      governance: ['admin', 'governance'],
    }
    const keys = queryKeys[channel] || [`admin`, channel]
    queryClient.invalidateQueries({ queryKey: keys })
  }, [queryClient])

  const connect = useCallback(() => {
    if (!url || !enabled) return

    setStatus('connecting')
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('connected')
        // 订阅 channel
        channels.forEach(ch => {
          ws.send(JSON.stringify({ type: 'subscribe', channel: ch }))
        })
      }

      ws.onmessage = (event) => {
        try {
          const msg: WsMessage = JSON.parse(event.data)
          setLastMessage(msg)
          onMessage?.(msg)
          invalidateQueries(msg.channel)
        } catch {
          // ignore parse errors
        }
      }

      ws.onerror = () => setStatus('error')

      ws.onclose = () => {
        setStatus('disconnected')
        wsRef.current = null
        // 自动重连
        if (enabled) {
          reconnectTimer.current = setTimeout(connect, reconnectInterval)
        }
      }
    } catch {
      setStatus('error')
    }
  }, [url, channels, enabled, onMessage, invalidateQueries, reconnectInterval])

  useEffect(() => {
    if (!enabled) return
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect, enabled])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return {
    status,
    lastMessage,
    send,
    reconnect: connect,
  }
}
