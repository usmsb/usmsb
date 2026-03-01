// USMSB SDK API Types

export interface Agent {
  id: string
  name: string
  type: AgentType
  capabilities: string[]
  state: Record<string, unknown>
  goals_count: number
  resources_count: number
  created_at: number
}

export type AgentType = 'human' | 'ai_agent' | 'organization' | 'system'

export interface AgentCreate {
  name: string
  type: AgentType
  capabilities?: string[]
  state?: Record<string, unknown>
}

export interface Goal {
  id: string
  name: string
  description: string
  priority: number
  status: GoalStatus
}

export type GoalStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'

export interface GoalCreate {
  name: string
  description?: string
  priority?: number
}

export interface Environment {
  id: string
  name: string
  type: EnvironmentType
  state: Record<string, unknown>
}

export type EnvironmentType = 'natural' | 'social' | 'technological' | 'economic' | 'virtual'

export interface EnvironmentCreate {
  name: string
  type: EnvironmentType
  state?: Record<string, unknown>
}

export interface PredictionRequest {
  agent_id: string
  environment_id?: string
  goal_name?: string
  context?: Record<string, unknown>
}

export interface Prediction {
  predicted_actions: PredictedAction[]
  confidence: number
  reasoning: string
  alternative_scenarios: AlternativeScenario[]
  risk_factors: string[]
}

export interface PredictedAction {
  type: string
  description: string
  parameters?: Record<string, unknown>
}

export interface AlternativeScenario {
  name: string
  probability: number
  description: string
}

export interface Workflow {
  id: string
  name: string
  steps_count: number
  status: WorkflowStatus
}

export type WorkflowStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'

export interface WorkflowCreate {
  task_description: string
  agent_id: string
  available_tools?: string[]
}

export interface WorkflowResult {
  workflow_id: string
  status: WorkflowStatus
  total_steps: number
  completed_steps: number
  failed_steps: number
  execution_time: number
  step_results: Record<string, unknown>
}

export interface HealthResponse {
  status: string
  version: string
  timestamp: number
  services: Record<string, string>
}

export interface Metrics {
  agents_count: number
  environments_count: number
  intelligence_sources?: IntelligenceSourceMetrics
  daily_activity?: Array<{ name: string; agents: number; predictions: number; workflows: number }>
  weekly_usage?: Array<{ name: string; used: number }>
}

export interface IntelligenceSourceMetrics {
  total_sources: number
  llm_sources: number
  knowledge_sources: number
  agentic_sources: number
  total_requests: number
  successful_requests: number
  failed_requests: number
  success_rate: number
  total_cost: number
  total_tokens: number
}

// ========== Active Matching Types ==========

export interface MatchScore {
  overall: number
  capability_match: number
  price_match: number
  reputation_match: number
  time_match: number
  suggested_price_range?: Record<string, number>
  reasoning: string
}

export interface Opportunity {
  opportunity_id: string
  counterpart_agent_id: string
  counterpart_name: string
  opportunity_type: 'supply' | 'demand'
  details: Record<string, unknown>
  match_score: MatchScore
  status: 'discovered' | 'contacted' | 'negotiating' | 'accepted' | 'rejected' | 'expired'
  created_at: number
  negotiation_session_id?: string
}

export interface NegotiationProposal {
  price: number
  delivery_time: string
  payment_terms: string
  quality_guarantee?: string
  additional_terms?: Record<string, unknown>
}

export interface NegotiationRound {
  round_number: number
  proposer_id: string
  proposal: NegotiationProposal
  response: 'accepted' | 'rejected' | 'counter' | 'pending'
  counter_proposal?: NegotiationProposal
}

export interface NegotiationSession {
  session_id: string
  initiator_id: string
  counterpart_id: string
  context: Record<string, unknown>
  status: 'pending' | 'in_progress' | 'agreed' | 'rejected' | 'timeout'
  rounds: NegotiationRound[]
  final_terms?: NegotiationProposal
  created_at: number
}

export interface MatchingStats {
  total_opportunities: number
  active_negotiations: number
  successful_matches: number
  pending_responses: number
}

// ========== Network Explorer Types ==========

export interface AgentNetworkStats {
  total_explorations: number
  total_discovered: number
  network_size: number
  trusted_agents: number
}

export interface NetworkAgent {
  agent_id: string
  agent_name: string
  capabilities: string[]
  skills: string[]
  reputation: number
  status: string
}

export interface AgentRecommendation {
  recommended_agent_id: string
  recommended_agent_name: string
  capability_match: number
  trust_score: number
  reason: string
}

// ========== Marketplace Service Types ==========

// Legacy types for backward compatibility
export interface ServiceResponse {
  id: string
  service_name: string
  description?: string
  service_type?: string
  capabilities?: string[]
  skills?: string[] | string
  price?: number
  availability?: string
  agent_id?: string
  created_at: number
}

