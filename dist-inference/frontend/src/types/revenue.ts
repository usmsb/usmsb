export interface RevenueStats {
  total_revenue_vibe: number
  today_revenue_vibe: number
  month_revenue_vibe: number
  gpu_time_revenue_vibe: number
  token_fee_revenue_vibe: number
  platform_share_vibe: number
  node_payout_vibe: number
}

export interface RevenueTrend {
  date: string
  revenue_vibe: number
  requests: number
}

export interface WithdrawalRecord {
  id: string
  wallet_address: string
  amount_vibe: number
  status: 'pending' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
  tx_hash?: string
}
