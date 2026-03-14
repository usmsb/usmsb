"""
上下文管理器 - 整合所有上下文组件

负责构建完整的 LLM 上下文：
1. 系统提示词
2. 用户信息
3. 对话历史
4. 知识库检索
5. 工具描述
6. 技能描述
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from ..knowledge.vector_store import VectorKnowledgeBase
from ..prompts.system_prompt import SYSTEM_PROMPT
from ..prompts.tool_prompts import get_tool_prompt

logger = logging.getLogger(__name__)


@dataclass
class ContextConfig:
    """上下文配置"""

    max_history_messages: int = 20
    max_knowledge_results: int = 5
    max_context_tokens: int = 8000
    include_system_prompt: bool = True
    include_tools: bool = True
    include_knowledge: bool = True
    include_user_info: bool = True


@dataclass
class UserInfo:
    """用户信息"""

    address: str
    role: str = "USER"
    permissions: list[str] = field(default_factory=list)
    voting_power: float = 0.0
    stake: float = 0.0
    binding_type: str = "unknown"
    preferences: dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """
    上下文管理器

    整合所有上下文组件，生成完整的 LLM 输入
    """

    def __init__(
        self,
        db_path: str = "context.db",
        knowledge_base: VectorKnowledgeBase | None = None,
        config: ContextConfig | None = None,
    ):
        self.db_path = db_path
        self.knowledge_base = knowledge_base
        self.config = config or ContextConfig()
        self._user_preferences: dict[str, dict[str, Any]] = {}

    async def init(self):
        """初始化"""
        logger.info("Context Manager initialized")

    async def save(self):
        """保存状态"""
        pass

    def build_system_prompt(
        self,
        user_info: UserInfo | None = None,
        available_tools: list[str] | None = None,
    ) -> str:
        """构建系统提示词"""
        parts = [SYSTEM_PROMPT]

        if user_info and self.config.include_user_info:
            parts.append(self._build_user_context(user_info))

        if available_tools and self.config.include_tools:
            parts.append(get_tool_prompt(available_tools))

        return "\n\n".join(parts)

    def _build_user_context(self, user_info: UserInfo) -> str:
        """构建用户上下文"""
        role_descriptions = {
            "USER": "普通用户",
            "DEVELOPER": "开发者",
            "VALIDATOR": "验证者",
            "ADMIN": "管理员",
            "GOVERNOR": "治理者",
            "SERVICE_PROVIDER": "服务提供者",
            "AI_AGENT": "AI Agent",
        }

        binding_descriptions = {
            "wallet": "真实钱包绑定",
            "manual": "临时标识符",
            "agent": "AI Agent 绑定",
        }

        return f"""
## 当前用户信息

- **钱包地址**: {user_info.address[:8]}...{user_info.address[-4:] if len(user_info.address) > 12 else user_info.address}
- **角色**: {role_descriptions.get(user_info.role, user_info.role)}
- **绑定方式**: {binding_descriptions.get(user_info.binding_type, user_info.binding_type)}
- **投票权**: {user_info.voting_power:.2f}
- **质押**: {user_info.stake:.2f} VIBE
- **权限数量**: {len(user_info.permissions)} 项

