import { format, formatDistanceToNow } from 'date-fns'

/** Truncate wallet address: 0x1234...abcd */
export function truncateWallet(addr: string, chars = 4): string {
  if (!addr || addr.length < 10) return addr
  return `${addr.slice(0, chars + 2)}...${addr.slice(-chars)}`
}

/** Format number: 1234 → 1.2K, 1234567 → 1.2M */
export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}

/** Format Vibe amount with 4 decimal places */
export function formatVibe(amount: number): string {
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(2)}M`
  if (amount >= 1_000) return `${(amount / 1_000).toFixed(2)}K`
  return amount.toFixed(4)
}

/** Format timestamp */
export function formatTime(iso: string): string {
  return format(new Date(iso), 'HH:mm:ss')
}

export function formatDate(iso: string): string {
  return format(new Date(iso), 'yyyy-MM-dd')
}

export function formatDateTime(iso: string): string {
  return format(new Date(iso), 'yyyy-MM-dd HH:mm:ss')
}

export function timeAgo(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true })
}

/** Format latency in ms */
export function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

/** Format VRAM in GB */
export function formatVRAM(gb: number): string {
  return `${gb.toFixed(0)}GB`
}

/** Calculate percentage */
export function pct(used: number, total: number): number {
  if (total === 0) return 0
  return Math.round((used / total) * 100)
}

/** Status color mapping */
export const STATUS_COLORS = {
  idle: 'neon-green',
  busy: 'neon-blue',
  offline: 'neon-red',
  loading: 'neon-yellow',
  maintenance: 'neon-purple',
  queued: 'neon-yellow',
  running: 'neon-blue',
  completed: 'neon-green',
  failed: 'neon-red',
  cancelled: 'text-secondary',
} as const

/** Get badge class */
export function getStatusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    idle: 'badge-green',
    busy: 'badge-blue',
    offline: 'badge-red',
    loading: 'badge-yellow',
    maintenance: 'badge-purple',
    queued: 'badge-yellow',
    running: 'badge-blue',
    completed: 'badge-green',
    failed: 'badge-red',
    cancelled: 'badge-purple',
    pending: 'badge-yellow',
  }
  return map[status] ?? 'badge-blue'
}

/** Clamp value */
export function clamp(val: number, min: number, max: number): number {
  return Math.min(Math.max(val, min), max)
}
