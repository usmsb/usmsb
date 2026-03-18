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

  // Order
  [ActionType.ORDER_FROM_PRE_MATCH, [
    /创建.*订单.*从.*预匹配/, /从.*预匹配.*创建.*订单/, /create.*order.*from.*pre.?match/i,
    /订单.*预匹配/, /order.*from.*prematch/i
  ]],
  [ActionType.ORDER_CREATE, [
    /创建.*订单/, /新建.*订单/, /create.*order/i, /new.*order/i, /发起.*订单/
  ]],
  [ActionType.ORDER_CONFIRM, [
    /确认.*订单/, /confirm.*order/i, /订单.*确认/
  ]],
  [ActionType.ORDER_START, [
    /开始.*工作/, /start.*work/i, /开始.*订单/, /order.*start/i, /启动.*工作/
  ]],
  [ActionType.ORDER_DELIVER, [
    /提交.*交付/, /submit.*deliver/i, /交付.*成果/, /order.*deliver/i, /提交.*成果/
  ]],
  [ActionType.ORDER_ACCEPT, [
    /接受.*交付/, /accept.*deliver/i, /验收.*订单/, /order.*accept/i
  ]],
  [ActionType.ORDER_DISPUTE, [
    /争议.*订单/, /dispute.*order/i, /订单.*争议/, /投诉.*订单/
  ]],
  [ActionType.ORDER_CANCEL, [
    /取消.*订单/, /cancel.*order/i, /订单.*取消/
  ]],
  [ActionType.ORDER_LIST, [
    /列出.*订单/, /查看.*订单/, /list.*order/i, /我的订单/, /show.*order/i
  ]],
  [ActionType.ORDER_GET, [
    /查询.*订单/, /get.*order/i, /订单.*详情/
  ]],
  [ActionType.ORDER_STATUS, [
    /订单.*状态/, /order.*status/i
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

    // Extract IDs (collab-id, workflow-id, negotiation-id, order-id, etc.)
    const idMatch = request.match(/(collab|workflow|negotiation|service|agent|order|prematch)[-_]?([a-zA-Z0-9-]+)/i);
    if (idMatch) {
      const prefix = idMatch[1].toLowerCase();
      const idValue = `${idMatch[1]}-${idMatch[2]}`;
      params.id = idValue;
      if (prefix === "collab" || prefix === "collaboration") {
        params.collabId = idValue;
      } else if (prefix === "workflow") {
        params.workflowId = idValue;
      } else if (prefix === "negotiation" || prefix === "neg") {
        params.negotiationId = idValue;
      } else if (prefix === "order") {
        params.orderId = idValue;
      } else if (prefix === "prematch" || prefix === "pre-match") {
        params.negotiationId = idValue;  // reuse negotiationId
      }
    }

    // Extract rating (for accept)
    if (action === ActionType.ORDER_ACCEPT) {
      const ratingMatch = request.match(/(\d+)\s*(?:星|star|分|rating)/i);
      if (ratingMatch) {
        params.rating = parseInt(ratingMatch[1], 10);
      } else {
        params.rating = 5;  // default
      }
      const commentMatch = request.match(/(?:评价|comment|备注)[:：]?\s*(.+)/i);
      if (commentMatch) {
        params.comment = commentMatch[1].trim();
      }
    }

    // Extract reason (for dispute/cancel)
    if (action === ActionType.ORDER_DISPUTE || action === ActionType.ORDER_CANCEL) {
      const reasonMatch = request.match(/(?:原因|reason|理由)[:：]?\s*(.+)/i);
      if (reasonMatch) {
        params.reason = reasonMatch[1].trim();
      } else {
        // Use the whole request after the action as reason
        params.reason = request;
      }
    }

    // Extract deliverable info (for deliver)
    if (action === ActionType.ORDER_DELIVER) {
      const descMatch = request.match(/(?:交付|成果|内容|description)[:：]?\s*(.+)/i);
      params.description = descMatch ? descMatch[1].trim() : request;
      // Extract artifact type
      if (/代码|code/i.test(request)) params.artifactType = "code";
      else if (/文档|doc/i.test(request)) params.artifactType = "document";
      else if (/链接|link|url/i.test(request)) params.artifactType = "link";
      else params.artifactType = "text";
    }

    // Extract price (for order create)
    if (action === ActionType.ORDER_CREATE) {
      const priceMatch = request.match(/(\d+)\s*(?:VIBE|vibe|元|块)/i);
      if (priceMatch) {
        params.price = parseInt(priceMatch[1], 10);
      }
    }

    // Extract goal/description for order create
    if (action === ActionType.ORDER_CREATE || action === ActionType.ORDER_FROM_PRE_MATCH) {
      const goalMatch = request.match(/(?:任务|目标|任务描述|goal|description)[:：]?\s*(.+)/i);
      if (goalMatch) {
        params.taskDescription = goalMatch[1].trim();
      } else {
        params.taskDescription = request;
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