请根据用户角色和权限提供相应的服务。
"""

    async def build_messages(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]],
        user_info: UserInfo | None = None,
        available_tools: list[str] | None = None,
        memory_context: dict[str, Any] | None = None,
        smart_recall_context: str = "",
    ) -> list[dict[str, str]]:
        """
        构建完整的消息列表

        Args:
            user_message: 用户当前消息
            conversation_history: 对话历史
            user_info: 用户信息
            available_tools: 可用工具列表
            memory_context: 分层记忆上下文（摘要、用户画像）
            smart_recall_context: 智能召回上下文

        Returns:
            完整的消息列表，用于 LLM API 调用
        """
        messages = []

        system_prompt = self.build_system_prompt(user_info, available_tools)

        # 添加知识库检索结果
        knowledge_context = await self._get_knowledge_context(user_message)
        if knowledge_context:
            system_prompt += f"\n\n## 相关知识\n\n{knowledge_context}"

        # 添加分层记忆上下文（摘要、用户画像）
        if memory_context:
            memory_prompt = self._build_memory_prompt(memory_context)
            if memory_prompt:
                system_prompt += f"\n\n{memory_prompt}"

        # 添加智能召回上下文
        if smart_recall_context:
            system_prompt += f"\n\n## 历史相关记忆\n\n{smart_recall_context}"

        messages.append({"role": "system", "content": system_prompt})

        recent_history = (
            conversation_history[-self.config.max_history_messages :]
            if conversation_history
            else []
        )
        for msg in recent_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        return messages

    async def _get_knowledge_context(self, query: str) -> str | None:
        """获取相关知识上下文"""
        if not self.knowledge_base or not self.config.include_knowledge:
            return None

        try:
            results = await self.knowledge_base.search(
                query,
                top_k=self.config.max_knowledge_results,
            )

            if not results:
                return None

            knowledge_parts = []
            for i, result in enumerate(results, 1):
                knowledge_parts.append(
                    f"{i}. [{result.item.category}] {result.item.content[:500]}..."
                    if len(result.item.content) > 500
                    else f"{i}. [{result.item.category}] {result.item.content}"
                )

            return "\n".join(knowledge_parts)
        except Exception as e:
            logger.warning(f"Failed to get knowledge context: {e}")
            return None

    def _build_memory_prompt(self, memory_context: dict[str, Any]) -> str:
        """构建分层记忆提示词"""
        if not memory_context:
            return ""

        parts = []

        # 1. 对话摘要
        summaries = memory_context.get("summaries", [])
        if summaries:
            parts.append("\n## 历史对话摘要")
            for i, summary in enumerate(summaries[:3], 1):
                parts.append(f"\n【之前对话 {i}】（{summary.get('message_count', 0)} 条消息）")
                parts.append(summary.get("summary", ""))
                topics = summary.get("topics", [])
                if topics:
                    parts.append(f"涉及主题: {', '.join(topics)}")
                decisions = summary.get("decisions", [])
                if decisions:
                    parts.append(f"重要决定: {', '.join(decisions)}")

        # 2. 用户画像
        profile = memory_context.get("user_profile")
        if profile:
            parts.append("\n## 用户画像")

            prefs = profile.get("preferences", {})
            if prefs:
                parts.append("\n用户偏好:")
                for k, v in list(prefs.items())[:5]:
                    parts.append(f"- {k}: {v}")

            commitments = profile.get("commitments", [])
            if commitments:
                parts.append("\n用户承诺/决定:")
                for c in commitments[-5:]:
                    parts.append(f"- {c}")

        # 3. 重要记忆
        memories = memory_context.get("important_memories", [])
        if memories:
            parts.append("\n## 重要记忆")
            for mem in memories[:5]:
                parts.append(f"- [{mem.get('type', 'info')}] {mem.get('content', '')}")

        return "\n".join(parts) if parts else ""

    def build_function_calling_tools(
        self,
        available_tools: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        构建 Function Calling 工具定义

        返回 OpenAI/Anthropic 格式的工具定义
        """
        tools = []

        default_tools = [
            {
                "name": "get_system_status",
                "description": "获取系统运行状态，包括节点状态、网络连接、资源使用情况",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_balance",
                "description": "查询指定钱包地址的代币余额",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "要查询的钱包地址",
                        },
                    },
                    "required": ["address"],
                },
            },
            {
                "name": "get_transaction",
                "description": "查询区块链交易详情",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tx_hash": {
                            "type": "string",
                            "description": "交易哈希",
                        },
                    },
                    "required": ["tx_hash"],
                },
            },
            {
                "name": "stake_tokens",
                "description": "质押代币，需要用户确认",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "number",
                            "description": "质押数量",
                        },
                        "token": {
                            "type": "string",
                            "description": "代币类型，默认为 VIBE",
                        },
                    },
                    "required": ["amount"],
                },
            },
            {
                "name": "vote_proposal",
                "description": "对治理提案进行投票",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "proposal_id": {
                            "type": "integer",
                            "description": "提案 ID",
                        },
                        "support": {
                            "type": "boolean",
                            "description": "是否支持该提案",
                        },
                    },
                    "required": ["proposal_id", "support"],
                },
            },
            {
                "name": "query_data",
                "description": "查询数据库或区块链数据",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "查询语句或条件描述",
                        },
                        "table": {
                            "type": "string",
                            "description": "目标表或数据源",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_proposals",
                "description": "获取治理提案列表",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["active", "passed", "rejected", "all"],
                            "description": "提案状态筛选",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回数量限制",
                        },
                    },
                },
            },
            {
                "name": "navigate",
                "description": "导航到指定页面",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "string",
                            "description": "目标页面路径",
                        },
                    },
                    "required": ["page"],
                },
            },
        ]

        if available_tools:
            tool_names = set(available_tools)
            tools = [t for t in default_tools if t["name"] in tool_names]
        else:
            tools = default_tools

        return [{"type": "function", "function": t} for t in tools]

    async def load_project_knowledge(
        self,
        project_path: str,
        categories: list[str] | None = None,
    ) -> int:
        """
        加载项目知识到知识库

        扫描项目目录，提取文档、代码注释等知识
        """
        if not self.knowledge_base:
            logger.warning("Knowledge base not available")
            return 0

        categories = categories or ["docs", "code", "config"]
        loaded_count = 0

        for category in categories:
            category_path = os.path.join(project_path, category)
            if not os.path.exists(category_path):
                continue

            for root, _dirs, files in os.walk(category_path):
                for file in files:
                    if file.endswith((".md", ".txt", ".py", ".json", ".yaml", ".yml")):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, encoding="utf-8") as f:
                                content = f.read()

                            if content.strip():
                                await self.knowledge_base.add_knowledge(
                                    content=content[:2000],
                                    metadata={
                                        "file_path": file_path,
                                        "file_name": file,
                                    },
                                    source="project",
                                    category=category,
                                )
                                loaded_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to load {file_path}: {e}")

        logger.info(f"Loaded {loaded_count} knowledge items from project")
        return loaded_count

    def update_user_preference(
        self,
        user_address: str,
        key: str,
        value: Any,
    ):
        """更新用户偏好"""
        if user_address not in self._user_preferences:
            self._user_preferences[user_address] = {}
        self._user_preferences[user_address][key] = value

    def get_user_preferences(self, user_address: str) -> dict[str, Any]:
        """获取用户偏好"""
        return self._user_preferences.get(user_address, {})
