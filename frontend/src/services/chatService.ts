/**
 * Chat Service - OpenHarness StreamEvent Pattern
 *
 * Implements the new communication protocol:
 * - WebSocket: Command channel (user_message, confirm_plan, cancel_task)
 * - SSE: Progress channel (text_delta, tool_call, tool_result, progress)
 */

// ==================== Types ====================

export type ChatEventType =
  | 'text_delta'
  | 'text_complete'
  | 'tool_call'
  | 'tool_result'
  | 'progress'
  | 'plan_generating'
  | 'plan_ready'
  | 'plan_confirmed'
  | 'plan_rejected'
  | 'task_start'
  | 'task_complete'
  | 'task_failed'
  | 'stream_end'
  | 'error'
  | 'heartbeat'

export interface ChatStreamEvent {
  event: ChatEventType
  data: any
  metadata?: Record<string, any>
  done?: boolean
}

export interface ToolCallData {
  tool_name: string
  tool_input: Record<string, any>
  call_id?: string
}

export interface ToolResultData {
  tool_name: string
  output: string
  is_error: boolean
  execution_time_ms?: number
  call_id?: string
}

export interface ProgressData {
  step_index: number
  total_steps: number
  percentage: number
  message?: string
}

export interface PlanReadyData {
  plan_id: string
  steps: Array<{
    index: number
    name: string
    description: string
    status: string
  }>
  estimated_time_seconds: number
  confirmation_phrase: string
}

// ==================== Chat Event Handler ====================

export type ChatEventHandler = (event: ChatStreamEvent) => void

// ==================== WebSocket Client ====================

class ChatWebSocketClient {
  private ws: WebSocket | null = null
  private _sessionId: string = ''
  private walletAddress: string = ''
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private handlers: Set<ChatEventHandler> = new Set()
  private isIntentionalClose = false
  private connectionResolve: ((sessionId: string) => void) | null = null
  private sessionIdPromise: Promise<string>

  constructor(walletAddress: string) {
    this.walletAddress = walletAddress
    // Derive session ID the same way the backend does: f"ws_{wallet_address}_{timestamp}"
    // Use minute-level timestamp so within the same minute the IDs match
    const ts = Math.floor(Date.now() / 60000) * 60000
    this._sessionId = `ws_${walletAddress}_${ts}`
    // Create a promise that resolves when MESSAGE_RECEIVED is received
    this.sessionIdPromise = new Promise((resolve) => {
      this.connectionResolve = resolve
    })
  }

  connect(): Promise<string> {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      // Use the pre-generated session ID in the URL path
      const wsUrl = `${protocol}//${host}/api/meta-agent/ws/chat/${this.walletAddress}`

      console.log('[ChatWS] Connecting to', wsUrl, 'with sessionId', this._sessionId)

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('[ChatWS] Connected')
        this.reconnectAttempts = 0
        this.isIntentionalClose = false
        // Resolve with the pre-generated session ID immediately
        resolve(this._sessionId)
      }

