/**
 * Agent registration module for self-registration and Owner binding.
 */

import fetch from "node-fetch";

// Configuration constants
const AGENT_ID_PREFIX = "agent-";
const AGENT_ID_LENGTH = 12;
const AGENT_NAME_MAX_LENGTH = 100;

const API_KEY_PREFIX = "usmsb_";
const API_KEY_HASH_LENGTH = 16;
const API_KEY_DEFAULT_EXPIRE_DAYS = 365;
const API_KEY_MAX_EXPIRE_DAYS = 3650;
const API_KEY_MAX_PER_AGENT = 10;

const BINDING_CODE_PREFIX = "bind-";
const BINDING_CODE_EXPIRE_SECONDS = 3600; // 1 hour

// Helper functions
function generateRandomString(length: number): string {
  const crypto = require("crypto");
  return crypto.randomBytes(Math.ceil(length / 2)).toString("hex").slice(0, length);
}

function generateAgentId(): string {
  return `${AGENT_ID_PREFIX}${generateRandomString(AGENT_ID_LENGTH)}`;
}

function generateApiKey(agentId: string, timestamp?: number): string {
  const crypto = require("crypto");
  const ts = timestamp ?? Math.floor(Date.now() / 1000);
  const raw = `${agentId}:${ts}:${generateRandomString(32)}`;
  const hash = crypto.createHash("sha256").update(raw).digest("hex").slice(0, API_KEY_HASH_LENGTH);
  return `${API_KEY_PREFIX}${hash}_${ts}`;
}

function generateBindingCode(): { code: string; expiresAt: number } {
  const code = `${BINDING_CODE_PREFIX}${generateRandomString(8)}`;
  const expiresAt = Math.floor(Date.now() / 1000) + BINDING_CODE_EXPIRE_SECONDS;
  return { code, expiresAt };
}

// Result types
export interface RegistrationResult {
  success: boolean;
  agentId?: string;
  apiKey?: string;
  level: number;
  message: string;
  error?: string;
  code?: string;
}

export interface BindingRequestResult {
  success: boolean;
  bindingCode?: string;
  bindingUrl?: string;
  expiresAt?: number;
  expiresIn?: number;
  message: string;
  error?: string;
  code?: string;
}

export interface BindingStatus {
  bound: boolean;
  ownerWallet?: string;
  stakeTier?: string;
  stakeAmount?: number;
  boundAt?: number;
}

export interface APIKeyInfo {
  id: string;
  name: string;
  createdAt: number;
  expiresAt: number;
  lastUsedAt?: number;
  revoked: boolean;
}

/**
 * Registration client for Agent operations.
 */
export class RegistrationClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * Register a new Agent (self-registration, no Owner required).
   */
  async register(
    name: string,
    description: string = "",
    capabilities: string[] = []
  ): Promise<RegistrationResult> {
    // Validate name
    if (!name || name.length > AGENT_NAME_MAX_LENGTH) {
      return {
        success: false,
        level: 0,
        message: "",
        error: `Name must be 1-${AGENT_NAME_MAX_LENGTH} characters`,
        code: "INVALID_NAME",
      };
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/agents/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description, capabilities }),
      });

      const data = await response.json() as any;

      if (response.status === 200 && data.success) {
        return {
          success: true,
          agentId: data.agent_id,
          apiKey: data.api_key,
          level: data.level ?? 0,
          message: data.message ?? "Registration successful",
        };
      } else {
        return {
          success: false,
          level: 0,
          message: "",
          error: data.error ?? "Registration failed",
          code: data.code ?? "REGISTRATION_FAILED",
        };
      }
    } catch (e: any) {
      return {
        success: false,
        level: 0,
        message: "",
        error: `Network error: ${e.message}`,
        code: "NETWORK_ERROR",
      };
    }
  }

  /**
   * Request Owner binding.
   */
  async requestBinding(apiKey: string, message: string = ""): Promise<BindingRequestResult> {
    try {
      const response = await fetch(`${this.baseUrl}/api/agents/request-binding`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify({ message }),
      });

      const data = await response.json() as any;

      if (response.status === 200 && data.success) {
        return {
          success: true,
          bindingCode: data.binding_code,
          bindingUrl: data.binding_url,
          expiresAt: data.expires_at,
          expiresIn: data.expires_in,
          message: data.message ?? "",
        };
      } else {
        return {
          success: false,
          message: "",
          error: data.error ?? "Request failed",
          code: data.code ?? "REQUEST_FAILED",
        };
      }
    } catch (e: any) {
      return {
        success: false,
        message: "",
        error: e.message,
        code: "INTERNAL_ERROR",
      };
    }
  }

  /**
   * Get Agent's binding status.
   */
  async getBindingStatus(apiKey: string): Promise<BindingStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/api/agents/binding-status`, {
        method: "GET",
        headers: { "X-API-Key": apiKey },
      });

      const data = await response.json() as any;

      return {
        bound: data.bound ?? false,
        ownerWallet: data.owner_wallet,
        stakeTier: data.stake_tier,
        stakeAmount: data.stake_amount,
        boundAt: data.bound_at,
      };
    } catch {
      return { bound: false };
    }
  }
}
