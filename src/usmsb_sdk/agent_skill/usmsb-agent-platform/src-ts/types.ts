/**
 * Type definitions for USMSB Agent Platform Skill.
 */

/**
 * Stake tier levels as defined in whitepaper.
 */
export enum StakeTier {
  NONE = 0,
  BRONZE = 100,      // 100-999 VIBE
  SILVER = 1000,     // 1000-4999 VIBE
  GOLD = 5000,       // 5000-9999 VIBE
  PLATINUM = 10000,  // 10000+ VIBE
}

/**
 * Order lifecycle status.
 */
export enum OrderStatus {
  CREATED = "created",
  CONFIRMED = "confirmed",
  IN_PROGRESS = "in_progress",
  DELIVERED = "delivered",
  COMPLETED = "completed",
  DISPUTED = "disputed",
  CANCELLED = "cancelled",
  EXPIRED = "expired",
  REFUNDED = "refunded",
}

/**
 * Action types and their stake requirements.
 */
export enum ActionType {
  // Requires stake (100 VIBE minimum)
  COLLABORATION_CREATE = "collaboration:create",
  COLLABORATION_CONTRIBUTE = "collaboration:contribute",
  MARKETPLACE_PUBLISH_SERVICE = "marketplace:publish_service",
  NEGOTIATION_ACCEPT = "negotiation:accept",
  WORKFLOW_EXECUTE = "workflow:execute",
  ORDER_ACCEPT = "order:accept",
  ORDER_CANCEL = "order:cancel",

  // No stake required
  COLLABORATION_JOIN = "collaboration:join",
  COLLABORATION_LIST = "collaboration:list",
  MARKETPLACE_FIND_WORK = "marketplace:find_work",
  MARKETPLACE_FIND_WORKERS = "marketplace:find_workers",
  MARKETPLACE_PUBLISH_DEMAND = "marketplace:publish_demand",
  MARKETPLACE_HIRE = "marketplace:hire",
  DISCOVERY_BY_CAPABILITY = "discovery:by_capability",
  DISCOVERY_BY_SKILL = "discovery:by_skill",
  DISCOVERY_RECOMMEND = "discovery:recommend",
  NEGOTIATION_INITIATE = "negotiation:initiate",
  NEGOTIATION_REJECT = "negotiation:reject",
  NEGOTIATION_PROPOSE = "negotiation:propose",
  WORKFLOW_CREATE = "workflow:create",
  WORKFLOW_LIST = "workflow:list",
  LEARNING_ANALYZE = "learning:analyze",
  LEARNING_INSIGHTS = "learning:insights",

  // Order actions
  ORDER_FROM_PRE_MATCH = "order:from_pre_match",
  ORDER_CREATE = "order:create",
  ORDER_CONFIRM = "order:confirm",
  ORDER_START = "order:start",
  ORDER_DELIVER = "order:deliver",
  ORDER_DISPUTE = "order:dispute",
  ORDER_LIST = "order:list",
  ORDER_GET = "order:get",
  ORDER_STATUS = "order:status",
}

// Action metadata
export interface ActionMeta {
  category: string;
  action: string;
  requiresStake: boolean;
}

// Action metadata map
export const ACTION_META: Record<ActionType, ActionMeta> = {
  [ActionType.COLLABORATION_CREATE]: { category: "collaboration", action: "create", requiresStake: true },
  [ActionType.COLLABORATION_CONTRIBUTE]: { category: "collaboration", action: "contribute", requiresStake: true },
  [ActionType.MARKETPLACE_PUBLISH_SERVICE]: { category: "marketplace", action: "publish_service", requiresStake: true },
  [ActionType.NEGOTIATION_ACCEPT]: { category: "negotiation", action: "accept", requiresStake: true },
  [ActionType.WORKFLOW_EXECUTE]: { category: "workflow", action: "execute", requiresStake: true },
  [ActionType.ORDER_ACCEPT]: { category: "order", action: "accept", requiresStake: false },
  [ActionType.ORDER_CANCEL]: { category: "order", action: "cancel", requiresStake: false },
  [ActionType.COLLABORATION_JOIN]: { category: "collaboration", action: "join", requiresStake: false },
  [ActionType.COLLABORATION_LIST]: { category: "collaboration", action: "list", requiresStake: false },
  [ActionType.MARKETPLACE_FIND_WORK]: { category: "marketplace", action: "find_work", requiresStake: false },
  [ActionType.MARKETPLACE_FIND_WORKERS]: { category: "marketplace", action: "find_workers", requiresStake: false },
  [ActionType.MARKETPLACE_PUBLISH_DEMAND]: { category: "marketplace", action: "publish_demand", requiresStake: false },
  [ActionType.MARKETPLACE_HIRE]: { category: "marketplace", action: "hire", requiresStake: false },
  [ActionType.DISCOVERY_BY_CAPABILITY]: { category: "discovery", action: "by_capability", requiresStake: false },
  [ActionType.DISCOVERY_BY_SKILL]: { category: "discovery", action: "by_skill", requiresStake: false },
  [ActionType.DISCOVERY_RECOMMEND]: { category: "discovery", action: "recommend", requiresStake: false },
  [ActionType.NEGOTIATION_INITIATE]: { category: "negotiation", action: "initiate", requiresStake: false },
  [ActionType.NEGOTIATION_REJECT]: { category: "negotiation", action: "reject", requiresStake: false },
  [ActionType.NEGOTIATION_PROPOSE]: { category: "negotiation", action: "propose", requiresStake: false },
  [ActionType.WORKFLOW_CREATE]: { category: "workflow", action: "create", requiresStake: false },
  [ActionType.WORKFLOW_LIST]: { category: "workflow", action: "list", requiresStake: false },
  [ActionType.LEARNING_ANALYZE]: { category: "learning", action: "analyze", requiresStake: false },
  [ActionType.LEARNING_INSIGHTS]: { category: "learning", action: "insights", requiresStake: false },
  // Order actions
  [ActionType.ORDER_FROM_PRE_MATCH]: { category: "order", action: "from_pre_match", requiresStake: false },
  [ActionType.ORDER_CREATE]: { category: "order", action: "create", requiresStake: false },
  [ActionType.ORDER_CONFIRM]: { category: "order", action: "confirm", requiresStake: false },
  [ActionType.ORDER_START]: { category: "order", action: "start", requiresStake: false },
  [ActionType.ORDER_DELIVER]: { category: "order", action: "deliver", requiresStake: false },
  [ActionType.ORDER_DISPUTE]: { category: "order", action: "dispute", requiresStake: false },
  [ActionType.ORDER_LIST]: { category: "order", action: "list", requiresStake: false },
  [ActionType.ORDER_GET]: { category: "order", action: "get", requiresStake: false },
  [ActionType.ORDER_STATUS]: { category: "order", action: "status", requiresStake: false },
};

