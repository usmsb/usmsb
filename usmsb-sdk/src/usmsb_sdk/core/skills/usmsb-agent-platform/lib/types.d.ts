/**
 * Type definitions for USMSB Agent Platform Skill.
 */
/**
 * Stake tier levels as defined in whitepaper.
 */
export declare enum StakeTier {
    NONE = 0,
    BRONZE = 100,// 100-999 VIBE
    SILVER = 1000,// 1000-4999 VIBE
    GOLD = 5000,// 5000-9999 VIBE
    PLATINUM = 10000
}
/**
 * Action types and their stake requirements.
 */
export declare enum ActionType {
    COLLABORATION_CREATE = "collaboration:create",
    COLLABORATION_CONTRIBUTE = "collaboration:contribute",
    MARKETPLACE_PUBLISH_SERVICE = "marketplace:publish_service",
    NEGOTIATION_ACCEPT = "negotiation:accept",
    WORKFLOW_EXECUTE = "workflow:execute",
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
    LEARNING_INSIGHTS = "learning:insights"
}
export interface ActionMeta {
    category: string;
    action: string;
    requiresStake: boolean;
}
export declare const ACTION_META: Record<ActionType, ActionMeta>;
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
export declare function stakeInfoFromAmount(agentId: string, amount: number): StakeInfo;
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
export declare const ErrorCode: {
    readonly INSUFFICIENT_STAKE: "INSUFFICIENT_STAKE";
    readonly PARSE_ERROR: "PARSE_ERROR";
    readonly UNAUTHORIZED: "UNAUTHORIZED";
    readonly NOT_FOUND: "NOT_FOUND";
    readonly INTERNAL_ERROR: "INTERNAL_ERROR";
    readonly RATE_LIMITED: "RATE_LIMITED";
    readonly VALIDATION_ERROR: "VALIDATION_ERROR";
};
export type ErrorCodeType = typeof ErrorCode[keyof typeof ErrorCode];
//# sourceMappingURL=types.d.ts.map