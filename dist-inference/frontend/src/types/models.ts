export interface ModelInfo {
  model_id: string
  name: string
  vram_required_gb: number
  gpu_count_needed: number
  is_preloaded: boolean
  loaded_on_nodes: string[]
  total_requests: number
  avg_latency_ms: number
  description?: string
}
