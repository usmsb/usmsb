/**
 * Gene Capsule Module for TypeScript
 *
 * Implements the Gene Capsule system for storing and managing agent experiences,
 * skills, and patterns. This is the core of the precise matching system.
 */

// ==================== Enums ====================

export enum ShareLevel {
  PUBLIC = "public",           // Fully visible
  SEMI_PUBLIC = "semi_public", // Visible on match, details hidden
  PRIVATE = "private",         // Only Meta Agent can see (for matching)
  HIDDEN = "hidden"            // Not participating in matching
}

export enum VerificationStatus {
  UNVERIFIED = "unverified",
  PENDING = "pending",
  VERIFIED = "verified",
  FAILED = "failed"
}

export enum ProficiencyLevel {
  BASIC = "basic",
  INTERMEDIATE = "intermediate",
  ADVANCED = "advanced",
  EXPERT = "expert",
  MASTER = "master"
}

export enum PatternType {
  PROBLEM_SOLVING = "problem_solving",
  OPTIMIZATION = "optimization",
  AUTOMATION = "automation",
  INTEGRATION = "integration",
  ANALYSIS = "analysis",
  CREATIVE = "creative"
}

// ==================== Interfaces ====================

export interface ExperienceGene {
  gene_id: string;
  task_type: string;
  task_category: string;

  // Task description (desensitized)
  task_description: string;
  task_keywords: string[];

  // Execution result
  outcome: string;  // success, partial, failed
  quality_score: number;  // 0-1
  completion_time: number;  // seconds

  // Client feedback
  client_rating?: number;  // 1-5
  client_review?: string;  // desensitized
  would_recommend?: boolean;

  // Techniques and methods
  techniques_used: string[];
  tools_used: string[];
  approach_description: string;

  // Shareable experience
  lessons_learned: string[];
  best_practices: string[];

  // Verification
  verified: boolean;
  verification_status: string;
  verification_methods?: string[];
  verification_timestamp?: string;

  // Visibility
  share_level: string;
  visible_to_verified_only: boolean;

  // Value score (computed)
  value_score?: number;

  // Timestamps
  created_at: string;
  task_completed_at?: string;
}

export interface SkillGene {
  skill_id: string;
  skill_name: string;
  category: string;

  // Proficiency
  proficiency_level: string;

  // Statistics (incremental)
  times_used: number;
  success_count: number;
  avg_quality_score: number;

  // Related experiences
  related_experience_ids: string[];

  // Certifications
  certifications: string[];
  verified_at?: string;
}

export interface PatternGene {
  pattern_id: string;
  pattern_name: string;
  pattern_type: string;

  // Pattern definition
  trigger_conditions: string[];  // When to apply this pattern
  approach: string;               // How to apply
  expected_outcome: string;       // What to expect

  // Usage statistics
  times_applied: number;
  success_rate: number;

  // Supporting examples
  example_experience_ids: string[];

  // Confidence
  confidence: number;
}

export interface GeneCapsule {
  capsule_id: string;
  agent_id: string;
  version: string;

  // Core genes
  experience_genes: ExperienceGene[];
  skill_genes: SkillGene[];
  pattern_genes: PatternGene[];

  // Statistics
  total_tasks: number;
  success_rate: number;
  avg_satisfaction: number;

  // Verification status
  verification_status: string;

  // Timestamps
  created_at: string;
  last_updated: string;
}

export interface ExperienceValueScore {
  overall_score: number;  // 0-100

  // Dimension scores
  scarcity_score: number;      // How rare is this capability
  difficulty_score: number;    // Task complexity
  impact_score: number;        // Value created for client
  recency_score: number;       // How recent
  demonstration_score: number; // How well it demonstrates capability
}

// ==================== Request/Response Types ====================

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

// ==================== Gene Capsule API Class ====================

/**
 * Gene Capsule API client for managing agent experiences, skills, and patterns.
 */
export class GeneCapsuleAPI {
  private client: PlatformClient;
  private agentId: string;

  constructor(client: PlatformClient, agentId: string) {
    this.client = client;
    this.agentId = agentId;
  }

  /**
   * Get agent's gene capsule.
   */
  async getCapsule(agentId?: string): Promise<GeneCapsule> {
    const targetId = agentId || this.agentId;
    return this.client.get(`/api/gene-capsule/${targetId}`);
  }

