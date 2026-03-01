/**
 * Intent parser for natural language requests.
 */

import { ActionType, Intent, ACTION_META } from "./types";

/**
 * Pattern definitions for each action type.
 */
const PATTERNS: Map<ActionType, RegExp[]> = new Map([
  // Collaboration
  [ActionType.COLLABORATION_CREATE, [
    /创建.*协作/, /建立.*合作/, /start.*collaboration/i, /create.*collab/i
  ]],
  [ActionType.COLLABORATION_JOIN, [
    /加入.*协作/, /参与.*协作/, /join.*collab/i, /participate.*collab/i
  ]],
  [ActionType.COLLABORATION_LIST, [
    /列出.*协作/, /查看.*协作/, /list.*collab/i, /show.*collab/i, /我的协作/
  ]],
  [ActionType.COLLABORATION_CONTRIBUTE, [
    /提交.*贡献/, /贡献.*内容/, /contribute/i, /submit.*contribution/i
  ]],

  // Marketplace
  [ActionType.MARKETPLACE_PUBLISH_SERVICE, [
    /发布.*服务/, /提供.*服务/, /publish.*service/i, /offer.*service/i, /创建.*服务/
  ]],
  [ActionType.MARKETPLACE_FIND_WORK, [
    /找.*工作/, /找工作/, /find.*work/i, /looking.*job/i, /搜索.*工作/
  ]],
  [ActionType.MARKETPLACE_FIND_WORKERS, [
    /找.*worker/, /找.*工人/, /找.*开发/, /hire.*agent/i, /find.*developer/i, /find.*workers/i
  ]],
  [ActionType.MARKETPLACE_PUBLISH_DEMAND, [
    /发布.*需求/, /创建.*需求/, /publish.*demand/i, /post.*job/i
  ]],
  [ActionType.MARKETPLACE_HIRE, [
    /雇佣/, /hire/i
  ]],

  // Discovery
  [ActionType.DISCOVERY_BY_CAPABILITY, [
    /按.*能力.*发现/, /找有.*能力的/, /discover.*capability/i, /find.*agent.*with/i, /按能力.*搜索/
  ]],
  [ActionType.DISCOVERY_BY_SKILL, [
    /按.*技能.*发现/, /找.*技能/, /find.*skill/i, /按技能.*搜索/
  ]],
  [ActionType.DISCOVERY_RECOMMEND, [
    /推荐.*agent/, /智能.*推荐/, /recommend/i, /suggest.*agent/i
  ]],

  // Negotiation
  [ActionType.NEGOTIATION_INITIATE, [
    /发起.*协商/, /start.*negotiation/i, /initiate.*negotiation/i, /开始.*协商/
  ]],
  [ActionType.NEGOTIATION_ACCEPT, [
    /接受.*协商/, /accept.*negotiation/i, /agree.*terms/i, /同意.*协商/
  ]],
  [ActionType.NEGOTIATION_REJECT, [
    /拒绝.*协商/, /reject.*negotiation/i, /decline.*offer/i
  ]],
  [ActionType.NEGOTIATION_PROPOSE, [
    /提议.*条件/, /propose.*terms/i, /new.*offer/i, /提出.*条件/
  ]],

  // Workflow
  [ActionType.WORKFLOW_CREATE, [
    /创建.*工作流/, /create.*workflow/i, /new.*workflow/i
  ]],
  [ActionType.WORKFLOW_EXECUTE, [
    /执行.*工作流/, /run.*workflow/i, /execute.*workflow/i
  ]],
  [ActionType.WORKFLOW_LIST, [
    /列出.*工作流/, /查看.*工作流/, /list.*workflow/i, /show.*workflow/i
  ]],

  // Learning
  [ActionType.LEARNING_ANALYZE, [
    /分析.*表现/, /analyze.*performance/i, /性能.*分析/
  ]],
  [ActionType.LEARNING_INSIGHTS, [
    /获取.*洞察/, /get.*insights/i, /改进.*建议/
  ]],
]);

/**
 * Common skill keywords to extract.
 */
const SKILL_KEYWORDS = [
  "python", "javascript", "typescript", "java", "go", "rust", "c++",
  "react", "vue", "angular", "node", "django", "flask", "fastapi",
  "ai", "ml", "machine learning", "deep learning", "nlp", "cv",
  "blockchain", "smart contract", "web3", "defi",
  "frontend", "backend", "fullstack", "devops", "cloud",
  "前端", "后端", "全栈", "区块链", "智能合约", "人工智能",
];

/**
 * Intent parser class.
 */
export class IntentParser {
  /**
   * Parse a natural language request into an Intent.
   */
  parse(request: string): Intent {
    const requestLower = request.toLowerCase();

    // Find matching action type
    for (const [actionType, patterns] of PATTERNS) {
      for (const pattern of patterns) {
        if (pattern.test(requestLower)) {
          const parameters = this.extractParameters(request, actionType);
          return {
            action: actionType,
            parameters,
            confidence: 1.0,
            rawRequest: request,
          };
        }
      }
    }

    throw new Error(`Cannot parse request: ${request}`);
  }

  /**
   * Extract parameters from the request based on action type.
   */
  private extractParameters(request: string, action: ActionType): Record<string, any> {
    const params: Record<string, any> = {};
    const meta = ACTION_META[action];

    // Extract price (for publish_service)
    if (action === ActionType.MARKETPLACE_PUBLISH_SERVICE) {
      const priceMatch = request.match(/(\d+)\s*(VIBE|vibe|块|元)?/);
      if (priceMatch) {
        params.price = parseInt(priceMatch[1], 10);
      }
    }

    // Extract skills
    const skills = this.extractSkills(request);
    if (skills.length > 0) {
      params.skills = skills;
    }

    // Extract IDs (collab-id, workflow-id, etc.)
    const idMatch = request.match(/(collab|workflow|negotiation|service|agent)[-:_]?([a-zA-Z0-9-]+)/i);
    if (idMatch) {
      params.id = `${idMatch[1]}-${idMatch[2]}`;
      // Map to specific ID parameter based on category
      if (meta.category === "collaboration") {
        params.collabId = params.id;
      } else if (meta.category === "workflow") {
        params.workflowId = params.id;
      } else if (meta.category === "negotiation") {
        params.negotiationId = params.id;
      }
    }

    // Extract goal/description for collaboration create
    if (action === ActionType.COLLABORATION_CREATE) {
      const goalMatch = request.match(/(?:目标|goal|目的是)[:：]?\s*(.+)/i);
      if (goalMatch) {
        params.goal = goalMatch[1].trim();
      } else {
        params.goal = request;
      }
    }

    // Extract content for contribute
    if (action === ActionType.COLLABORATION_CONTRIBUTE) {
      const contentMatch = request.match(/(?:内容|content)[:：]?\s*(.+)/i);
      if (contentMatch) {
        params.content = contentMatch[1].trim();
      }
    }

    return params;
  }

  /**
   * Extract skill keywords from request.
   */
  private extractSkills(request: string): string[] {
    const requestLower = request.toLowerCase();
    const foundSkills: string[] = [];

    for (const skill of SKILL_KEYWORDS) {
      if (requestLower.includes(skill.toLowerCase())) {
        foundSkills.push(skill);
      }
    }

    return foundSkills;
  }
}
