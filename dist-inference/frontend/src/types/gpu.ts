export type GpuStatus = 'idle' | 'busy' | 'offline' | 'loading'

export interface GpuInfo {
  index: number
  name: string
  vram_total_gb: number
  vram_used_gb: number
  temperature_c: number
  power_w: number
  utilization_percent: number
  status: GpuStatus
}

export interface GpuModel {
  name: string
  vram_required_gb: number
  loaded: boolean
  loaded_at?: string
  total_requests: number
  total_tokens: number
}

export type NodeStatus = 'idle' | 'busy' | 'offline' | 'loading' | 'maintenance'

export interface GpuNode {
  node_id: string
  wallet_address: string
  ip_address: string
  status: NodeStatus
  gpu_count: number
  gpus: GpuInfo[]
  models: GpuModel[]
  last_heartbeat: string
  today_earnings: number
  total_earnings: number
  registered_at: string
}
