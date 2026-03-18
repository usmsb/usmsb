/**
 * Gene Capsule Module for TypeScript
 *
 * Implements the Gene Capsule system for storing and managing agent experiences,
 * skills, and patterns. This is the core of the precise matching system.
 */
export declare enum ShareLevel {
    PUBLIC = "public",// Fully visible
    SEMI_PUBLIC = "semi_public",// Visible on match, details hidden
    PRIVATE = "private",// Only Meta Agent can see (for matching)
    HIDDEN = "hidden"
}
export declare enum VerificationStatus {
    UNVERIFIED = "unverified",
    PENDING = "pending",
    VERIFIED = "verified",
    FAILED = "failed"
}
export declare enum ProficiencyLevel {
    BASIC = "basic",
    INTERMEDIATE = "intermediate",
    ADVANCED = "advanced",
    EXPERT = "expert",
    MASTER = "master"
}
export declare enum PatternType {
    PROBLEM_SOLVING = "problem_solving",
    OPTIMIZATION = "optimization",
    AUTOMATION = "automation",
    INTEGRATION = "integration",
    ANALYSIS = "analysis",
    CREATIVE = "creative"
}
export interface ExperienceGene {
    gene_id: string;
    task_type: string;
    task_category: string;
    task_description: string;
    task_keywords: string[];
    outcome: string;
    quality_score: number;
    completion_time: number;
    client_rating?: number;
    client_review?: string;
    would_recommend?: boolean;
    techniques_used: string[];
    tools_used: string[];
    approach_description: string;
    lessons_learned: string[];
    best_practices: string[];
    verified: boolean;
    verification_status: string;
    verification_methods?: string[];
    verification_timestamp?: string;
    share_level: string;
    visible_to_verified_only: boolean;
    value_score?: number;
    created_at: string;
    task_completed_at?: string;
}
export interface SkillGene {
    skill_id: string;
    skill_name: string;
    category: string;
    proficiency_level: string;
    times_used: number;
    success_count: number;
    avg_quality_score: number;
    related_experience_ids: string[];
    certifications: string[];
    verified_at?: string;
}
export interface PatternGene {
    pattern_id: string;
    pattern_name: string;
    pattern_type: string;
    trigger_conditions: string[];
    approach: string;
    expected_outcome: string;
    times_applied: number;
    success_rate: number;
    example_experience_ids: string[];
    confidence: number;
}
export interface GeneCapsule {
    capsule_id: string;
    agent_id: string;
    version: string;
    experience_genes: ExperienceGene[];
    skill_genes: SkillGene[];
    pattern_genes: PatternGene[];
    total_tasks: number;
    success_rate: number;
    avg_satisfaction: number;
    verification_status: string;
    created_at: string;
    last_updated: string;
}
export interface ExperienceValueScore {
    overall_score: number;
    scarcity_score: number;
    difficulty_score: number;
    impact_score: number;
    recency_score: number;
    demonstration_score: number;
}
export interface AddExperienceRequest {
    agent_id: string;
    experience: {
        task_type: string;
        task_category: string;
        task_description: string;
        techniques_used: string[];
        tools_used?: string[];
        approach_description?: string;
        outcome: string;
        quality_score: number;
        completion_time: number;
        client_rating?: number;
        client_review?: string;
        lessons_learned?: string[];
    };
    auto_desensitize?: boolean;
}
export interface UpdateVisibilityRequest {
    agent_id: string;
    share_level: string;
}
export interface DesensitizeTextRequest {
    text: string;
    context?: string;
    recursion_depth?: number;
}
export interface DesensitizeTextResponse {
    original_text: string;
    desensitized_text: string;
    detected_entities: string[];
    rounds_completed: number;
    confidence: number;
}
export interface FindMatchingExperiencesRequest {
    agent_id: string;
    task_description: string;
    required_skills?: string[];
    min_relevance?: number;
    limit?: number;
}
export interface MatchingExperience {
    experience: ExperienceGene;
    relevance_score: number;
    matching_skills: string[];
    matching_techniques: string[];
    reasoning?: string;
}
export interface SearchAgentsByExperienceRequest {
    task_description: string;
    required_skills?: string[];
    min_experience_relevance?: number;
    limit?: number;
}
export interface AgentExperienceSearchResult {
    agent_id: string;
    agent_name?: string;
    overall_relevance: number;
    matched_experiences: MatchingExperience[];
    verified_experiences_count: number;
    total_experience_value: number;
}
export interface ExportShowcaseRequest {
    agent_id: string;
    experience_ids?: string[];
    for_negotiation?: boolean;
}
export interface ShowcaseResponse {
    agent_id: string;
    showcase_id: string;
    experiences: ExperienceGene[];
    skills: SkillGene[];
    patterns: PatternGene[];
    generated_at: string;
    summary?: string;
}
export interface RequestVerificationRequest {
    agent_id: string;
}
export interface VerificationStatusResponse {
    experience_id: string;
    status: string;
    verification_methods: string[];
    verification_score: number;
    verified_at?: string;
    details?: string;
}
/**
 * Gene Capsule API client for managing agent experiences, skills, and patterns.
 */
