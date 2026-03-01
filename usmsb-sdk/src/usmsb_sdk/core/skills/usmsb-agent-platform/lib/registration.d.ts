/**
 * Agent registration module for self-registration and Owner binding.
 */
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
export declare class RegistrationClient {
    private baseUrl;
    constructor(baseUrl: string);
    /**
     * Register a new Agent (self-registration, no Owner required).
     */
    register(name: string, description?: string, capabilities?: string[]): Promise<RegistrationResult>;
    /**
     * Request Owner binding.
     */
    requestBinding(apiKey: string, message?: string): Promise<BindingRequestResult>;
    /**
     * Get Agent's binding status.
     */
    getBindingStatus(apiKey: string): Promise<BindingStatus>;
}
//# sourceMappingURL=registration.d.ts.map