      this.ws.onclose = (event) => {
        console.log('[ChatWS] Disconnected:', event.reason)
        if (!this.isIntentionalClose) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('[ChatWS] Error:', error)
        reject(error)
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('[ChatWS] Failed to parse message:', error)
        }
      }
    })
  }

  private handleMessage(message: { type: string; data: any }) {
    // Transform WebSocket message to ChatStreamEvent format
    const eventType = this.mapMessageType(message.type)
    const event: ChatStreamEvent = {
      event: eventType,
      data: message.data,
    }

    // Extract session_id if present and resolve connection promise
    if (message.data?.session_id) {
      this._sessionId = message.data.session_id
      if (this.connectionResolve) {
        this.connectionResolve(this._sessionId)
        this.connectionResolve = null
      }
    }

    this.handlers.forEach(handler => {
      try {
        handler(event)
      } catch (error) {
        console.error('[ChatWS] Handler error:', error)
      }
    })
  }

  private mapMessageType(type: string): ChatEventType {
    const typeMap: Record<string, ChatEventType> = {
      message_received: 'text_complete',
      stream_start: 'task_start',
      error: 'error',
    }
    return typeMap[type] || (type as ChatEventType)
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[ChatWS] Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`[ChatWS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      this.connect().catch(console.error)
    }, delay)
  }

  send(type: string, payload: Record<string, any>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type,
        payload,
        session_id: this._sessionId,
        wallet_address: this.walletAddress,
        timestamp: Date.now() / 1000,
      }))
    }
  }

  sendMessage(message: string) {
    this.send('user_message', { message })
  }

  confirmPlan(planId: string) {
    this.send('confirm_plan', { plan_id: planId })
  }

  cancelTask(taskId: string) {
    this.send('cancel_task', { task_id: taskId })
  }

  subscribe(handler: ChatEventHandler): () => void {
    this.handlers.add(handler)
    return () => {
      this.handlers.delete(handler)
    }
  }

  disconnect() {
    this.isIntentionalClose = true
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  getSessionId(): string {
    return this._sessionId
  }
}

// ==================== SSE Client ====================

class ChatSSEClient {
  private eventSource: EventSource | null = null
  private walletAddress: string = ''
  private handlers: Set<ChatEventHandler> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  constructor(walletAddress: string) {
    this.walletAddress = walletAddress
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const host = window.location.host
      // Use wallet_address like backend does to derive session_id
      const sseUrl = `${window.location.protocol}//${host}/api/meta-agent/sse/chat/${this.walletAddress}`

      console.log('[ChatSSE] Connecting to', sseUrl)

      this.eventSource = new EventSource(sseUrl)

      this.eventSource.onopen = () => {
        console.log('[ChatSSE] Connected')
        this.reconnectAttempts = 0
        resolve()
      }

      this.eventSource.onerror = (error) => {
        console.error('[ChatSSE] Error:', error)
        if (this.eventSource) {
          this.eventSource.close()
        }
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect()
        } else {
          reject(new Error('Max reconnect attempts reached'))
        }
      }

      // Listen for all event types
      const eventTypes: ChatEventType[] = [
        'text_delta', 'text_complete', 'tool_call', 'tool_result',
        'progress', 'plan_generating', 'plan_ready', 'plan_confirmed',
        'plan_rejected', 'task_start', 'task_complete', 'task_failed',
        'stream_end', 'error', 'heartbeat'
      ]

      eventTypes.forEach(type => {
        this.eventSource?.addEventListener(type, (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data)
            const event: ChatStreamEvent = {
              event: type,
              data: data.data,
              metadata: data.metadata,
              done: data.done,
            }
            this.emit(event)
          } catch (error) {
            console.error('[ChatSSE] Failed to parse event:', error)
          }
        })
      })
    })
  }

  private scheduleReconnect() {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`[ChatSSE] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      this.connect().catch(console.error)
    }, delay)
  }

  private emit(event: ChatStreamEvent) {
    this.handlers.forEach(handler => {
      try {
        handler(event)
      } catch (error) {
        console.error('[ChatSSE] Handler error:', error)
      }
    })
  }

  subscribe(handler: ChatEventHandler): () => void {
    this.handlers.add(handler)
    return () => {
      this.handlers.delete(handler)
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
  }
}

// ==================== Chat Service (Facade) ====================

export class ChatService {
  private wsClient: ChatWebSocketClient | null = null
  private sseClient: ChatSSEClient | null = null
  private walletAddress: string = ''

  async connect(walletAddress: string): Promise<string> {
    this.walletAddress = walletAddress
    this.wsClient = new ChatWebSocketClient(walletAddress)
    const sessionId = await this.wsClient.connect()
    return sessionId
  }

  async startSSE(walletAddress: string): Promise<void> {
    this.sseClient = new ChatSSEClient(walletAddress)
    await this.sseClient.connect()
  }

  sendMessage(message: string) {
    this.wsClient?.sendMessage(message)
  }

  confirmPlan(planId: string) {
    this.wsClient?.confirmPlan(planId)
  }

  cancelTask(taskId: string) {
    this.wsClient?.cancelTask(taskId)
  }

  subscribe(handler: ChatEventHandler): () => void {
    const unsubscribes: Array<() => void> = []

    if (this.wsClient) {
      unsubscribes.push(this.wsClient.subscribe(handler))
    }
    if (this.sseClient) {
      unsubscribes.push(this.sseClient.subscribe(handler))
    }

    return () => {
      unsubscribes.forEach(unsub => unsub())
    }
  }

  disconnect() {
    this.wsClient?.disconnect()
    this.sseClient?.disconnect()
    this.wsClient = null
    this.sseClient = null
  }
}

// ==================== React Hook ====================

import { useEffect, useRef, useCallback, useState } from 'react'

export interface UseChatStreamingOptions {
  walletAddress: string
  enabled?: boolean
  onTextDelta?: (text: string) => void
  onToolCall?: (data: ToolCallData) => void
  onToolResult?: (data: ToolResultData) => void
  onProgress?: (data: ProgressData) => void
  onPlanReady?: (data: PlanReadyData) => void
  onTaskComplete?: () => void
  onError?: (error: string) => void
}

export function useChatStreaming(options: UseChatStreamingOptions) {
  const {
    walletAddress,
    enabled = true,
    onTextDelta,
    onToolCall,
    onToolResult,
    onProgress,
    onPlanReady,
    onTaskComplete,
    onError,
  } = options

  const serviceRef = useRef<ChatService | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [sessionId, setSessionId] = useState('')

  const handleEvent = useCallback((event: ChatStreamEvent) => {
    switch (event.event) {
      case 'text_delta':
        onTextDelta?.(event.data?.text || '')
        break
      case 'tool_call':
        onToolCall?.(event.data)
        break
      case 'tool_result':
        onToolResult?.(event.data)
        break
      case 'progress':
        onProgress?.(event.data)
        break
      case 'plan_ready':
        onPlanReady?.(event.data)
        break
      case 'task_complete':
        onTaskComplete?.()
        break
      case 'error':
        onError?.(event.data?.error || 'Unknown error')
        break
    }
  }, [onTextDelta, onToolCall, onToolResult, onProgress, onPlanReady, onTaskComplete, onError])

  useEffect(() => {
    if (!enabled || !walletAddress) return

    let mounted = true
    let service: ChatService | null = new ChatService()
    serviceRef.current = service

    const connect = async () => {
      try {
        const sid = await service!.connect(walletAddress)
        if (!mounted) return
        setSessionId(sid)
        await service!.startSSE(walletAddress)
        if (!mounted) return
        service!.subscribe(handleEvent)
        setIsConnected(true)
      } catch (error) {
        if (!mounted) return
        console.error('[useChatStreaming] Connection failed:', error)
        onError?.('Failed to connect to chat service')
      }
    }

    connect()

    return () => {
      mounted = false
      service?.disconnect()
      serviceRef.current = null
      setIsConnected(false)
    }
  }, [walletAddress, enabled, handleEvent, onError])

  const sendMessage = useCallback((message: string) => {
    serviceRef.current?.sendMessage(message)
  }, [])

  const confirmPlan = useCallback((planId: string) => {
    serviceRef.current?.confirmPlan(planId)
  }, [])

  const cancelTask = useCallback((taskId: string) => {
    serviceRef.current?.cancelTask(taskId)
  }, [])

  return {
    isConnected,
    sessionId,
    sendMessage,
    confirmPlan,
    cancelTask,
  }
}

export default ChatService
