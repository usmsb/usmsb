/**
 * Main AgentPlatform class for interacting with USMSB Platform.
 */
import { RegistrationResult, BindingRequestResult, BindingStatus } from "./registration";
import { PlatformResult, StakeInfo } from "./types";
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
}
export default AgentPlatform;
//# sourceMappingURL=platform.d.ts.map