export declare class GeneCapsuleAPI {
    private client;
    private agentId;
    constructor(client: PlatformClient, agentId: string);
    /**
     * Get agent's gene capsule.
     */
    getCapsule(agentId?: string): Promise<GeneCapsule>;
    /**
     * Add a new experience gene.
     */
    addExperience(experience: {
        task_type: string;
        task_category: string;
        task_description: string;
        techniques_used: string[];
        tools_used?: string[];
        approach_description?: string;
        outcome: string;
        quality_score: number;
        completion_time: number;
        client_rating?: number;
        client_review?: string;
        lessons_learned?: string[];
    }, autoDesensitize?: boolean): Promise<ExperienceGene>;
    /**
     * Update experience visibility.
     */
    updateVisibility(experienceId: string, shareLevel: string): Promise<{
        success: boolean;
        experience_id: string;
        share_level: string;
    }>;
    /**
     * Find matching experiences for a task.
     */
    match(taskDescription: string, requiredSkills?: string[], minRelevance?: number, limit?: number): Promise<MatchingExperience[]>;
    /**
     * Export showcase for negotiation.
     */
    showcase(experienceIds?: string[], forNegotiation?: boolean): Promise<ShowcaseResponse>;
    /**
     * Search agents by experience.
     */
    searchAgents(taskDescription: string, requiredSkills?: string[], minRelevance?: number, limit?: number): Promise<AgentExperienceSearchResult[]>;
    /**
     * Request verification for an experience.
     */
    requestVerification(experienceId: string): Promise<any>;
    /**
     * Desensitize text using LLM.
     */
    desensitize(text: string, context?: string, recursionDepth?: number): Promise<DesensitizeTextResponse>;
    /**
     * Get pattern library.
     */
    getPatterns(agentId?: string): Promise<PatternGene[]>;
    /**
     * Get experience value scores.
     */
    getValueScores(agentId?: string): Promise<ExperienceValueScore[]>;
    /**
     * Sync capsule with platform.
     */
    sync(): Promise<any>;
    /**
     * Get capsule summary for display.
     */
    getSummary(agentId?: string): Promise<{
        capsule_id: string;
        version: string;
        total_tasks: number;
        success_rate: number;
        avg_satisfaction: number;
        categories: Record<string, number>;
        top_skills: Array<{
            name: string;
            level: string;
            times_used: number;
        }>;
        patterns_count: number;
        last_updated: string;
    }>;
}
interface PlatformClient {
    get(path: string, params?: Record<string, any>): Promise<any>;
    post(path: string, body?: Record<string, any>): Promise<any>;
    patch(path: string, body?: Record<string, any>): Promise<any>;
}
export {};
//# sourceMappingURL=gene-capsule.d.ts.map