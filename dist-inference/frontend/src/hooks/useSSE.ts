import { useEffect, useRef } from 'react'
import { sseClient } from '@/lib/sse'

export function useSSE<T>(
  url: string | null,
  onMessage: (data: T) => void,
  onError?: (e: Event) => void
) {
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    if (!url) return
    const cleanup = sseClient.subscribe<T>(url, onMessageRef.current, onError)
    return cleanup
  }, [url, onError])

  useEffect(() => {
    return () => sseClient.closeAll()
  }, [])
}
