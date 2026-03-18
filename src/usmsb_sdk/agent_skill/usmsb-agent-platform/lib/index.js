"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.OrderStatus = exports.stakeInfoFromAmount = exports.ACTION_META = exports.ErrorCode = exports.StakeTier = exports.ActionType = exports.RegistrationClient = exports.StakeChecker = exports.IntentParser = exports.AgentPlatform = void 0;
var platform_1 = require("./platform");
Object.defineProperty(exports, "AgentPlatform", { enumerable: true, get: function () { return platform_1.AgentPlatform; } });
var intent_parser_1 = require("./intent-parser");
Object.defineProperty(exports, "IntentParser", { enumerable: true, get: function () { return intent_parser_1.IntentParser; } });
var stake_checker_1 = require("./stake-checker");
Object.defineProperty(exports, "StakeChecker", { enumerable: true, get: function () { return stake_checker_1.StakeChecker; } });
var registration_1 = require("./registration");
Object.defineProperty(exports, "RegistrationClient", { enumerable: true, get: function () { return registration_1.RegistrationClient; } });
var types_1 = require("./types");
Object.defineProperty(exports, "ActionType", { enumerable: true, get: function () { return types_1.ActionType; } });
Object.defineProperty(exports, "StakeTier", { enumerable: true, get: function () { return types_1.StakeTier; } });
Object.defineProperty(exports, "ErrorCode", { enumerable: true, get: function () { return types_1.ErrorCode; } });
Object.defineProperty(exports, "ACTION_META", { enumerable: true, get: function () { return types_1.ACTION_META; } });
Object.defineProperty(exports, "stakeInfoFromAmount", { enumerable: true, get: function () { return types_1.stakeInfoFromAmount; } });
Object.defineProperty(exports, "OrderStatus", { enumerable: true, get: function () { return types_1.OrderStatus; } });
//# sourceMappingURL=index.js.map