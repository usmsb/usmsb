"use strict";
/**
 * Type definitions for USMSB Agent Platform Skill.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ErrorCode = exports.ACTION_META = exports.ActionType = exports.OrderStatus = exports.StakeTier = void 0;
exports.stakeInfoFromAmount = stakeInfoFromAmount;
/**
 * Stake tier levels as defined in whitepaper.
 */
var StakeTier;
(function (StakeTier) {
    StakeTier[StakeTier["NONE"] = 0] = "NONE";
    StakeTier[StakeTier["BRONZE"] = 100] = "BRONZE";
    StakeTier[StakeTier["SILVER"] = 1000] = "SILVER";
    StakeTier[StakeTier["GOLD"] = 5000] = "GOLD";
    StakeTier[StakeTier["PLATINUM"] = 10000] = "PLATINUM";
})(StakeTier || (exports.StakeTier = StakeTier = {}));
/**
 * Order lifecycle status.
 */
var OrderStatus;
(function (OrderStatus) {
    OrderStatus["CREATED"] = "created";
    OrderStatus["CONFIRMED"] = "confirmed";
    OrderStatus["IN_PROGRESS"] = "in_progress";
    OrderStatus["DELIVERED"] = "delivered";
    OrderStatus["COMPLETED"] = "completed";
    OrderStatus["DISPUTED"] = "disputed";
    OrderStatus["CANCELLED"] = "cancelled";
    OrderStatus["EXPIRED"] = "expired";
    OrderStatus["REFUNDED"] = "refunded";
})(OrderStatus || (exports.OrderStatus = OrderStatus = {}));
/**
 * Action types and their stake requirements.
 */
var ActionType;
(function (ActionType) {
    // Requires stake (100 VIBE minimum)
    ActionType["COLLABORATION_CREATE"] = "collaboration:create";
    ActionType["COLLABORATION_CONTRIBUTE"] = "collaboration:contribute";
    ActionType["MARKETPLACE_PUBLISH_SERVICE"] = "marketplace:publish_service";
    ActionType["NEGOTIATION_ACCEPT"] = "negotiation:accept";
    ActionType["WORKFLOW_EXECUTE"] = "workflow:execute";
    ActionType["ORDER_ACCEPT"] = "order:accept";
    ActionType["ORDER_CANCEL"] = "order:cancel";
    // No stake required
    ActionType["COLLABORATION_JOIN"] = "collaboration:join";
    ActionType["COLLABORATION_LIST"] = "collaboration:list";
    ActionType["MARKETPLACE_FIND_WORK"] = "marketplace:find_work";
    ActionType["MARKETPLACE_FIND_WORKERS"] = "marketplace:find_workers";
    ActionType["MARKETPLACE_PUBLISH_DEMAND"] = "marketplace:publish_demand";
    ActionType["MARKETPLACE_HIRE"] = "marketplace:hire";
    ActionType["DISCOVERY_BY_CAPABILITY"] = "discovery:by_capability";
    ActionType["DISCOVERY_BY_SKILL"] = "discovery:by_skill";
    ActionType["DISCOVERY_RECOMMEND"] = "discovery:recommend";
    ActionType["NEGOTIATION_INITIATE"] = "negotiation:initiate";
    ActionType["NEGOTIATION_REJECT"] = "negotiation:reject";
    ActionType["NEGOTIATION_PROPOSE"] = "negotiation:propose";
    ActionType["WORKFLOW_CREATE"] = "workflow:create";
    ActionType["WORKFLOW_LIST"] = "workflow:list";
    ActionType["LEARNING_ANALYZE"] = "learning:analyze";
    ActionType["LEARNING_INSIGHTS"] = "learning:insights";
    // Order actions
    ActionType["ORDER_FROM_PRE_MATCH"] = "order:from_pre_match";
    ActionType["ORDER_CREATE"] = "order:create";
    ActionType["ORDER_CONFIRM"] = "order:confirm";
    ActionType["ORDER_START"] = "order:start";
    ActionType["ORDER_DELIVER"] = "order:deliver";
    ActionType["ORDER_DISPUTE"] = "order:dispute";
    ActionType["ORDER_LIST"] = "order:list";
    ActionType["ORDER_GET"] = "order:get";
    ActionType["ORDER_STATUS"] = "order:status";
})(ActionType || (exports.ActionType = ActionType = {}));
// Action metadata map
exports.ACTION_META = {
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
 * Create StakeInfo from staked amount.
 */
function stakeInfoFromAmount(agentId, amount) {
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
 * Standard error codes.
 */
exports.ErrorCode = {
    INSUFFICIENT_STAKE: "INSUFFICIENT_STAKE",
    PARSE_ERROR: "PARSE_ERROR",
    UNAUTHORIZED: "UNAUTHORIZED",
    NOT_FOUND: "NOT_FOUND",
    INTERNAL_ERROR: "INTERNAL_ERROR",
    RATE_LIMITED: "RATE_LIMITED",
    VALIDATION_ERROR: "VALIDATION_ERROR",
};
//# sourceMappingURL=types.js.map