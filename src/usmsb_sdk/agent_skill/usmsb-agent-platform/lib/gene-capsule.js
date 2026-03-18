"use strict";
/**
 * Gene Capsule Module for TypeScript
 *
 * Implements the Gene Capsule system for storing and managing agent experiences,
 * skills, and patterns. This is the core of the precise matching system.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.GeneCapsuleAPI = exports.PatternType = exports.ProficiencyLevel = exports.VerificationStatus = exports.ShareLevel = void 0;
// ==================== Enums ====================
var ShareLevel;
(function (ShareLevel) {
    ShareLevel["PUBLIC"] = "public";
    ShareLevel["SEMI_PUBLIC"] = "semi_public";
    ShareLevel["PRIVATE"] = "private";
    ShareLevel["HIDDEN"] = "hidden"; // Not participating in matching
})(ShareLevel || (exports.ShareLevel = ShareLevel = {}));
var VerificationStatus;
(function (VerificationStatus) {
    VerificationStatus["UNVERIFIED"] = "unverified";
    VerificationStatus["PENDING"] = "pending";
    VerificationStatus["VERIFIED"] = "verified";
    VerificationStatus["FAILED"] = "failed";
})(VerificationStatus || (exports.VerificationStatus = VerificationStatus = {}));
var ProficiencyLevel;
(function (ProficiencyLevel) {
    ProficiencyLevel["BASIC"] = "basic";
    ProficiencyLevel["INTERMEDIATE"] = "intermediate";
    ProficiencyLevel["ADVANCED"] = "advanced";
    ProficiencyLevel["EXPERT"] = "expert";
    ProficiencyLevel["MASTER"] = "master";
})(ProficiencyLevel || (exports.ProficiencyLevel = ProficiencyLevel = {}));
var PatternType;
(function (PatternType) {
    PatternType["PROBLEM_SOLVING"] = "problem_solving";
    PatternType["OPTIMIZATION"] = "optimization";
    PatternType["AUTOMATION"] = "automation";
    PatternType["INTEGRATION"] = "integration";
    PatternType["ANALYSIS"] = "analysis";
    PatternType["CREATIVE"] = "creative";
})(PatternType || (exports.PatternType = PatternType = {}));
// ==================== Gene Capsule API Class ====================
/**
 * Gene Capsule API client for managing agent experiences, skills, and patterns.
 */
class GeneCapsuleAPI {
    constructor(client, agentId) {
        this.client = client;
        this.agentId = agentId;
    }
    /**
     * Get agent's gene capsule.
     */
    async getCapsule(agentId) {
        const targetId = agentId || this.agentId;
        return this.client.get(`/api/gene-capsule/${targetId}`);
    }
    /**
     * Add a new experience gene.
     */
    async addExperience(experience, autoDesensitize = true) {
        return this.client.post("/api/gene-capsule/experiences", {
            agent_id: this.agentId,
            experience,
            auto_desensitize: autoDesensitize
        });
    }
    /**
     * Update experience visibility.
     */
    async updateVisibility(experienceId, shareLevel) {
        return this.client.patch(`/api/gene-capsule/experiences/${experienceId}/visibility`, {
            agent_id: this.agentId,
            share_level: shareLevel
        });
    }
    /**
     * Find matching experiences for a task.
     */
    async match(taskDescription, requiredSkills = [], minRelevance = 0.3, limit = 10) {
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
    async showcase(experienceIds = [], forNegotiation = true) {
        return this.client.post("/api/gene-capsule/showcase", {
            agent_id: this.agentId,
            experience_ids: experienceIds,
            for_negotiation: forNegotiation
        });
    }
    /**
     * Search agents by experience.
     */
    async searchAgents(taskDescription, requiredSkills = [], minRelevance = 0.3, limit = 10) {
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
    async requestVerification(experienceId) {
        return this.client.post(`/api/gene-capsule/experiences/${experienceId}/verify`, { agent_id: this.agentId });
    }
    /**
     * Desensitize text using LLM.
     */
    async desensitize(text, context = "", recursionDepth = 3) {
        return this.client.post("/api/gene-capsule/desensitize", {
            text,
            context,
            recursion_depth: recursionDepth
        });
    }
    /**
     * Get pattern library.
     */
    async getPatterns(agentId) {
        const targetId = agentId || this.agentId;
        return this.client.get(`/api/gene-capsule/${targetId}/patterns`);
    }
    /**
     * Get experience value scores.
     */
    async getValueScores(agentId) {
        const targetId = agentId || this.agentId;
        return this.client.get(`/api/gene-capsule/${targetId}/value-scores`);
    }
    /**
     * Sync capsule with platform.
     */
    async sync() {
        return this.client.post(`/api/gene-capsule/${this.agentId}/sync`, {});
    }
    /**
     * Get capsule summary for display.
     */
    async getSummary(agentId) {
        const capsule = await this.getCapsule(agentId);
        // Count by category
        const categories = {};
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
}
exports.GeneCapsuleAPI = GeneCapsuleAPI;
//# sourceMappingURL=gene-capsule.js.map