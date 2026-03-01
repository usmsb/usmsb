/**
 * Stake checker for verifying stake requirements.
 */
import { ActionType, StakeInfo, StakeTier } from "./types";
/**
 * Stake checker class.
 */
export declare class StakeChecker {
    private client;
    private cache;
    /**
     * Minimum stake required for earning features (whitepaper rule).
     */
    static readonly MIN_STAKE_WHITEPAPER = 100;
    constructor(client?: any);
    /**
     * Get stake information for an agent.
     */
    getStakeInfo(agentId: string): Promise<StakeInfo>;
    /**
     * Verify if an agent has sufficient stake for an action.
     */
    verifyStake(agentId: string, action: ActionType): Promise<{
        valid: boolean;
        error?: string;
    }>;
    /**
     * Determine stake tier from amount.
     */
    static getTier(stakeAmount: number): StakeTier;
    /**
     * Get maximum number of agents for a tier.
     */
    static getMaxAgents(tier: StakeTier): number;
    /**
     * Get discount percentage for a tier.
     */
    static getDiscount(tier: StakeTier): number;
    /**
     * Calculate reputation score from stake amount.
     * Formula from whitepaper: reputation = min(0.5 + (staked / 1000), 1.0)
     */
    static calculateReputation(stakeAmount: number): number;
    /**
     * Clear stake info cache.
     */
    clearCache(agentId?: string): void;
}
//# sourceMappingURL=stake-checker.d.ts.map