export interface DemandResponse {
  id: string
  title: string
  description?: string
  category?: string
  required_skills?: string[] | string
  budget_min?: number
  budget_max?: number
  priority?: string
  deadline?: string
  agent_id?: string
  created_at: number
}

export interface Service {
  id: string
  agent_id: string
  service_name: string
  description: string
  category: string
  skills: string[]
  price: number
  price_type: string
  status: string
  created_at: number
}

export interface ServiceCreate {
  agent_id: string
  service_name: string
  description: string
  category: string
  skills: string[]
  price: number
  price_type: string
}

export interface Demand {
  id: string
  agent_id: string
  title: string
  description: string
  category: string
  required_skills: string[]
  budget_min?: number
  budget_max?: number
  status: string
  created_at: number
}

export interface DemandCreate {
  agent_id: string
  title: string
  description: string
  category: string
  required_skills: string[]
  budget_min?: number
  budget_max?: number
  deadline?: string
  priority?: string
  quality_requirements?: string
}

// ========== Matching Result Types ==========

export interface MatchingSearchResult {
  opportunity_id?: string
  counterpart_agent_id?: string
  agent_id?: string
  counterpart_name?: string
  name?: string
  opportunity_type?: 'supply' | 'demand'
  details?: Record<string, unknown>
  match_score?: MatchingScoreBreakdown
  status?: OpportunityStatus
  created_at?: number
}

export interface MatchingScoreBreakdown {
  overall: number
  capability_match: number
  capability?: number
  price_match: number
  price?: number
  reputation_match: number
  reputation?: number
  time_match: number
  time?: number
  reasoning?: string
}

export type OpportunityStatus = 'discovered' | 'contacted' | 'negotiating' | 'accepted' | 'rejected' | 'expired'

// Alias for backward compatibility
export type MatchStats = MatchingStats

// Type guard for parsing skills array
export function parseSkillsArray(skills: string[] | string | undefined): string[] {
  if (!skills) return []
  if (Array.isArray(skills)) return skills
  try {
    return JSON.parse(skills)
  } catch {
    return []
  }
}

// Helper function to transform API opportunity response to typed Opportunity
export function transformToOpportunity(opp: MatchingSearchResult): Opportunity {
  return {
    opportunity_id: opp.opportunity_id || '',
    counterpart_agent_id: opp.counterpart_agent_id || '',
    counterpart_name: opp.counterpart_name || 'Unknown Agent',
    opportunity_type: opp.opportunity_type || 'demand',
    details: opp.details || {},
    match_score: opp.match_score ? {
      overall: opp.match_score.overall ?? 0.5,
      capability_match: opp.match_score.capability_match ?? opp.match_score.capability ?? 0.5,
      price_match: opp.match_score.price_match ?? opp.match_score.price ?? 0.5,
      reputation_match: opp.match_score.reputation_match ?? opp.match_score.reputation ?? 0.5,
      time_match: opp.match_score.time_match ?? opp.match_score.time ?? 0.5,
      reasoning: opp.match_score.reasoning || 'Match available',
    } : {
      overall: 0.5,
      capability_match: 0.5,
      price_match: 0.5,
      reputation_match: 0.5,
      time_match: 0.5,
      reasoning: 'Match available',
    },
    status: opp.status || 'discovered',
    created_at: opp.created_at || Date.now(),
  }
}

// Helper to check if a negotiation is active
export function isNegotiationActive(negotiation: { status: string }): boolean {
  return negotiation.status === 'pending' || negotiation.status === 'in_progress'
}

// ========== Agent Registration & Binding Types ==========

export interface SelfRegistrationRequest {
  name: string
  description?: string
  capabilities?: string[]
}

export interface SelfRegistrationResponse {
  success: boolean
  agent_id: string
  api_key: string
  level: number
  binding_status: string
  message: string
}

export interface BindingRequestRequest {
  message?: string
}

export interface BindingRequestResponse {
  success: boolean
  binding_code: string
  binding_url: string
  expires_in: number
  expires_at?: number
  message: string
}

export interface BindingStatus {
  bound: boolean
  binding_status: string
  owner_wallet?: string
  stake_tier: string
  staked_amount: number
  tier_benefits?: TierBenefits
  pending_request?: {
    binding_code: string
    binding_url: string
    expires_at: number
    status: string
  }
}

export interface CompleteBindingRequest {
  stake_amount: number
}

export interface CompleteBindingResponse {
  success: boolean
  agent_id: string
  owner_wallet: string
  stake_amount: number
  stake_tier: string
  tier_benefits?: TierBenefits
  completed_at: number
  message: string
}

// ========== API Key Types ==========

export interface APIKeyInfo {
  id: string
  prefix: string
  name: string
  level: number
  expires_at?: number
  last_used_at?: number
  created_at: number
  revoked?: boolean
}

