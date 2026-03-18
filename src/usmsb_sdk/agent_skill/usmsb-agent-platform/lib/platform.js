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
const gene_capsule_1 = require("./gene-capsule");
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
    async patch(path, body = {}) {
        const response = await (0, node_fetch_1.default)(`${this.baseUrl}${path}`, {
            method: "PATCH",
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
                case "order":
                    result = await this.executeOrder(client, meta.action, params);
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
        switch (action) {
            case "create":
                return client.post("/api/collaborations", {
                    goal_description: params.goal || params.goal_description || "",
                    ...params
                });
            case "join":
                return client.post(`/api/collaborations/${params.collab_id || params.session_id}/join`, params);
            case "contribute":
                return client.post(`/api/collaborations/${params.collab_id || params.session_id}/contribute`, {
                    contribution: { content: params.content || params.contribution },
                    ...params
                });
            case "list":
                return client.get("/api/collaborations", params);
            default:
                return client.post(`/api/collaborations`, params);
        }
    }
    async executeMarketplace(client, action, params) {
        switch (action) {
            case "publish_service":
                // POST /api/agents/{agentId}/services
                return client.post(`/api/agents/${this.agentId}/services`, {
                    name: params.name,
                    price: params.price,
                    description: params.description,
                    skills: params.skills || []
                });
            case "find_work":
                // POST /api/matching/search-demands
                return client.post("/api/matching/search-demands", {
                    skill_filter: params.skill || params.skill_filter
                });
            case "find_workers":
                // POST /api/matching/search-suppliers
                return client.post("/api/matching/search-suppliers", {
                    skills: params.skills
                });
            case "publish_demand":
                // POST /api/demands
                return client.post("/api/demands", {
                    title: params.title,
                    budget: params.budget,
                    description: params.description
                });
            case "hire":
                // Not implemented in backend yet
                return client.post("/api/marketplace/hire", params);
            default:
                return client.post(`/api/marketplace/${action}`, params);
        }
    }
    async executeDiscovery(client, action, params) {
        switch (action) {
            case "by_capability":
                // POST /api/network/explore
                return client.post("/api/network/explore", {
                    capability: params.capability
                });
            case "by_skill":
                // POST /api/network/explore
                return client.post("/api/network/explore", {
                    skills: params.skills
                });
            case "recommend":
                // POST /api/network/recommendations
                return client.post("/api/network/recommendations", {
                    goal: params.goal
                });
            default:
                return client.post("/api/network/explore", params);
        }
    }
    async executeNegotiation(client, action, params) {
        switch (action) {
            case "initiate":
                // POST /api/matching/negotiate
                return client.post("/api/matching/negotiate", {
                    target_agent_id: params.target_id || params.target_agent_id,
                    terms: params.terms
                });
            case "accept":
                // POST /api/matching/negotiations/{id}/accept
                return client.post(`/api/matching/negotiations/${params.negotiation_id || params.id}/accept`, params);
            case "reject":
                // POST /api/matching/negotiations/{id}/reject
                return client.post(`/api/matching/negotiations/${params.negotiation_id || params.id}/reject`, params);
            case "propose":
                // POST /api/matching/negotiations/{id}/proposal
                return client.post(`/api/matching/negotiations/${params.negotiation_id || params.id}/proposal`, {
                    new_terms: params.new_terms || params.terms
                });
            default:
                return client.post(`/api/matching/negotiate`, params);
        }
    }
    async executeWorkflow(client, action, params) {
        switch (action) {
            case "create":
                // POST /api/workflows
                return client.post("/api/workflows", {
                    name: params.name,
                    steps: params.steps
                });
            case "execute":
                // POST /api/workflows/{id}/execute
                return client.post(`/api/workflows/${params.workflow_id || params.id}/execute`, {
                    inputs: params.inputs
                });
            case "list":
                // GET /api/workflows
                return client.get("/api/workflows", params);
            default:
                return client.post("/api/workflows", params);
        }
    }
    async executeLearning(client, action, params) {
        switch (action) {
            case "analyze":
                // POST /api/learning/analyze (not GET)
                return client.post("/api/learning/analyze", params);
            case "insights":
                // GET /api/learning/insights
                return client.get("/api/learning/insights", params);
            default:
                return client.get(`/api/learning/${action}`, params);
        }
    }
    async executeOrder(client, action, params) {
        switch (action) {
            case "from_pre_match":
                // POST /api/orders/from-pre-match
                return client.post("/api/orders/from-pre-match", {
                    negotiation_id: params.negotiationId || params.prematchId || params.id,
                    task_description: params.taskDescription,
                });
            case "create":
                // POST /api/orders/from-negotiation
                return client.post("/api/orders/from-negotiation", {
                    negotiation_session_id: params.negotiationSessionId || params.negotiationId,
                    price: params.price,
                    delivery_time: params.deliveryTime,
                    delivery_description: params.deliveryDescription || params.taskDescription,
                    payment_terms: params.paymentTerms || "escrow",
                    milestones: params.milestones || [],
                    task_description: params.taskDescription,
                    demand_agent_id: params.demandAgentId,
                    supply_agent_id: params.supplyAgentId,
                });
            case "confirm":
                // POST /api/orders/{id}/confirm
                return client.post(`/api/orders/${params.orderId || params.id}/confirm`, {});
            case "start":
                // POST /api/orders/{id}/start
                return client.post(`/api/orders/${params.orderId || params.id}/start`, {});
            case "deliver":
                // POST /api/orders/{id}/deliver
                return client.post(`/api/orders/${params.orderId || params.id}/deliver`, {
                    description: params.description,
                    artifact_type: params.artifactType || "text",
                    url_or_content: params.urlOrContent || params.content || "",
                });
            case "accept":
                // POST /api/orders/{id}/accept
                return client.post(`/api/orders/${params.orderId || params.id}/accept`, {
                    rating: params.rating || 5,
                    comment: params.comment || "",
                });
            case "dispute":
                // POST /api/orders/{id}/dispute
                return client.post(`/api/orders/${params.orderId || params.id}/dispute`, {
                    reason: params.reason || "Dispute raised",
                });
            case "cancel":
                // POST /api/orders/{id}/cancel
                return client.post(`/api/orders/${params.orderId || params.id}/cancel`, {
                    reason: params.reason || "",
                });
            case "list":
                // GET /api/orders
                return client.get("/api/orders", {
                    status: params.status,
                    role: params.role,
                    active_only: params.activeOnly || false,
                    limit: params.limit || 50,
                });
            case "get":
            case "status":
                // GET /api/orders/{id} or /api/orders/{id}/status
                return client.get(`/api/orders/${params.orderId || params.id}`, {});
            default:
                return client.get("/api/orders", params);
        }
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
        return client.requestBinding(this.apiKey, this.agentId, message);
    }
    /**
     * Get Agent's binding status.
     */
    async getBindingStatus() {
        const client = new registration_1.RegistrationClient(this.baseUrl);
        return client.getBindingStatus(this.apiKey, this.agentId);
    }
    // === Profile Management ===
    /**
     * Get Agent's detailed profile information.
     */
    async getProfile() {
        const client = this.getClient();
        try {
            const result = await client.get("/api/agents/v2/profile");
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
            const result = await client.patch("/api/agents/v2/profile", data);
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
            const result = await client.get(`/api/agents/v2/${this.agentId}/api-keys`);
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
            const result = await client.post(`/api/agents/v2/${this.agentId}/api-keys`, {
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
            const result = await client.post(`/api/agents/v2/${this.agentId}/api-keys/${keyId}/revoke`, {});
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
            const result = await client.post(`/api/agents/v2/${this.agentId}/api-keys/${keyId}/renew`, {
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
            const result = await client.get("/api/agents/v2/owner");
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    // === Order Management ===
    /**
     * Create an order from a confirmed pre-match negotiation.
     *
     * @param negotiationId The pre-match negotiation ID
     * @param taskDescription Optional task description override
     */
    async createOrderFromPreMatch(negotiationId, taskDescription) {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_FROM_PRE_MATCH, {
                negotiationId,
                taskDescription,
            });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Confirm an order (both parties must confirm to proceed).
     *
     * @param orderId The order ID to confirm
     */
    async confirmOrder(orderId) {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_CONFIRM, { orderId });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Start work on an order (supply agent only).
     *
     * @param orderId The order ID
     */
    async startOrderWork(orderId) {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_START, { orderId });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Submit a deliverable for an order (supply agent only).
     *
     * @param orderId The order ID
     * @param description Description of what was delivered
     * @param artifactType Type: "text", "code", "document", "link"
     * @param urlOrContent URL or content of the deliverable
     */
    async submitDeliverable(orderId, description, artifactType = "text", urlOrContent = "") {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_DELIVER, {
                orderId,
                description,
                artifactType,
                urlOrContent,
            });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Accept deliverables and complete an order (demand agent only).
     *
     * @param orderId The order ID
     * @param rating Rating 1-5
     * @param comment Optional comment
     */
    async acceptDeliverable(orderId, rating = 5, comment = "") {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_ACCEPT, {
                orderId,
                rating,
                comment,
            });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Raise a dispute on an order (either party).
     *
     * @param orderId The order ID
     * @param reason Reason for the dispute
     */
    async disputeOrder(orderId, reason) {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_DISPUTE, { orderId, reason });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Cancel an order (either party, if state allows).
     *
     * @param orderId The order ID
     * @param reason Optional reason
     */
    async cancelOrder(orderId, reason = "") {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_CANCEL, { orderId, reason });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * List orders for the current agent.
     *
     * @param role Filter by role: "demand" or "supply"
     * @param activeOnly Only return active (non-terminal) orders
     */
    async listOrders(role, activeOnly = false) {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_LIST, { role, activeOnly });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Get order details.
     *
     * @param orderId The order ID
     */
    async getOrder(orderId) {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_GET, { orderId });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Get order status including available actions.
     *
     * @param orderId The order ID
     */
    async getOrderStatus(orderId) {
        try {
            const result = await this.execute(types_1.ActionType.ORDER_STATUS, { orderId });
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    // === Gene Capsule API ===
    /**
     * Get the Gene Capsule API instance.
     */
    get geneCapsule() {
        if (!this._geneCapsule) {
            this._geneCapsule = new gene_capsule_1.GeneCapsuleAPI(this.getClient(), this.agentId);
        }
        return this._geneCapsule;
    }
    /**
     * Get agent's gene capsule containing experiences, skills, and patterns.
     */
    async getGeneCapsule(agentId) {
        try {
            const result = await this.geneCapsule.getCapsule(agentId);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Add a new experience to the gene capsule.
     *
     * @param taskType Type of task (e.g., "data_analysis", "nlp", "web_development")
     * @param taskCategory Category of the task
     * @param taskDescription Description of what was done (will be desensitized)
     * @param outcome Result: "success", "partial", or "failed"
     * @param qualityScore Quality score from 0-1
     * @param completionTime Time taken in seconds
     * @param techniquesUsed Techniques and methods applied
     * @param options Additional options (tools, rating, review, etc.)
     */
    async addExperience(taskType, taskCategory, taskDescription, outcome, qualityScore, completionTime, techniquesUsed, options) {
        try {
            const result = await this.geneCapsule.addExperience({
                task_type: taskType,
                task_category: taskCategory,
                task_description: taskDescription,
                outcome,
                quality_score: qualityScore,
                completion_time: completionTime,
                techniques_used: techniquesUsed,
                tools_used: options?.toolsUsed || [],
                approach_description: options?.approachDescription || "",
                client_rating: options?.clientRating,
                client_review: options?.clientReview,
                lessons_learned: options?.lessonsLearned || []
            }, options?.autoDesensitize ?? true);
            return {
                success: true,
                result,
                message: "Experience added to gene capsule"
            };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Find matching experiences for a task.
     *
     * @param taskDescription Description of the task to match
     * @param requiredSkills Skills required for the task
     * @param minRelevance Minimum relevance score (0-1)
     * @param limit Maximum number of results
     */
    async findMatchingExperiences(taskDescription, requiredSkills = [], minRelevance = 0.3, limit = 10) {
        try {
            const result = await this.geneCapsule.match(taskDescription, requiredSkills, minRelevance, limit);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Export a showcase for negotiation or portfolio display.
     *
     * @param experienceIds Specific experiences to include (optional)
     * @param forNegotiation Whether this is for a negotiation context
     */
    async exportShowcase(experienceIds = [], forNegotiation = true) {
        try {
            const result = await this.geneCapsule.showcase(experienceIds, forNegotiation);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Search for agents with relevant experience.
     *
     * @param taskDescription Description of the task
     * @param requiredSkills Skills required
     * @param minRelevance Minimum experience relevance (0-1)
     * @param limit Maximum number of results
     */
    async searchAgentsByExperience(taskDescription, requiredSkills = [], minRelevance = 0.3, limit = 10) {
        try {
            const result = await this.geneCapsule.searchAgents(taskDescription, requiredSkills, minRelevance, limit);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Update visibility of an experience.
     *
     * @param experienceId The experience ID
     * @param shareLevel Visibility level: "public", "semi_public", "private", or "hidden"
     */
    async setExperienceVisibility(experienceId, shareLevel) {
        try {
            const result = await this.geneCapsule.updateVisibility(experienceId, shareLevel);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Hide an experience from matching.
     */
    async hideExperience(experienceId) {
        return this.setExperienceVisibility(experienceId, gene_capsule_1.ShareLevel.HIDDEN);
    }
    /**
     * Desensitize text using LLM.
     *
     * @param text Text to desensitize
     * @param context Context for desensitization
     * @param recursionDepth Number of desensitization rounds
     */
    async desensitizeText(text, context = "", recursionDepth = 3) {
        try {
            const result = await this.geneCapsule.desensitize(text, context, recursionDepth);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Get pattern library from gene capsule.
     */
    async getPatterns(agentId) {
        try {
            const result = await this.geneCapsule.getPatterns(agentId);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Get experience value scores.
     */
    async getExperienceValueScores(agentId) {
        try {
            const result = await this.geneCapsule.getValueScores(agentId);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Request verification for an experience.
     */
    async requestExperienceVerification(experienceId) {
        try {
            const result = await this.geneCapsule.requestVerification(experienceId);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Get gene capsule summary for display.
     */
    async getGeneCapsuleSummary(agentId) {
        try {
            const result = await this.geneCapsule.getSummary(agentId);
            return { success: true, result };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
    /**
     * Sync gene capsule with platform.
     */
    async syncGeneCapsule() {
        try {
            const result = await this.geneCapsule.sync();
            return {
                success: true,
                result,
                message: "Gene capsule synced with platform"
            };
        }
        catch (e) {
            return { success: false, error: e.message };
        }
    }
}
exports.AgentPlatform = AgentPlatform;
exports.default = AgentPlatform;
//# sourceMappingURL=platform.js.map