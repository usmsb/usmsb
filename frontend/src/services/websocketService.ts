/**
 * WebSocket Service for AI Civilization Platform
 *
 * Provides real-time communication with the backend:
 * - Environment updates
 * - Transaction notifications
 * - Matching opportunities
 * - Chat messages
 */

import { useEffect, useState, useCallback } from 'react'
import { useAuthStore } from '../stores/authStore'

// Message type definitions
export type MessageType =
  | 'ping'
  | 'pong'
  | 'auth'
  | 'auth_success'
  | 'auth_failed'
  | 'environment_update'
  | 'market_change'
  | 'new_opportunity'
  | 'match_update'
  | 'transaction_update'
  | 'transaction_complete'
  | 'notification'
  | 'price_alert'
  | 'chat_message'
  | 'agent_status'
  | '*'

// Generic data payload type
export type MessageData = Record<string, unknown>

// WebSocket message structure
export interface WebSocketMessage<T = MessageData> {
  type: MessageType
  data?: T
  timestamp: number
  [key: string]: unknown
}

// Type-specific data interfaces
export interface EnvironmentUpdateData {
  environment_id: string
  state: Record<string, unknown>
  changes: Array<{ key: string; old_value: unknown; new_value: unknown }>
}

export interface TransactionUpdateData {
  transaction_id: string
  status: 'pending' | 'confirmed' | 'failed'
  details: Record<string, unknown>
}

export interface NotificationData {
  id: string
  title: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
  timestamp: number
  read: boolean
}

export interface AgentStatusData {
  agent_id: string
  status: 'online' | 'offline' | 'busy' | 'inactive'
  last_heartbeat: number
}

export interface ChatMessageData {
  message_id: string
  sender_id: string
  receiver_id: string
  content: string
  timestamp: number
}

export interface OpportunityData {
  opportunity_id: string
  type: 'supply' | 'demand'
  details: Record<string, unknown>
  match_score: number
}

// Type handler function
export type MessageHandler<T = MessageData> = (message: WebSocketMessage<T>) => void

// Send message types
export interface PingMessage {
  type: 'ping'
  timestamp: number
}

export interface AuthMessage {
  type: 'auth'
  agentId: string
  sessionId: string
}

export type SendableMessage = PingMessage | AuthMessage | Record<string, unknown>

class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private pingInterval: ReturnType<typeof setInterval> | null = null
  private handlers: Map<MessageType, Set<MessageHandler>> = new Map()
  private isConnected = false

  connect(url?: string): void {
    const wsUrl = url || this.getDefaultUrl()

    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      this.ws = new WebSocket(wsUrl)
      this.setupEventHandlers()
    } catch (error) {
      console.error('WebSocket connection error:', error)
      this.scheduleReconnect()
    }
  }

  private getDefaultUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/ws`
  }

  private setupEventHandlers(): void {
    if (!this.ws) return

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.isConnected = true
      this.reconnectAttempts = 0
      this.startPingInterval()
      this.authenticate()
    }

    this.ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.reason)
      this.isConnected = false
      this.stopPingInterval()
      this.scheduleReconnect()
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage
        this.handleMessage(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    // Handle pong
    if (message.type === 'pong') {
      return
    }

    // Dispatch to handlers
    const handlers = this.handlers.get(message.type)
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(message)
        } catch (error) {
          console.error('Handler error:', error)
        }
      })
    }

    // Also dispatch to wildcard handlers
    const wildcardHandlers = this.handlers.get('*')
    if (wildcardHandlers) {
      wildcardHandlers.forEach((handler) => {
        try {
          handler(message)
        } catch (error) {
          console.error('Wildcard handler error:', error)
        }
      })
    }
  }

  private authenticate(): void {
    const authStore = useAuthStore.getState()
    const { agentId, sessionId } = authStore

    if (agentId && sessionId) {
      this.send({
        type: 'auth',
        agentId,
        sessionId,
      })
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      this.connect()
    }, delay)
  }

  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping', timestamp: Date.now() })
    }, 25000)
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  send(message: SendableMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    }
  }

  subscribe<T = MessageData>(type: MessageType, handler: MessageHandler<T>): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler as MessageHandler)

    // Return unsubscribe function
    return () => {
      this.handlers.get(type)?.delete(handler as MessageHandler)
    }
  }

  disconnect(): void {
    this.stopPingInterval()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.isConnected = false
  }

  getConnectionStatus(): boolean {
    return this.isConnected
  }
}

// Singleton instance
export const wsService = new WebSocketService()

// React hook for WebSocket
export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  useEffect(() => {
    wsService.connect()

    const unsubscribe = wsService.subscribe('*', (message) => {
      setLastMessage(message)
    })

    // Check connection status periodically
    const interval = setInterval(() => {
      setIsConnected(wsService.getConnectionStatus())
    }, 1000)

    return () => {
      unsubscribe()
      clearInterval(interval)
    }
  }, [])

  const subscribe = useCallback(<T = MessageData>(type: MessageType | '*', handler: MessageHandler<T>) => {
    return wsService.subscribe(type, handler)
  }, [])

  const send = useCallback((message: SendableMessage) => {
    wsService.send(message)
  }, [])

  return {
    isConnected,
    lastMessage,
    subscribe,
    send,
  }
}

// Hook for environment updates
export function useEnvironmentUpdates(onUpdate: (state: EnvironmentUpdateData) => void): void {
  useEffect(() => {
    return wsService.subscribe<EnvironmentUpdateData>('environment_update', (message) => {
      if (message.data) {
        onUpdate(message.data)
      }
    })
  }, [onUpdate])
}

// Hook for transaction updates
export function useTransactionUpdates(onUpdate: (data: TransactionUpdateData) => void): void {
  useEffect(() => {
    return wsService.subscribe<TransactionUpdateData>('transaction_update', (message) => {
      if (message.data) {
        onUpdate(message.data)
      }
    })
  }, [onUpdate])
}

// Hook for notifications
export function useNotifications(onNotification: (notification: NotificationData) => void): void {
  useEffect(() => {
    return wsService.subscribe<NotificationData>('notification', (message) => {
      if (message.data) {
        onNotification({
          id: (message.data.id as string) || '',
          title: (message.data.title as string) || '',
          message: (message.data.message as string) || '',
          type: (message.data.type as NotificationData['type']) || 'info',
          timestamp: message.timestamp,
          read: (message.data.read as boolean) || false,
        })
      }
    })
  }, [onNotification])
}

export default wsService
