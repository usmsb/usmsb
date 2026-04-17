type SSECallback<T> = (data: T) => void

class SSEClient {
  private eventSources: Map<string, EventSource> = new Map()
  private reconnectTimers: Map<string, ReturnType<typeof setTimeout>> = new Map()
  private reconnectAttempts: Map<string, number> = new Map()

  subscribe<T>(url: string, onMessage: SSECallback<T>, onError?: (e: Event) => void): () => void {
    this.close(url)
    this.connect<T>(url, onMessage, onError)
    return () => this.close(url)
  }

  private connect<T>(url: string, onMessage: SSECallback<T>, onError?: (e: Event) => void) {
    const es = new EventSource(url)
    this.eventSources.set(url, es)

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch {}
    }

    es.onerror = (e) => {
      onError?.(e)
      this.scheduleReconnect<T>(url, onMessage, onError)
    }
  }

  private scheduleReconnect<T>(url: string, onMessage: SSECallback<T>, onError?: (e: Event) => void) {
    const attempts = this.reconnectAttempts.get(url) ?? 0
    const delay = Math.min(1000 * 2 ** attempts, 30_000)
    this.reconnectAttempts.set(url, attempts + 1)

    const timer = setTimeout(() => {
      this.reconnectTimers.delete(url)
      this.connect<T>(url, onMessage, onError)
    }, delay)
    this.reconnectTimers.set(url, timer)
  }

  close(url: string) {
    this.eventSources.get(url)?.close()
    this.eventSources.delete(url)
    clearTimeout(this.reconnectTimers.get(url))
    this.reconnectTimers.delete(url)
    this.reconnectAttempts.delete(url)
  }

  closeAll() {
    this.eventSources.forEach((es) => es.close())
    this.eventSources.clear()
    this.reconnectTimers.forEach((t) => clearTimeout(t))
    this.reconnectTimers.clear()
  }
}

export const sseClient = new SSEClient()
