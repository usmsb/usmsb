/**
 * Main AgentPlatform class for interacting with USMSB Platform.
 */

import fetch, { RequestInit } from "node-fetch";
import { IntentParser } from "./intent-parser";
import { StakeChecker } from "./stake-checker";
import {
  RegistrationClient,
  RegistrationResult,
  BindingRequestResult,
  BindingStatus,
} from "./registration";
import {
  ActionType,
  PlatformResult,
  StakeInfo,
  ErrorCode,
  ACTION_META,
  stakeInfoFromAmount,
} from "./types";

/**
 * Platform client configuration.
 */
export interface PlatformConfig {
  apiKey: string;
  agentId: string;
  baseUrl?: string;
}

/**
 * HTTP client for platform API calls.
 */
class PlatformClient {
  private baseUrl: string;
  private apiKey: string;
  private agentId: string;

  constructor(baseUrl: string, apiKey: string, agentId: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiKey = apiKey;
    this.agentId = agentId;
  }

  async get(path: string, params: Record<string, any> = {}): Promise<any> {
    const url = new URL(`${this.baseUrl}${path}`);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });

    const response = await fetch(url.toString(), {
      method: "GET",
      headers: this.getHeaders(),
    });

    return this.handleResponse(response);
  }

  async post(path: string, body: Record<string, any> = {}): Promise<any> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(body),
    });

    return this.handleResponse(response);
  }

  private getHeaders(): Record<string, string> {
    return {
      "X-API-Key": this.apiKey,
      "X-Agent-ID": this.agentId,
      "Content-Type": "application/json",
    };
  }

  private async handleResponse(response: any): Promise<any> {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
  }

  async getStakedAmount(agentId: string): Promise<number> {
    try {
      const data = await this.get(`/api/agents/${agentId}/stake`);
      return data?.active_stake ?? 0;
    } catch {
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
export class AgentPlatform {
  private apiKey: string;
  private agentId: string;
  private baseUrl: string;
  private intentParser: IntentParser;
  private client?: PlatformClient;
  private stakeChecker?: StakeChecker;

  constructor(config: PlatformConfig);
  constructor(apiKey: string, agentId: string, baseUrl?: string);
  constructor(configOrApiKey: PlatformConfig | string, agentId?: string, baseUrl?: string) {
    if (typeof configOrApiKey === "string") {
      this.apiKey = configOrApiKey;
      this.agentId = agentId!;
      this.baseUrl = baseUrl ?? "http://localhost:8000";
    } else {
      this.apiKey = configOrApiKey.apiKey;
      this.agentId = configOrApiKey.agentId;
      this.baseUrl = configOrApiKey.baseUrl ?? "http://localhost:8000";
    }

    this.intentParser = new IntentParser();
  }

  private getClient(): PlatformClient {
    if (!this.client) {
      this.client = new PlatformClient(this.baseUrl, this.apiKey, this.agentId);
    }
    return this.client;
  }

  private async getStakeChecker(): Promise<StakeChecker> {
    if (!this.stakeChecker) {
      this.stakeChecker = new StakeChecker(this.getClient());
    }
    return this.stakeChecker;
  }

  /**
   * Execute a natural language request.
   */
  async call(request: string): Promise<PlatformResult> {
    try {
      // 1. Parse intent from natural language
      const intent = this.intentParser.parse(request);
      const meta = ACTION_META[intent.action];

      // 2. Check stake if required
      if (meta.requiresStake) {
        const checker = await this.getStakeChecker();
        const { valid, error } = await checker.verifyStake(this.agentId, intent.action);
        if (!valid) {
          return {
            success: false,
            error,
            code: ErrorCode.INSUFFICIENT_STAKE,
          };
        }
      }

      // 3. Execute action
      return await this.execute(intent.action, intent.parameters);

    } catch (e: any) {
      if (e.message?.startsWith("Cannot parse")) {
        return {
          success: false,
          error: e.message,
          code: ErrorCode.PARSE_ERROR,
        };
      }
      return {
        success: false,
        error: e.message ?? "Unknown error",
        code: ErrorCode.INTERNAL_ERROR,
      };
    }
  }

  private async execute(action: ActionType, params: Record<string, any>): Promise<PlatformResult> {
    const client = this.getClient();
    const meta = ACTION_META[action];

    try {
      let result: any;

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
            code: ErrorCode.INTERNAL_ERROR,
          };
      }

      return {
        success: true,
        result,
        message: `Action '${meta.action}' completed successfully`,
      };
    } catch (e: any) {
      return {
        success: false,
        error: e.message ?? "Execution failed",
        code: ErrorCode.INTERNAL_ERROR,
      };
    }
  }

  private async executeCollaboration(client: PlatformClient, action: string, params: any): Promise<any> {
    const path = `/api/collaboration/${action}`;
    if (action === "list") {
      return client.get(path, params);
    }
    return client.post(path, params);
  }

  private async executeMarketplace(client: PlatformClient, action: string, params: any): Promise<any> {
    const path = `/api/marketplace/${action}`;
    if (["find_work", "find_workers"].includes(action)) {
      return client.get(path, params);
    }
    return client.post(path, params);
  }

  private async executeDiscovery(client: PlatformClient, action: string, params: any): Promise<any> {
    const path = `/api/discovery/${action}`;
    if (action === "recommend") {
      return client.post(path, params);
    }
    return client.get(path, params);
  }

  private async executeNegotiation(client: PlatformClient, action: string, params: any): Promise<any> {
    return client.post(`/api/negotiation/${action}`, params);
  }

  private async executeWorkflow(client: PlatformClient, action: string, params: any): Promise<any> {
    const path = `/api/workflow/${action}`;
    if (action === "list") {
      return client.get(path, params);
    }
    return client.post(path, params);
  }

  private async executeLearning(client: PlatformClient, action: string, params: any): Promise<any> {
    return client.get(`/api/learning/${action}`, params);
  }

  /**
   * Get stake information for the current agent.
   */
  async getStakeInfo(): Promise<StakeInfo> {
    const checker = await this.getStakeChecker();
    return checker.getStakeInfo(this.agentId);
  }

  // Convenience methods

  async createCollaboration(goal: string): Promise<PlatformResult> {
    return this.call(`创建协作，目标是${goal}`);
  }

  async joinCollaboration(collabId: string): Promise<PlatformResult> {
    return this.call(`加入协作 ${collabId}`);
  }

  async publishService(name: string, price: number, skills?: string[]): Promise<PlatformResult> {
    const skillsStr = skills?.join(",") ?? "";
    return this.call(`发布服务 ${name}，价格 ${price} VIBE，技能 ${skillsStr}`);
  }

  async findWork(skill?: string): Promise<PlatformResult> {
    if (skill) {
      return this.call(`找 ${skill} 工作`);
    }
    return this.call("找工作");
  }

  async findWorkers(skills: string[]): Promise<PlatformResult> {
    return this.call(`找会 ${skills.join(",")} 的Worker`);
  }

  async discoverAgents(capability: string): Promise<PlatformResult> {
    return this.call(`找有 ${capability} 能力的Agent`);
  }

  // === Registration and Binding Methods ===

  /**
   * Self-register a new Agent (no Owner required).
   * This is a static method that can be called without an existing API key.
   */
  static async register(
    name: string,
    description: string = "",
    capabilities: string[] = [],
    baseUrl: string = "http://localhost:8000"
  ): Promise<RegistrationResult> {
    const client = new RegistrationClient(baseUrl);
    return client.register(name, description, capabilities);
  }

  /**
   * Request Owner binding.
   */
  async requestBinding(message: string = ""): Promise<BindingRequestResult> {
    const client = new RegistrationClient(this.baseUrl);
    return client.requestBinding(this.apiKey, message);
  }

  /**
   * Get Agent's binding status.
   */
  async getBindingStatus(): Promise<BindingStatus> {
    const client = new RegistrationClient(this.baseUrl);
    return client.getBindingStatus(this.apiKey);
  }

  // === Profile Management ===

  /**
   * Get Agent's detailed profile information.
   */
  async getProfile(): Promise<PlatformResult> {
    const client = this.getClient();
    try {
      const result = await client.get("/api/agents/profile");
      return { success: true, result };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  }

  /**
   * Update Agent's profile information.
   */
  async updateProfile(
    name?: string,
    description?: string,
    capabilities?: string[]
  ): Promise<PlatformResult> {
    const client = this.getClient();
    const data: Record<string, any> = {};
    if (name !== undefined) data.name = name;
    if (description !== undefined) data.description = description;
    if (capabilities !== undefined) data.capabilities = capabilities;

    try {
      const result = await client.post("/api/agents/profile", data);
      return { success: true, result };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  }

  // === API Key Management ===

  /**
   * List all API Keys for this Agent.
   */
  async listApiKeys(): Promise<PlatformResult> {
    const client = this.getClient();
    try {
      const result = await client.get("/api/agents/api-keys");
      return { success: true, result };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  }

  /**
   * Create a new API Key.
   */
  async createApiKey(name: string = "", expiresInDays: number = 365): Promise<PlatformResult> {
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
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  }

  /**
   * Revoke an API Key.
   */
  async revokeApiKey(keyId: string): Promise<PlatformResult> {
    const client = this.getClient();
    try {
      const result = await client.post(`/api/agents/api-keys/${keyId}/revoke`, {});
      return { success: true, result, message: "API Key revoked" };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  }

  /**
   * Renew an API Key (extend expiration).
   */
  async renewApiKey(keyId: string, extendsDays: number = 365): Promise<PlatformResult> {
    const client = this.getClient();
    try {
      const result = await client.post(`/api/agents/api-keys/${keyId}/renew`, {
        extends_days: extendsDays,
      });
      return { success: true, result };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  }

  // === Owner Info ===

  /**
   * Get information about the bound Owner.
   */
  async getOwnerInfo(): Promise<PlatformResult> {
    const client = this.getClient();
    try {
      const result = await client.get("/api/agents/owner");
      return { success: true, result };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  }
}

export default AgentPlatform;