export interface APIKeyListResponse {
  success: boolean
  keys: APIKeyInfo[]
}

export interface CreateAPIKeyRequest {
  name: string
  expires_in_days?: number
}

export interface CreateAPIKeyResponse {
  success: boolean
  key_id: string
  api_key: string
  name: string
  expires_at: number
  message: string
}

export interface RenewAPIKeyRequest {
  extends_days: number
}

export interface RenewAPIKeyResponse {
  success: boolean
  key_id: string
  new_expires_at: number
  message: string
}

// ========== Stake Tier Types ==========

export interface TierBenefits {
  max_agents: number
  discount: number
}

export type StakeTier = 'NONE' | 'BRONZE' | 'SILVER' | 'GOLD' | 'PLATINUM'

// ========== Staking Types ==========

export interface DepositRequest {
  amount: number
}

export interface WithdrawRequest {
  amount: number
}

export interface StakingInfo {
  success: boolean
  agent_id: string
  staked_amount: number
  stake_status: string
  stake_tier: StakeTier
  locked_stake: number
  unlock_available_at?: number
  pending_rewards: number
  apy: number
  tier_benefits: TierBenefits
}

export interface RewardsInfo {
  success: boolean
  agent_id: string
  pending_rewards: number
  total_claimed: number
  last_claim_at?: number
  apy: number
}

export interface ClaimRewardsResponse {
  success: boolean
  agent_id: string
  claimed_amount: number
  new_balance: number
  message: string
}

// ========== Reputation Types ==========

export interface ReputationInfo {
  success: boolean
  agent_id: string
  score: number
  tier: string
  total_transactions: number
  successful_transactions: number
  success_rate: number
  avg_rating: number
  total_ratings: number
}

export interface ReputationEvent {
  timestamp: number
  event_type: string
  change: number
  reason: string
  related_id?: string
}

export interface ReputationHistory {
  success: boolean
  agent_id: string
  current_score: number
  history: ReputationEvent[]
  total_events: number
}

// ========== Wallet Types ==========

export interface WalletBalance {
  success: boolean
  agent_id: string
  balance: number
  staked_amount: number
  locked_amount: number
  pending_rewards: number
  total_assets: number
  stake_tier: StakeTier
  tier_benefits: TierBenefits
}

export interface TransactionRecord {
  id: string
  transaction_type: string
  amount: number
  status: string
  counterparty_id?: string
  title?: string
  description?: string
  created_at: number
  completed_at?: number
}

export interface TransactionHistory {
  success: boolean
  agent_id: string
  transactions: TransactionRecord[]
  total_count: number
  page: number
  page_size: number
}

// ========== Heartbeat Types ==========

export interface HeartbeatRequest {
  status: 'online' | 'busy' | 'offline'
  metadata?: Record<string, unknown>
}

export interface HeartbeatResponse {
  success: boolean
  agent_id: string
  status: string
  ttl_remaining: number
  last_heartbeat: number
  is_alive: boolean
  message: string
}

export interface HeartbeatStatus {
  success: boolean
  agent_id: string
  status: string
  last_heartbeat: number
  ttl_remaining: number
  is_alive: boolean
  heartbeat_interval: number
  ttl: number
}

// ========== System Status Types ==========

export interface SystemStatus {
  version: string
  uptime: {
    seconds: number
    hours: number
    days: number
  }
  platform: {
    system: string
    python: string
  }
  agents: {
    online: number
    offline: number
    busy: number
  }
  stake_distribution: Record<string, number>
  services: {
    llm: boolean
    prediction: boolean
    workflow: boolean
    meta_agent: boolean
  }
  timestamp: number
}

export interface StatsSummary {
  total_agents: number
  online_agents: number
  bound_agents: number
  total_stake: number
  total_balance: number
  active_services: number
  active_demands: number
  active_collaborations: number
}

// ========== Agent Profile Types ==========

export interface AgentProfile {
  success: boolean
  result: {
    agent_id: string
    name: string
    description: string
    capabilities: string[]
    status: string
    reputation: number
    level: number
    binding_status: string
    owner_wallet?: string
    stake_tier: StakeTier
    staked_amount: number
    created_at: number
  }
}

export interface OwnerInfo {
  success: boolean
  result: {
    owner_wallet: string
    staked_amount: number
    stake_status: string
    stake_tier: StakeTier
    bound_at: number
  }
}

export interface UpdateProfileRequest {
  name?: string
  description?: string
  capabilities?: string[]
}

// ========== Error Types ==========

export interface APIErrorDetail {
  success: false
  error: string
  code: string
  message?: string
  stake_requirement?: {
    required: number
    current: number
    shortfall: number
    action: string
  }
  retry_after?: number
  recovery_suggestion?: string
  request_id?: string
  timestamp?: number
}
