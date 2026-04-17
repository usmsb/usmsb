export type RequestStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface InferenceRequest {
  request_id: string
  model_name: string
  user_wallet: string
  node_id: string
  status: RequestStatus
  input_tokens: number
  output_tokens: number
  latency_ms: number
  cost_vibe: number
  created_at: string
  completed_at?: string
  error?: string
}

export interface InferenceStats {
  total_requests: number
  success_rate: number
  avg_latency_ms: number
  total_tokens: number
  total_cost_vibe: number
}
