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