  /**
   * Add a new experience gene.
   */
  async addExperience(
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
    },
    autoDesensitize: boolean = true
  ): Promise<ExperienceGene> {
    return this.client.post("/api/gene-capsule/experiences", {
      agent_id: this.agentId,
      experience,
      auto_desensitize: autoDesensitize
    });
  }

  /**
   * Update experience visibility.
   */
  async updateVisibility(
    experienceId: string,
    shareLevel: string
  ): Promise<{ success: boolean; experience_id: string; share_level: string }> {
    return this.client.patch(
      `/api/gene-capsule/experiences/${experienceId}/visibility`,
      {
        agent_id: this.agentId,
        share_level: shareLevel
      }
    );
  }

  /**
   * Find matching experiences for a task.
   */
  async match(
    taskDescription: string,
    requiredSkills: string[] = [],
    minRelevance: number = 0.3,
    limit: number = 10
  ): Promise<MatchingExperience[]> {
    return this.client.post("/api/gene-capsule/match", {
      agent_id: this.agentId,
      task_description: taskDescription,
      required_skills: requiredSkills,
      min_relevance: minRelevance,
      limit: limit
    });
  }

  /**
   * Export showcase for negotiation.
   */
  async showcase(
    experienceIds: string[] = [],
    forNegotiation: boolean = true
  ): Promise<ShowcaseResponse> {
    return this.client.post("/api/gene-capsule/showcase", {
      agent_id: this.agentId,
      experience_ids: experienceIds,
      for_negotiation: forNegotiation
    });
  }

  /**
   * Search agents by experience.
   */
  async searchAgents(
    taskDescription: string,
    requiredSkills: string[] = [],
    minRelevance: number = 0.3,
    limit: number = 10
  ): Promise<AgentExperienceSearchResult[]> {
    return this.client.post("/api/gene-capsule/search-agents", {
      task_description: taskDescription,
      required_skills: requiredSkills,
      min_experience_relevance: minRelevance,
      limit: limit
    });
  }

  /**
   * Request verification for an experience.
   */
  async requestVerification(experienceId: string): Promise<any> {
    return this.client.post(
      `/api/gene-capsule/experiences/${experienceId}/verify`,
      { agent_id: this.agentId }
    );
  }

  /**
   * Desensitize text using LLM.
   */
  async desensitize(
    text: string,
    context: string = "",
    recursionDepth: number = 3
  ): Promise<DesensitizeTextResponse> {
    return this.client.post("/api/gene-capsule/desensitize", {
      text,
      context,
      recursion_depth: recursionDepth
    });
  }

  /**
   * Get pattern library.
   */
  async getPatterns(agentId?: string): Promise<PatternGene[]> {
    const targetId = agentId || this.agentId;
    return this.client.get(`/api/gene-capsule/${targetId}/patterns`);
  }

  /**
   * Get experience value scores.
   */
  async getValueScores(agentId?: string): Promise<ExperienceValueScore[]> {
    const targetId = agentId || this.agentId;
    return this.client.get(`/api/gene-capsule/${targetId}/value-scores`);
  }

  /**
   * Sync capsule with platform.
   */
  async sync(): Promise<any> {
    return this.client.post(`/api/gene-capsule/${this.agentId}/sync`, {});
  }

  /**
   * Get capsule summary for display.
   */
  async getSummary(agentId?: string): Promise<{
    capsule_id: string;
    version: string;
    total_tasks: number;
    success_rate: number;
    avg_satisfaction: number;
    categories: Record<string, number>;
    top_skills: Array<{ name: string; level: string; times_used: number }>;
    patterns_count: number;
    last_updated: string;
  }> {
    const capsule = await this.getCapsule(agentId);

    // Count by category
    const categories: Record<string, number> = {};
    for (const exp of capsule.experience_genes) {
      const cat = exp.task_category || "other";
      categories[cat] = (categories[cat] || 0) + 1;
    }

    // Top skills
    const topSkills = [...capsule.skill_genes]
      .sort((a, b) => b.times_used - a.times_used)
      .slice(0, 5)
      .map(s => ({
        name: s.skill_name,
        level: s.proficiency_level,
        times_used: s.times_used
      }));

    return {
      capsule_id: capsule.capsule_id,
      version: capsule.version,
      total_tasks: capsule.total_tasks,
      success_rate: Math.round(capsule.success_rate * 100 * 10) / 10,
      avg_satisfaction: Math.round(capsule.avg_satisfaction * 10) / 10,
      categories,
      top_skills: topSkills,
      patterns_count: capsule.pattern_genes.length,
      last_updated: capsule.last_updated
    };
  }

  /**
   * Search for agents by experience relevance.
   */
  async searchAgents(
    taskDescription: string,
    requiredSkills: string[] = [],
    minRelevance: number = 0.3,
    limit: number = 10
  ): Promise<AgentExperienceSearchResult[]> {
    return this.client.post("/api/gene-capsule/search-agents", {
      task_description: taskDescription,
      required_skills: requiredSkills,
      min_experience_relevance: minRelevance,
      limit: limit
    });
  }

  /**
   * Request verification for an experience.
   */
  async requestVerification(experienceId: string): Promise<any> {
    return this.client.post(
      `/api/gene-capsule/experiences/${experienceId}/verify`,
      { agent_id: this.agentId }
    );
  }
}

// PlatformClient interface to avoid circular dependency
interface PlatformClient {
  get(path: string, params?: Record<string, any>): Promise<any>;
  post(path: string, body?: Record<string, any>): Promise<any>;
  patch(path: string, body?: Record<string, any>): Promise<any>;
}
