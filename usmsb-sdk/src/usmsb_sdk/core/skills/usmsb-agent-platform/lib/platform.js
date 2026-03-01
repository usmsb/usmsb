"use strict";
/**
 * Main AgentPlatform class for interacting with USMSB Platform.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.AgentPlatform = void 0;
const node_fetch_1 = __importDefault(require("node-fetch"));
const intent_parser_1 = require("./intent-parser");
const stake_checker_1 = require("./stake-checker");
const registration_1 = require("./registration");
const types_1 = require("./types");
/**
 * HTTP client for platform API calls.
 */
class PlatformClient {
    constructor(baseUrl, apiKey, agentId) {
        this.baseUrl = baseUrl.replace(/\/$/, "");
        this.apiKey = apiKey;
        this.agentId = agentId;
    }
    async get(path, params = {}) {
        const url = new URL(`${this.baseUrl}${path}`);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined) {
                url.searchParams.append(key, String(value));
            }
        });
        const response = await (0, node_fetch_1.default)(url.toString(), {
            method: "GET",
            headers: this.getHeaders(),
        });
        return this.handleResponse(response);
    }
    async post(path, body = {}) {
        const response = await (0, node_fetch_1.default)(`${this.baseUrl}${path}`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify(body),
        });
        return this.handleResponse(response);
    }
    getHeaders() {
        return {
            "X-API-Key": this.apiKey,
            "X-Agent-ID": this.agentId,
            "Content-Type": "application/json",
        };
    }
    async handleResponse(response) {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    }
    async getStakedAmount(agentId) {
        try {
            const data = await this.get(`/api/agents/${agentId}/stake`);
            return data?.active_stake ?? 0;
        }
        catch {
            return 0;
        }
    }
}
/**
 * Main class for interacting with USMSB Agent Platform.
 *
 * @example
 * ```typescript
 * import { AgentPlatform } from "usmsb-agent-platform";
 *
 * const platform = new AgentPlatform({
 *   apiKey: "usmsb_xxx_xxx",
 *   agentId: "agent-xxx"
 * });
 *
 * const result = await platform.call("帮我创建一个协作，目标是开发电商网站");
 * console.log(result);
 * ```
 */
