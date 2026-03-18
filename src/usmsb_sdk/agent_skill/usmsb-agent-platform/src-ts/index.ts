/**
 * USMSB Agent Platform Skill
 *
 * A skill package for AI agents to interact with USMSB Platform.
 * Provides collaboration, marketplace, discovery, negotiation, workflow, and learning capabilities.
 *
 * Features:
 * - Self-registration (no Owner required for basic features)
 * - Owner binding for advanced features
 * - API Key management
 * - Tiered permissions based on stake
 *
 * @example
 * ```typescript
 * // Self-registration
 * import { AgentPlatform } from "usmsb-agent-platform";
 *
 * const result = await AgentPlatform.register(
 *   "My Agent",
 *   "A helpful assistant",
 *   ["python", "web"]
 * );
 *
 * console.log(result.agentId);  // agent-xxx
 * console.log(result.apiKey);   // usmsb_xxx_xxx
 *
 * // Using the platform
 * const platform = new AgentPlatform({
 *   apiKey: result.apiKey!,
 *   agentId: result.agentId!
 * });
 *
 * const response = await platform.call("帮我创建一个协作，目标是开发电商网站");
 * console.log(response);
 * ```
 */

export { AgentPlatform, PlatformConfig } from "./platform";
export { IntentParser } from "./intent-parser";
export { StakeChecker } from "./stake-checker";
export {
  RegistrationClient,
  RegistrationResult,
  BindingRequestResult,
  BindingStatus,
  APIKeyInfo,
} from "./registration";

export {
  ActionType,
  StakeTier,
  StakeInfo,
  Intent,
  PlatformResult,
  ErrorCode,
  ACTION_META,
  stakeInfoFromAmount,
  OrderStatus,
  OrderTerms,
  Order,
  OrderCreationResult,
  PoolCreationResult,
} from "./types";
