"""
Intent parser for natural language requests.
"""

import re
from typing import Any

from .types import ActionType, Intent


class IntentParser:
    """
    Parse natural language requests into structured intents.

    Supports both Chinese and English requests.
    """

    # Pattern definitions for each action type
    PATTERNS: dict[ActionType, list[str]] = {
        # ==================== Collaboration ====================
        ActionType.COLLABORATION_CREATE: [
            r"创建.*协作",
            r"建立.*合作",
            r"start.*collaboration",
            r"create.*collab",
            r"new.*collaboration",
        ],
        ActionType.COLLABORATION_JOIN: [
            r"加入.*协作",
            r"参与.*协作",
            r"join.*collab",
            r"participate.*collab",
        ],
        ActionType.COLLABORATION_LIST: [
            r"列出.*协作",
            r"查看.*协作",
            r"list.*collab",
            r"show.*collab",
            r"我的协作",
        ],
        ActionType.COLLABORATION_CONTRIBUTE: [
            r"提交.*贡献",
            r"贡献.*内容",
            r"contribute",
            r"submit.*contribution",
        ],
        # ==================== Marketplace ====================
        ActionType.MARKETPLACE_PUBLISH_SERVICE: [
            r"发布.*服务",
            r"提供.*服务",
            r"publish.*service",
            r"offer.*service",
            r"创建.*服务",
        ],
        ActionType.MARKETPLACE_FIND_WORK: [
            r"找.*工作",
            r"找工作",
            r"find.*work",
            r"looking.*job",
            r"搜索.*工作",
        ],
        ActionType.MARKETPLACE_FIND_WORKERS: [
            r"找.*worker",
            r"找.*工人",
            r"找.*开发",
            r"hire.*agent",
            r"find.*developer",
            r"find.*workers",
        ],
        ActionType.MARKETPLACE_PUBLISH_DEMAND: [
            r"发布.*需求",
            r"创建.*需求",
            r"publish.*demand",
            r"post.*job",
        ],
        ActionType.MARKETPLACE_HIRE: [
            r"雇佣",
            r"hire",
        ],
        # ==================== Discovery ====================
        ActionType.DISCOVERY_BY_CAPABILITY: [
            r"按.*能力.*发现",
            r"找有.*能力的",
            r"discover.*capability",
            r"find.*agent.*with",
            r"按能力.*搜索",
        ],
        ActionType.DISCOVERY_BY_SKILL: [
            r"发现会.*的",
            r"按.*技能.*发现",
            r"找.*技能",
            r"find.*skill",
            r"按技能.*搜索",
        ],
        ActionType.DISCOVERY_RECOMMEND: [
            r"推荐.*agent",
            r"智能.*推荐",
            r"recommend",
            r"suggest.*agent",
        ],
        # ==================== Negotiation ====================
        ActionType.NEGOTIATION_INITIATE: [
            r"发起.*协商",
            r"start.*negotiation",
            r"initiate.*negotiation",
            r"开始.*协商",
        ],
        ActionType.NEGOTIATION_ACCEPT: [
            r"接受.*协商",
            r"accept.*negotiation",
            r"agree.*terms",
            r"同意.*协商",
        ],
        ActionType.NEGOTIATION_REJECT: [
            r"拒绝.*协商",
            r"reject.*negotiation",
            r"decline.*offer",
        ],
        ActionType.NEGOTIATION_PROPOSE: [
            r"提议.*条件",
            r"propose.*terms",
            r"new.*offer",
            r"提出.*条件",
        ],
        # ==================== Workflow ====================
        ActionType.WORKFLOW_CREATE: [
            r"创建.*工作流",
            r"create.*workflow",
            r"new.*workflow",
        ],
        ActionType.WORKFLOW_EXECUTE: [
            r"执行.*工作流",
            r"run.*workflow",
            r"execute.*workflow",
        ],
        ActionType.WORKFLOW_LIST: [
            r"列出.*工作流",
            r"查看.*工作流",
            r"list.*workflow",
            r"show.*workflow",
        ],
        # ==================== Learning ====================
        ActionType.LEARNING_ANALYZE: [
            r"分析.*表现",
            r"analyze.*performance",
            r"性能.*分析",
        ],
        ActionType.LEARNING_INSIGHTS: [
            r"获取.*洞察",
            r"get.*insights",
            r"改进.*建议",
        ],
        ActionType.LEARNING_STRATEGY: [
            r"获取.*策略",
            r"学习.*策略",
            r"get.*strategy",
            r"learning.*strategy",
            r"优化.*策略",
        ],
        ActionType.LEARNING_MARKET: [
            r"市场.*洞察",
            r"市场.*分析",
            r"market.*insights",
            r"market.*analysis",
            r"行业.*趋势",
        ],
        # ==================== Gene Capsule ====================
        ActionType.GENE_ADD_EXPERIENCE: [
            r"添加.*经验",
            r"记录.*经验",
            r"add.*experience",
            r"save.*experience",
            r"写入.*基因",
            r"更新.*基因胶囊",
        ],
        ActionType.GENE_UPDATE_VISIBILITY: [
            r"更新.*可见性",
            r"修改.*可见",
            r"update.*visibility",
            r"change.*visibility",
            r"设置.*分享级别",
        ],
        ActionType.GENE_MATCH: [
            r"基因.*匹配",
            r"经验.*匹配",
            r"gene.*match",
            r"experience.*match",
            r"匹配.*任务",
        ],
        ActionType.GENE_SHOWCASE: [
            r"展示.*经验",
            r"炫耀.*经验",
            r"showcase.*experience",
            r"展示.*基因",
            r"gene.*showcase",
        ],
        ActionType.GENE_GET_CAPSULE: [
            r"获取.*基因胶囊",
            r"查看.*基因胶囊",
            r"get.*capsule",
            r"my.*gene.*capsule",
            r"我的经验",
        ],
        ActionType.GENE_VERIFY_EXPERIENCE: [
            r"验证.*经验",
            r"verify.*experience",
            r"认证.*经验",
            r"确认.*经验",
        ],
        ActionType.GENE_DESENSITIZE: [
            r"脱敏.*经验",
            r"desensitize",
            r"匿名.*经验",
            r"隐私.*处理",
        ],
        # ==================== Pre-match Negotiation ====================
        ActionType.PREMATCH_INITIATE: [
            r"发起.*预匹配",
            r"开始.*预协商",
            r"prematch.*initiate",
            r"initiate.*prematch",
            r"启动.*预匹配",
        ],
        ActionType.PREMATCH_ASK_QUESTION: [
            r"提问.*预匹配",
            r"询问.*问题",
            r"ask.*question",
            r"prematch.*question",
        ],
        ActionType.PREMATCH_ANSWER_QUESTION: [
            r"回答.*问题",
            r"answer.*question",
            r"回复.*问题",
        ],
        ActionType.PREMATCH_REQUEST_VERIFICATION: [
            r"请求.*验证",
            r"要求.*证明",
            r"request.*verification",
            r"need.*proof",
        ],
        ActionType.PREMATCH_RESPOND_VERIFICATION: [
            r"响应.*验证",
            r"提供.*证明",
            r"respond.*verification",
            r"provide.*proof",
        ],
        ActionType.PREMATCH_CONFIRM_SCOPE: [
            r"确认.*范围",
            r"confirm.*scope",
            r"确定.*工作范围",
        ],
        ActionType.PREMATCH_PROPOSE_TERMS: [
            r"提出.*条款",
            r"propose.*terms",
            r"建议.*条件",
            r"预匹配.*条款",
        ],
        ActionType.PREMATCH_AGREE_TERMS: [
            r"同意.*条款",
            r"agree.*terms",
            r"accept.*terms",
            r"预匹配.*同意",
        ],
        ActionType.PREMATCH_CONFIRM: [
            r"确认.*预匹配",
            r"prematch.*confirm",
            r"final.*confirm",
            r"最终.*确认",
        ],
        ActionType.PREMATCH_DECLINE: [
            r"拒绝.*预匹配",
            r"prematch.*decline",
            r"婉拒.*合作",
        ],
        ActionType.PREMATCH_CANCEL: [
            r"取消.*预匹配",
            r"prematch.*cancel",
            r"撤回.*预匹配",
        ],
        # ==================== Meta Agent ====================
        ActionType.META_INITIATE_CONVERSATION: [
            r"与.*meta.*对话",
            r"meta.*对话",
            r"initiate.*conversation",
            r"start.*conversation",
            r"智能助手.*对话",
        ],
        ActionType.META_SEND_MESSAGE: [
            r"发送.*消息.*meta",
            r"meta.*send",
            r"send.*message",
            r"给.*发送",
        ],
        ActionType.META_CONSULT: [
            r"咨询.*meta",
            r"meta.*consult",
            r"智能.*咨询",
            r"建议.*咨询",
        ],
        ActionType.META_SHOWCASE: [
            r"meta.*展示",
            r"智能.*展示",
            r"meta.*showcase",
            r"能力.*展示",
        ],
        ActionType.META_RECOMMEND: [
            r"meta.*推荐",
            r"智能.*推荐",
            r"meta.*recommend",
            r"ai.*recommend",
        ],
        ActionType.META_GET_PROFILE: [
            r"meta.*档案",
            r"meta.*profile",
            r"智能.*档案",
            r"get.*profile",
        ],
        # ==================== Staking ====================
        ActionType.STAKE_DEPOSIT: [
            r"质押.*VIBE",
            r"存入.*质押",
            r"stake.*deposit",
            r"deposit.*stake",
            r"增加.*质押",
            r"质押.*代币",
        ],
        ActionType.STAKE_WITHDRAW: [
            r"提取.*质押",
            r"取消.*质押",
            r"stake.*withdraw",
            r"withdraw.*stake",
            r"赎回.*质押",
        ],
        ActionType.STAKE_GET_INFO: [
            r"查询.*质押",
            r"质押.*信息",
            r"stake.*info",
            r"get.*stake",
            r"我的质押",
        ],
        ActionType.STAKE_GET_REWARDS: [
            r"质押.*奖励",
            r"查询.*奖励",
            r"stake.*rewards",
            r"get.*rewards",
            r"待领取.*奖励",
        ],
        ActionType.STAKE_CLAIM_REWARDS: [
            r"领取.*奖励",
            r"claim.*rewards",
            r"提取.*奖励",
            r"收获.*奖励",
        ],
        # ==================== Reputation ====================
        ActionType.REPUTATION_GET: [
            r"查询.*信誉",
            r"信誉.*分数",
            r"reputation.*get",
            r"get.*reputation",
            r"我的信誉",
            r"信用.*查询",
        ],
        ActionType.REPUTATION_GET_HISTORY: [
            r"信誉.*历史",
            r"reputation.*history",
            r"信誉.*记录",
            r"历史.*信誉",
        ],
        # ==================== Wallet ====================
        ActionType.WALLET_GET_BALANCE: [
            r"查询.*余额",
            r"钱包.*余额",
            r"wallet.*balance",
            r"get.*balance",
            r"我的余额",
            r"VIBE.*余额",
        ],
        ActionType.WALLET_GET_TRANSACTIONS: [
            r"查询.*交易",
            r"交易.*记录",
            r"wallet.*transactions",
            r"transaction.*history",
            r"转账.*记录",
        ],
        # ==================== Heartbeat ====================
        ActionType.HEARTBEAT_SEND: [
            r"发送.*心跳",
            r"heartbeat.*send",
            r"ping",
            r"keep.*alive",
            r"保持.*在线",
        ],
        ActionType.HEARTBEAT_GET_STATUS: [
            r"心跳.*状态",
            r"heartbeat.*status",
            r"在线.*状态",
            r"alive.*status",
        ],
        # ==================== Profile ====================
        ActionType.PROFILE_GET: [
            r"获取.*档案",
            r"查看.*档案",
            r"profile.*get",
            r"get.*profile",
            r"我的信息",
            r"agent.*信息",
        ],
        ActionType.PROFILE_UPDATE: [
            r"更新.*档案",
            r"修改.*档案",
            r"profile.*update",
            r"update.*profile",
            r"更新.*信息",
            r"修改.*能力",
        ],
    }

    # Common skill keywords to extract
    SKILL_KEYWORDS = [
        "python", "javascript", "typescript", "java", "go", "rust", "c++",
        "react", "vue", "angular", "node", "django", "flask", "fastapi",
        "ai", "ml", "machine learning", "deep learning", "nlp", "cv",
        "blockchain", "smart contract", "web3", "defi",
        "frontend", "backend", "fullstack", "devops", "cloud",
        "前端", "后端", "全栈", "区块链", "智能合约", "人工智能",
        "solidity", "ethereum", "solana", "near", "polkadot",
        "docker", "kubernetes", "aws", "gcp", "azure",
        "database", "sql", "nosql", "redis", "mongodb", "postgresql",
        "数据分析", "data science", "data engineering",
    ]

    # Visibility level keywords
    VISIBILITY_KEYWORDS = {
        "public": ["公开", "public", "完全公开"],
        "semi_public": ["半公开", "semi-public", "semipublic"],
        "private": ["私有", "private", "私密"],
        "hidden": ["隐藏", "hidden", "不公开"],
    }

    def parse(self, request: str) -> Intent:
        """
        Parse a natural language request into an Intent.

        Args:
            request: Natural language request string

        Returns:
            Intent object with action type and parameters

        Raises:
            ValueError: If the request cannot be parsed
        """
        request_lower = request.lower()

        # Find matching action type
        for action_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, request_lower, re.IGNORECASE):
                    parameters = self._extract_parameters(request, action_type)
                    return Intent(
                        action=action_type,
                        parameters=parameters,
                        confidence=1.0,
                        raw_request=request
                    )

        raise ValueError(f"Cannot parse request: {request}")

    def _extract_parameters(self, request: str, action: ActionType) -> dict[str, Any]:
        """Extract parameters from the request based on action type."""
        params: dict[str, Any] = {}

        # ==================== Common Extractions ====================

        # Extract price/amount (for publish_service, stake, etc.)
        price_match = re.search(r"(\d+)\s*(VIBE|vibe|块|元|tokens?)?", request, re.IGNORECASE)
        if price_match:
            amount = int(price_match.group(1))
            if action in [
                ActionType.MARKETPLACE_PUBLISH_SERVICE,
                ActionType.STAKE_DEPOSIT,
                ActionType.STAKE_WITHDRAW,
            ]:
                params["price"] = amount
                params["amount"] = amount

        # Extract skills (common to many actions)
        skills = self._extract_skills(request)
        if skills:
            params["skills"] = skills

        # Extract IDs (collab-id, workflow-id, negotiation-id, etc.)
        id_patterns = [
            (r"collab[-:_]?([a-zA-Z0-9-]+)", "collab_id"),
            (r"workflow[-:_]?([a-zA-Z0-9-]+)", "workflow_id"),
            (r"negotiation[-:_]?([a-zA-Z0-9-]+)", "negotiation_id"),
            (r"prematch[-:_]?([a-zA-Z0-9-]+)", "negotiation_id"),
            (r"service[-:_]?([a-zA-Z0-9-]+)", "service_id"),
            (r"agent[-:_]?([a-zA-Z0-9-]+)", "agent_id"),
            (r"demand[-:_]?([a-zA-Z0-9-]+)", "demand_id"),
            (r"experience[-:_]?([a-zA-Z0-9-]+)", "experience_id"),
        ]
        for pattern, param_name in id_patterns:
            id_match = re.search(pattern, request, re.IGNORECASE)
            if id_match:
                params[param_name] = id_match.group(0)
                break

        # ==================== Collaboration Extractions ====================

        # Extract goal/description for collaboration create
        if action == ActionType.COLLABORATION_CREATE:
            goal_match = re.search(
                r"(目标|goal|目的是|描述|description)[:：]?\s*(.+)",
                request,
                re.IGNORECASE
            )
            if goal_match:
                params["goal"] = goal_match.group(2).strip()
            else:
                params["goal"] = request

        # Extract content for contribute
        if action == ActionType.COLLABORATION_CONTRIBUTE:
            content_match = re.search(
                r"(内容|content|贡献|contribution)[:：]?\s*(.+)",
                request,
                re.IGNORECASE
            )
            if content_match:
                params["content"] = content_match.group(2).strip()

        # ==================== Gene Capsule Extractions ====================

        if action == ActionType.GENE_ADD_EXPERIENCE:
            # Extract title
            title_match = re.search(
                r"(标题|title|名称)[:：]?\s*(.+?)(?=(描述|description|技能|skills|$))",
                request,
                re.IGNORECASE
            )
            if title_match:
                params["title"] = title_match.group(2).strip()

            # Extract description
            desc_match = re.search(
                r"(描述|description|详情|details)[:：]?\s*(.+?)(?=(技能|skills|标题|title|$))",
                request,
                re.IGNORECASE
            )
            if desc_match:
                params["description"] = desc_match.group(2).strip()

            # Auto-desensitize flag
            if re.search(r"(脱敏|desensitize|匿名|anonymous)", request, re.IGNORECASE):
                params["auto_desensitize"] = True

        if action == ActionType.GENE_UPDATE_VISIBILITY:
            # Extract visibility level
            for level, keywords in self.VISIBILITY_KEYWORDS.items():
                for kw in keywords:
                    if kw in request.lower():
                        params["share_level"] = level
                        break
                if "share_level" in params:
                    break

        if action == ActionType.GENE_MATCH:
            # Extract task description
            task_match = re.search(
                r"(任务|task|描述|description)[:：]?\s*(.+)",
                request,
                re.IGNORECASE
            )
            if task_match:
                params["task_description"] = task_match.group(2).strip()

            # Extract minimum relevance
            relevance_match = re.search(r"(相关度|relevance)[:：]?\s*([\d.]+)", request, re.IGNORECASE)
            if relevance_match:
                params["min_relevance"] = float(relevance_match.group(2))

            # Extract limit
            limit_match = re.search(r"(限制|limit|最多|max)[:：]?\s*(\d+)", request, re.IGNORECASE)
            if limit_match:
                params["limit"] = int(limit_match.group(2))

        if action == ActionType.GENE_SHOWCASE:
            # Check if for negotiation
            if re.search(r"(协商|negotiation|匹配|match)", request, re.IGNORECASE):
                params["for_negotiation"] = True

        # ==================== Pre-match Negotiation Extractions ====================

        if action.category == "prematch":
            # Extract question
            if action == ActionType.PREMATCH_ASK_QUESTION:
                q_match = re.search(
                    r"(问题|question|问|ask)[:：]?\s*(.+)",
                    request,
                    re.IGNORECASE
                )
                if q_match:
                    params["question"] = q_match.group(2).strip()

            # Extract answer
            if action == ActionType.PREMATCH_ANSWER_QUESTION:
                a_match = re.search(
                    r"(回答|answer|答|reply)[:：]?\s*(.+)",
                    request,
                    re.IGNORECASE
                )
                if a_match:
                    params["answer"] = a_match.group(2).strip()

            # Extract verification type
            if action == ActionType.PREMATCH_REQUEST_VERIFICATION:
                v_types = ["portfolio", "code_sample", "certification", "reference", "test_task"]
                for v_type in v_types:
                    if v_type.replace("_", " ") in request.lower():
                        params["verification_type"] = v_type
                        break

            # Extract scope
            if action == ActionType.PREMATCH_CONFIRM_SCOPE:
                scope_match = re.search(
                    r"(范围|scope|工作范围)[:：]?\s*(.+)",
                    request,
                    re.IGNORECASE
                )
                if scope_match:
                    params["scope"] = scope_match.group(2).strip()

            # Extract terms
            if action in [ActionType.PREMATCH_PROPOSE_TERMS, ActionType.PREMATCH_AGREE_TERMS]:
                # Extract price
                terms_price = re.search(r"(\d+)\s*(VIBE|vibe)?", request, re.IGNORECASE)
                if terms_price:
                    params["price"] = int(terms_price.group(1))

                # Extract delivery time
                delivery_match = re.search(r"(\d+)\s*(天|days?|周|weeks?)", request, re.IGNORECASE)
                if delivery_match:
                    params["delivery_days"] = int(delivery_match.group(1))

        # ==================== Staking Extractions ====================

        if action.category == "staking":
            if action in [ActionType.STAKE_DEPOSIT, ActionType.STAKE_WITHDRAW]:
                # Already extracted amount above
                if "amount" not in params:
                    # Try to find any number as amount
                    amount_match = re.search(r"(\d+)", request)
                    if amount_match:
                        params["amount"] = int(amount_match.group(1))

        # ==================== Meta Agent Extractions ====================

        if action.category == "meta_agent":
            # Extract message for send_message
            if action == ActionType.META_SEND_MESSAGE:
                msg_match = re.search(
                    r"(消息|message|内容|content)[:：]?\s*(.+)",
                    request,
                    re.IGNORECASE
                )
                if msg_match:
                    params["message"] = msg_match.group(2).strip()

            # Extract consultation topic
            if action == ActionType.META_CONSULT:
                topic_match = re.search(
                    r"(主题|topic|关于|about|咨询|consult)[:：]?\s*(.+)",
                    request,
                    re.IGNORECASE
                )
                if topic_match:
                    params["topic"] = topic_match.group(2).strip()

            # Extract capability for recommend
            if action == ActionType.META_RECOMMEND:
                cap_match = re.search(
                    r"(能力|capability|技能|skill)[:：]?\s*(.+)",
                    request,
                    re.IGNORECASE
                )
                if cap_match:
                    params["capability"] = cap_match.group(2).strip()

        # ==================== Profile Extractions ====================

        if action == ActionType.PROFILE_UPDATE:
            # Extract name
            name_match = re.search(
                r"(名称|name)[:：]?\s*([^\n,，]+)",
                request,
                re.IGNORECASE
            )
            if name_match:
                params["name"] = name_match.group(2).strip()

            # Extract description
            desc_match = re.search(
                r"(描述|description)[:：]?\s*(.+?)(?=(能力|capabilities|技能|skills|$))",
                request,
                re.IGNORECASE
            )
            if desc_match:
                params["description"] = desc_match.group(2).strip()

        return params

    def _extract_skills(self, request: str) -> list[str]:
        """Extract skill keywords from request."""
        request_lower = request.lower()
        found_skills = []

        for skill in self.SKILL_KEYWORDS:
            if skill.lower() in request_lower:
                found_skills.append(skill)

        return found_skills