class AgentPlatform {
    constructor(configOrApiKey, agentId, baseUrl) {
        if (typeof configOrApiKey === "string") {
            this.apiKey = configOrApiKey;
            this.agentId = agentId;
            this.baseUrl = baseUrl ?? "http://localhost:8000";
        }
        else {
            this.apiKey = configOrApiKey.apiKey;
            this.agentId = configOrApiKey.agentId;
            this.baseUrl = configOrApiKey.baseUrl ?? "http://localhost:8000";
        }
        this.intentParser = new intent_parser_1.IntentParser();
    }
    getClient() {
        if (!this.client) {
            this.client = new PlatformClient(this.baseUrl, this.apiKey, this.agentId);
        }
        return this.client;
    }
    async getStakeChecker() {
        if (!this.stakeChecker) {
            this.stakeChecker = new stake_checker_1.StakeChecker(this.getClient());
        }
        return this.stakeChecker;
    }
    /**
     * Execute a natural language request.
     */
    async call(request) {
        try {
            // 1. Parse intent from natural language
            const intent = this.intentParser.parse(request);
            const meta = types_1.ACTION_META[intent.action];
            // 2. Check stake if required
            if (meta.requiresStake) {
                const checker = await this.getStakeChecker();
                const { valid, error } = await checker.verifyStake(this.agentId, intent.action);
                if (!valid) {
                    return {
                        success: false,
                        error,
                        code: types_1.ErrorCode.INSUFFICIENT_STAKE,
                    };
                }
            }
            // 3. Execute action
            return await this.execute(intent.action, intent.parameters);
        }
        catch (e) {
            if (e.message?.startsWith("Cannot parse")) {
                return {
                    success: false,
                    error: e.message,
                    code: types_1.ErrorCode.PARSE_ERROR,
                };
            }
            return {
                success: false,
                error: e.message ?? "Unknown error",
                code: types_1.ErrorCode.INTERNAL_ERROR,
            };
        }
    }
    async execute(action, params) {
        const client = this.getClient();
        const meta = types_1.ACTION_META[action];
        try {
            let result;
            switch (meta.category) {
                case "collaboration":
                    result = await this.executeCollaboration(client, meta.action, params);
                    break;
                case "marketplace":
                    result = await this.executeMarketplace(client, meta.action, params);
                    break;
                case "discovery":
                    result = await this.executeDiscovery(client, meta.action, params);
                    break;
                case "negotiation":
                    result = await this.executeNegotiation(client, meta.action, params);
                    break;
                case "workflow":
                    result = await this.executeWorkflow(client, meta.action, params);
                    break;
                case "learning":
                    result = await this.executeLearning(client, meta.action, params);
                    break;
                default:
                    return {
                        success: false,
                        error: `Unknown category: ${meta.category}`,
                        code: types_1.ErrorCode.INTERNAL_ERROR,
                    };
            }
            return {
                success: true,
                result,
                message: `Action '${meta.action}' completed successfully`,
            };
        }
        catch (e) {
            return {
                success: false,
                error: e.message ?? "Execution failed",
                code: types_1.ErrorCode.INTERNAL_ERROR,
            };
        }
    }
    async executeCollaboration(client, action, params) {
        const path = `/api/collaboration/${action}`;
        if (action === "list") {
            return client.get(path, params);
        }
        return client.post(path, params);
    }
    async executeMarketplace(client, action, params) {
        const path = `/api/marketplace/${action}`;
        if (["find_work", "find_workers"].includes(action)) {
            return client.get(path, params);
        }
        return client.post(path, params);
    }
    async executeDiscovery(client, action, params) {
        const path = `/api/discovery/${action}`;
        if (action === "recommend") {
            return client.post(path, params);
        }
        return client.get(path, params);
    }
    async executeNegotiation(client, action, params) {
        return client.post(`/api/negotiation/${action}`, params);
    }
    async executeWorkflow(client, action, params) {
        const path = `/api/workflow/${action}`;
        if (action === "list") {
            return client.get(path, params);
        }
        return client.post(path, params);
    }
    async executeLearning(client, action, params) {
        return client.get(`/api/learning/${action}`, params);
    }
    /**
     * Get stake information for the current agent.
     */
    async getStakeInfo() {
        const checker = await this.getStakeChecker();
        return checker.getStakeInfo(this.agentId);
    }
    // Convenience methods
    async createCollaboration(goal) {
        return this.call(`创建协作，目标是${goal}`);
    }
    async joinCollaboration(collabId) {
        return this.call(`加入协作 ${collabId}`);
    }
    async publishService(name, price, skills) {
        const skillsStr = skills?.join(",") ?? "";
        return this.call(`发布服务 ${name}，价格 ${price} VIBE，技能 ${skillsStr}`);
    }
    async findWork(skill) {
        if (skill) {
            return this.call(`找 ${skill} 工作`);
        }
        return this.call("找工作");
    }
    async findWorkers(skills) {
        return this.call(`找会 ${skills.join(",")} 的Worker`);
    }
    async discoverAgents(capability) {
        return this.call(`找有 ${capability} 能力的Agent`);
    }
    // === Registration and Binding Methods ===
    /**
     * Self-register a new Agent (no Owner required).
     * This is a static method that can be called without an existing API key.
     */
    static async register(name, description = "", capabilities = [], baseUrl = "http://localhost:8000") {
        const client = new registration_1.RegistrationClient(baseUrl);
        return client.register(name, description, capabilities);
    }
    /**
     * Request Owner binding.
     */
    async requestBinding(message = "") {
        const client = new registration_1.RegistrationClient(this.baseUrl);
        return client.requestBinding(this.apiKey, message);
    }
    /**
     * Get Agent's binding status.
     */
    async getBindingStatus() {
        const client = new registration_1.RegistrationClient(this.baseUrl);
        return client.getBindingStatus(this.apiKey);
    }
    // === Profile Management ===
    /**
     * Get Agent's detailed profile information.
     */
    async getProfile() {
        const client = this.getClient();
        try {
            const result = await client.get("/api/agents/profile");
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Update Agent's profile information.
     */
    async updateProfile(name, description, capabilities) {
        const client = this.getClient();
        const data = {};
        if (name !== undefined)
            data.name = name;
        if (description !== undefined)
            data.description = description;
        if (capabilities !== undefined)
            data.capabilities = capabilities;
        try {
            const result = await client.post("/api/agents/profile", data);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    // === API Key Management ===
    /**
     * List all API Keys for this Agent.
     */
    async listApiKeys() {
        const client = this.getClient();
        try {
            const result = await client.get("/api/agents/api-keys");
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Create a new API Key.
     */
    async createApiKey(name = "", expiresInDays = 365) {
        const client = this.getClient();
        try {
            const result = await client.post("/api/agents/api-keys", {
                name,
                expires_in_days: expiresInDays,
            });
            return {
                success: true,
                result,
                message: "API Key created. Save it now - it won't be shown again!",
            };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Revoke an API Key.
     */
    async revokeApiKey(keyId) {
        const client = this.getClient();
        try {
            const result = await client.post(`/api/agents/api-keys/${keyId}/revoke`, {});
            return { success: true, result, message: "API Key revoked" };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Renew an API Key (extend expiration).
     */
    async renewApiKey(keyId, extendsDays = 365) {
        const client = this.getClient();
        try {
            const result = await client.post(`/api/agents/api-keys/${keyId}/renew`, {
                extends_days: extendsDays,
            });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    // === Owner Info ===
    /**
     * Get information about the bound Owner.
     */
    async getOwnerInfo() {
        const client = this.getClient();
        try {
            const result = await client.get("/api/agents/owner");
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
}
exports.AgentPlatform = AgentPlatform;
exports.default = AgentPlatform;
//# sourceMappingURL=platform.js.map