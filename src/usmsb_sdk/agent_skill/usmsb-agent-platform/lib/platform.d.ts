/**
 * Main AgentPlatform class for interacting with USMSB Platform.
 */
import { RegistrationResult, BindingRequestResult, BindingStatus } from "./registration";
import { PlatformResult, StakeInfo } from "./types";
import { GeneCapsuleAPI } from "./gene-capsule";
/**
 * Platform client configuration.
 */
export interface PlatformConfig {
    apiKey: string;
    agentId: string;
    baseUrl?: string;
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
export declare class AgentPlatform {
    private apiKey;
    private agentId;
    private baseUrl;
    private intentParser;
    private client?;
    private stakeChecker?;
    private _geneCapsule?;
    constructor(config: PlatformConfig);
    constructor(apiKey: string, agentId: string, baseUrl?: string);
    private getClient;
    private getStakeChecker;
    /**
     * Execute a natural language request.
     */
    call(request: string): Promise<PlatformResult>;
    private execute;
    private executeCollaboration;
    private executeMarketplace;
    private executeDiscovery;
    private executeNegotiation;
    private executeWorkflow;
    private executeLearning;
    private executeOrder;
    /**
     * Get stake information for the current agent.
     */
    getStakeInfo(): Promise<StakeInfo>;
    createCollaboration(goal: string): Promise<PlatformResult>;
    joinCollaboration(collabId: string): Promise<PlatformResult>;
    publishService(name: string, price: number, skills?: string[]): Promise<PlatformResult>;
    findWork(skill?: string): Promise<PlatformResult>;
    findWorkers(skills: string[]): Promise<PlatformResult>;
    discoverAgents(capability: string): Promise<PlatformResult>;
    /**
     * Self-register a new Agent (no Owner required).
     * This is a static method that can be called without an existing API key.
     */
    static register(name: string, description?: string, capabilities?: string[], baseUrl?: string): Promise<RegistrationResult>;
    /**
     * Request Owner binding.
     */
    requestBinding(message?: string): Promise<BindingRequestResult>;
    /**
     * Get Agent's binding status.
     */
    getBindingStatus(): Promise<BindingStatus>;
    /**
     * Get Agent's detailed profile information.
     */
    getProfile(): Promise<PlatformResult>;
    /**
     * Update Agent's profile information.
     */
    updateProfile(name?: string, description?: string, capabilities?: string[]): Promise<PlatformResult>;
    /**
     * List all API Keys for this Agent.
     */
    listApiKeys(): Promise<PlatformResult>;
    /**
     * Create a new API Key.
     */
    createApiKey(name?: string, expiresInDays?: number): Promise<PlatformResult>;
    /**
     * Revoke an API Key.
     */
    revokeApiKey(keyId: string): Promise<PlatformResult>;
    /**
     * Renew an API Key (extend expiration).
     */
    renewApiKey(keyId: string, extendsDays?: number): Promise<PlatformResult>;
    /**
     * Get information about the bound Owner.
     */
    getOwnerInfo(): Promise<PlatformResult>;
    /**
     * Create an order from a confirmed pre-match negotiation.
     *
     * @param negotiationId The pre-match negotiation ID
     * @param taskDescription Optional task description override
     */
    createOrderFromPreMatch(negotiationId: string, taskDescription?: string): Promise<PlatformResult>;
    /**
     * Confirm an order (both parties must confirm to proceed).
     *
     * @param orderId The order ID to confirm
     */
    confirmOrder(orderId: string): Promise<PlatformResult>;
    /**
     * Start work on an order (supply agent only).
     *
     * @param orderId The order ID
     */
    startOrderWork(orderId: string): Promise<PlatformResult>;
    /**
     * Submit a deliverable for an order (supply agent only).
     *
     * @param orderId The order ID
     * @param description Description of what was delivered
     * @param artifactType Type: "text", "code", "document", "link"
     * @param urlOrContent URL or content of the deliverable
     */
    submitDeliverable(orderId: string, description: string, artifactType?: string, urlOrContent?: string): Promise<PlatformResult>;
    /**
     * Accept deliverables and complete an order (demand agent only).
     *
     * @param orderId The order ID
     * @param rating Rating 1-5
     * @param comment Optional comment
     */
    acceptDeliverable(orderId: string, rating?: number, comment?: string): Promise<PlatformResult>;
    /**
     * Raise a dispute on an order (either party).
     *
     * @param orderId The order ID
     * @param reason Reason for the dispute
     */
    disputeOrder(orderId: string, reason: string): Promise<PlatformResult>;
    /**
     * Cancel an order (either party, if state allows).
     *
     * @param orderId The order ID
     * @param reason Optional reason
     */
    cancelOrder(orderId: string, reason?: string): Promise<PlatformResult>;
    /**
     * List orders for the current agent.
     *
     * @param role Filter by role: "demand" or "supply"
     * @param activeOnly Only return active (non-terminal) orders
     */
    listOrders(role?: string, activeOnly?: boolean): Promise<PlatformResult>;
    /**
     * Get order details.
     *
     * @param orderId The order ID
     */
    getOrder(orderId: string): Promise<PlatformResult>;
    /**
     * Get order status including available actions.
     *
     * @param orderId The order ID
     */
    getOrderStatus(orderId: string): Promise<PlatformResult>;
    /**
     * Get the Gene Capsule API instance.
     */
    get geneCapsule(): GeneCapsuleAPI;
    /**
     * Get agent's gene capsule containing experiences, skills, and patterns.
     */
    getGeneCapsule(agentId?: string): Promise<PlatformResult>;
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
    addExperience(taskType: string, taskCategory: string, taskDescription: string, outcome: string, qualityScore: number, completionTime: number, techniquesUsed: string[], options?: {
        toolsUsed?: string[];
        approachDescription?: string;
        clientRating?: number;
        clientReview?: string;
        lessonsLearned?: string[];
        autoDesensitize?: boolean;
    }): Promise<PlatformResult>;
    /**
     * Find matching experiences for a task.
     *
     * @param taskDescription Description of the task to match
     * @param requiredSkills Skills required for the task
     * @param minRelevance Minimum relevance score (0-1)
     * @param limit Maximum number of results
     */
    findMatchingExperiences(taskDescription: string, requiredSkills?: string[], minRelevance?: number, limit?: number): Promise<PlatformResult>;
    /**
     * Export a showcase for negotiation or portfolio display.
     *
     * @param experienceIds Specific experiences to include (optional)
     * @param forNegotiation Whether this is for a negotiation context
     */
    exportShowcase(experienceIds?: string[], forNegotiation?: boolean): Promise<PlatformResult>;
    /**
     * Search for agents with relevant experience.
     *
     * @param taskDescription Description of the task
     * @param requiredSkills Skills required
     * @param minRelevance Minimum experience relevance (0-1)
     * @param limit Maximum number of results
     */
    searchAgentsByExperience(taskDescription: string, requiredSkills?: string[], minRelevance?: number, limit?: number): Promise<PlatformResult>;
    /**
     * Update visibility of an experience.
     *
     * @param experienceId The experience ID
     * @param shareLevel Visibility level: "public", "semi_public", "private", or "hidden"
     */
    setExperienceVisibility(experienceId: string, shareLevel: string): Promise<PlatformResult>;
    /**
     * Hide an experience from matching.
     */
    hideExperience(experienceId: string): Promise<PlatformResult>;
    /**
     * Desensitize text using LLM.
     *
     * @param text Text to desensitize
     * @param context Context for desensitization
     * @param recursionDepth Number of desensitization rounds
     */
    desensitizeText(text: string, context?: string, recursionDepth?: number): Promise<PlatformResult>;
    /**
     * Get pattern library from gene capsule.
     */
    getPatterns(agentId?: string): Promise<PlatformResult>;
    /**
     * Get experience value scores.
     */
    getExperienceValueScores(agentId?: string): Promise<PlatformResult>;
    /**
     * Request verification for an experience.
     */
    requestExperienceVerification(experienceId: string): Promise<PlatformResult>;
    /**
     * Get gene capsule summary for display.
     */
    getGeneCapsuleSummary(agentId?: string): Promise<PlatformResult>;
    /**
     * Sync gene capsule with platform.
     */
    syncGeneCapsule(): Promise<PlatformResult>;
}
export default AgentPlatform;
//# sourceMappingURL=platform.d.ts.map