"use strict";
/**
 * Stake checker for verifying stake requirements.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.StakeChecker = void 0;
const types_1 = require("./types");
/**
 * Tier configuration.
 */
const TIER_CONFIG = {
    [types_1.StakeTier.NONE]: { min: 0, maxAgents: 0, discount: 0 },
    [types_1.StakeTier.BRONZE]: { min: 100, maxAgents: 1, discount: 0 },
    [types_1.StakeTier.SILVER]: { min: 1000, maxAgents: 3, discount: 5 },
    [types_1.StakeTier.GOLD]: { min: 5000, maxAgents: 10, discount: 10 },
    [types_1.StakeTier.PLATINUM]: { min: 10000, maxAgents: 50, discount: 20 },
};
/**
 * Stake checker class.
 */
class StakeChecker {
    constructor(client) {
        this.cache = new Map();
        this.client = client;
    }
    /**
     * Get stake information for an agent.
     */
    async getStakeInfo(agentId) {
        // Check cache first
        if (this.cache.has(agentId)) {
            return this.cache.get(agentId);
        }
        // Fetch from platform if client available
        let stakedAmount = 0;
        if (this.client && typeof this.client.getStakedAmount === "function") {
            stakedAmount = await this.client.getStakedAmount(agentId);
        }
        const info = (0, types_1.stakeInfoFromAmount)(agentId, stakedAmount);
        this.cache.set(agentId, info);
        return info;
    }
    /**
     * Verify if an agent has sufficient stake for an action.
     */
    async verifyStake(agentId, action) {
        const meta = types_1.ACTION_META[action];
        // Actions that don't require stake pass immediately
        if (!meta.requiresStake) {
            return { valid: true };
        }
        // Get stake info
        const stakeInfo = await this.getStakeInfo(agentId);
        // Check if stake is sufficient
        if (stakeInfo.stakedAmount < StakeChecker.MIN_STAKE_WHITEPAPER) {
            return {
                valid: false,
                error: `Insufficient stake: action '${meta.action}' requires ` +
                    `minimum ${StakeChecker.MIN_STAKE_WHITEPAPER} VIBE, ` +
                    `but agent has ${stakeInfo.stakedAmount} VIBE`,
            };
        }
        return { valid: true };
    }
    /**
     * Determine stake tier from amount.
     */
    static getTier(stakeAmount) {
        if (stakeAmount >= types_1.StakeTier.PLATINUM)
            return types_1.StakeTier.PLATINUM;
        if (stakeAmount >= types_1.StakeTier.GOLD)
            return types_1.StakeTier.GOLD;
        if (stakeAmount >= types_1.StakeTier.SILVER)
            return types_1.StakeTier.SILVER;
        if (stakeAmount >= types_1.StakeTier.BRONZE)
            return types_1.StakeTier.BRONZE;
        return types_1.StakeTier.NONE;
    }
    /**
     * Get maximum number of agents for a tier.
     */
    static getMaxAgents(tier) {
        return TIER_CONFIG[tier]?.maxAgents ?? 0;
    }
    /**
     * Get discount percentage for a tier.
     */
    static getDiscount(tier) {
        return TIER_CONFIG[tier]?.discount ?? 0;
    }
    /**
     * Calculate reputation score from stake amount.
     * Formula from whitepaper: reputation = min(0.5 + (staked / 1000), 1.0)
     */
    static calculateReputation(stakeAmount) {
        return Math.min(0.5 + stakeAmount / 1000, 1.0);
    }
    /**
     * Clear stake info cache.
     */
    clearCache(agentId) {
        if (agentId) {
            this.cache.delete(agentId);
        }
        else {
            this.cache.clear();
        }
    }
}
exports.StakeChecker = StakeChecker;
/**
 * Minimum stake required for earning features (whitepaper rule).
 */
StakeChecker.MIN_STAKE_WHITEPAPER = 100; // Bronze tier
//# sourceMappingURL=stake-checker.js.map