/**
 * Stake information for an agent.
 */
export interface StakeInfo {
  agentId: string;
  stakedAmount: number;
  tier: StakeTier;
  lockedUntil?: number;
}

/**
 * Create StakeInfo from staked amount.
 */
export function stakeInfoFromAmount(agentId: string, amount: number): StakeInfo {
  let tier = StakeTier.NONE;
  for (const t of [StakeTier.PLATINUM, StakeTier.GOLD, StakeTier.SILVER, StakeTier.BRONZE]) {
    if (amount >= t) {
      tier = t;
      break;
    }
  }
  return { agentId, stakedAmount: amount, tier };
}

/**
 * Parsed intent from natural language request.
 */
export interface Intent {
  action: ActionType;
  parameters: Record<string, any>;
  confidence: number;
  rawRequest: string;
}

/**
 * Result from platform operation.
 */
export interface PlatformResult {
  success: boolean;
  result?: Record<string, any>;
  error?: string;
  code?: string;
  message?: string;
}

/**
 * Standard error codes.
 */
export const ErrorCode = {
  INSUFFICIENT_STAKE: "INSUFFICIENT_STAKE",
  PARSE_ERROR: "PARSE_ERROR",
  UNAUTHORIZED: "UNAUTHORIZED",
  NOT_FOUND: "NOT_FOUND",
  INTERNAL_ERROR: "INTERNAL_ERROR",
  RATE_LIMITED: "RATE_LIMITED",
  VALIDATION_ERROR: "VALIDATION_ERROR",
} as const;

export type ErrorCodeType = typeof ErrorCode[keyof typeof ErrorCode];

/**
 * Order terms agreed between parties.
 */
export interface OrderTerms {
  price: number;
  deliveryTime?: string;   // ISO datetime
  deliveryDescription?: string;
  qualityGuarantees?: Record<string, any>;
  paymentTerms?: string;   // "escrow", "upfront", "milestone"
  milestones?: Array<{
    description: string;
    amount: number;
    deadline?: string;
  }>;
  additionalConditions?: Record<string, any>;
}

/**
 * A deliverable artifact.
 */
export interface Deliverable {
  artifactId: string;
  description: string;
  artifactType: string;
  urlOrContent: string;
  submittedAt: string;
  verified: boolean;
}

/**
 * Order data returned from API.
 */
export interface Order {
  orderId: string;
  source: string;
  sourceSessionId?: string;
  demandAgentId: string;
  supplyAgentId: string;
  taskDescription: string;
  terms: OrderTerms;
  poolId?: string;
  status: OrderStatus;
  priority: string;
  deliveryDeadline?: string;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  completionReason?: string;
  deliverables: Deliverable[];
  acceptanceData: Record<string, any>;
  chainOrderId?: string;
  chainTxHash?: string;
  vibeLocked: number;
  metadata: Record<string, any>;
  availableActions: string[];
  stateHistory: Array<{
    from_status: string;
    to_status: string;
    event: string;
    triggered_by: string;
    reason: string;
    timestamp: string;
  }>;
  isTerminal: boolean;
}

/**
 * Result of order creation.
 */
export interface OrderCreationResult {
  success: boolean;
  order?: Order;
  message: string;
  negotiationSessionId?: string;
}

/**
 * Result of joint order pool creation.
 */
export interface PoolCreationResult {
  success: boolean;
  poolId?: string;
  chainOrderId?: string;
  txHash?: string;
  message: string;
}
