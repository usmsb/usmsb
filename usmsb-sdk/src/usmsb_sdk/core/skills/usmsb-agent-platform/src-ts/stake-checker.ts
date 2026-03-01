/**
 * Stake checker for verifying stake requirements.
 */

import { ActionType, StakeInfo, StakeTier, stakeInfoFromAmount, ACTION_META } from "./types";

/**
 * Tier configuration.
 */
const TIER_CONFIG: Record<StakeTier, { min: number; maxAgents: number; discount: number }> = {
  [StakeTier.NONE]: { min: 0, maxAgents: 0, discount: 0 },
  [StakeTier.BRONZE]: { min: 100, maxAgents: 1, discount: 0 },
  [StakeTier.SILVER]: { min: 1000, maxAgents: 3, discount: 5 },
  [StakeTier.GOLD]: { min: 5000, maxAgents: 10, discount: 10 },
  [StakeTier.PLATINUM]: { min: 10000, maxAgents: 50, discount: 20 },
};

/**
 * Stake checker class.
 */
export class StakeChecker {
  private client: any;
  private cache: Map<string, StakeInfo> = new Map();

  /**
   * Minimum stake required for earning features (whitepaper rule).
   */
  static readonly MIN_STAKE_WHITEPAPER = 100; // Bronze tier

  constructor(client?: any) {
    this.client = client;
  }

  /**
   * Get stake information for an agent.
   */
  async getStakeInfo(agentId: string): Promise<StakeInfo> {
    // Check cache first
    if (this.cache.has(agentId)) {
      return this.cache.get(agentId)!;
    }

    // Fetch from platform if client available
    let stakedAmount = 0;
    if (this.client && typeof this.client.getStakedAmount === "function") {
      stakedAmount = await this.client.getStakedAmount(agentId);
    }

    const info = stakeInfoFromAmount(agentId, stakedAmount);
    this.cache.set(agentId, info);
    return info;
  }

  /**
   * Verify if an agent has sufficient stake for an action.
   */
  async verifyStake(agentId: string, action: ActionType): Promise<{ valid: boolean; error?: string }> {
    const meta = ACTION_META[action];

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
  static getTier(stakeAmount: number): StakeTier {
    if (stakeAmount >= StakeTier.PLATINUM) return StakeTier.PLATINUM;
    if (stakeAmount >= StakeTier.GOLD) return StakeTier.GOLD;
    if (stakeAmount >= StakeTier.SILVER) return StakeTier.SILVER;
    if (stakeAmount >= StakeTier.BRONZE) return StakeTier.BRONZE;
    return StakeTier.NONE;
  }

  /**
   * Get maximum number of agents for a tier.
   */
  static getMaxAgents(tier: StakeTier): number {
    return TIER_CONFIG[tier]?.maxAgents ?? 0;
  }

  /**
   * Get discount percentage for a tier.
   */
  static getDiscount(tier: StakeTier): number {
    return TIER_CONFIG[tier]?.discount ?? 0;
  }

  /**
   * Calculate reputation score from stake amount.
   * Formula from whitepaper: reputation = min(0.5 + (staked / 1000), 1.0)
   */
  static calculateReputation(stakeAmount: number): number {
    return Math.min(0.5 + stakeAmount / 1000, 1.0);
  }

  /**
   * Clear stake info cache.
   */
  clearCache(agentId?: string): void {
    if (agentId) {
      this.cache.delete(agentId);
    } else {
      this.cache.clear();
    }
  }
}
