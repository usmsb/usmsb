"""
Gene Capsule LLM 集成适配器

将 Gene Capsule 的经验、技能作为上下文注入 LLM 生成过程，
实现经验驱动的 RAG（Retrieval Augmented Generation）。

Gene Capsule API:
- platform.gene_capsule.get_capsule()     → 获取胶囊
- platform.gene_capsule.add_experience()  → 添加经验
- platform.gene_capsule.match()          → 匹配相关经验
- platform.gene_capsule.showcase()        → 导出谈判展示
- platform.gene_capsule.search_agents()   → 搜索相关 Agent
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GeneCapsuleAdapter:
    """
    Gene Capsule LLM 适配器

    将 Gene Capsule 经验库作为 LLM 的知识来源，
    在生成/推理时自动注入相关经验上下文。
    """

    def __init__(
        self,
        platform_client,  # USMSB Agent Platform client
        llm_adapter=None,  # LLM adapter for generation
    ):
        self.platform = platform_client
        self.llm_adapter = llm_adapter
        self._capsule_cache = None
        self._cache_ttl = 300  # 5分钟缓存

    async def get_capsule(self, agent_id: str = "") -> dict:
        """
        获取 Agent 的 Gene Capsule

        Returns:
            dict: {experiences: [...], skills: [...], patterns: [...]}
        """
        try:
            result = await self.platform.gene_capsule.get_capsule(agent_id)
            if result.get("success"):
                self._capsule_cache = result.get("data", {})
                return self._capsule_cache
            return {}
        except Exception as e:
            logger.warning(f"[GeneCapsuleAdapter] get_capsule failed: {e}")
            return {}

    async def add_experience(
        self,
        title: str,
        description: str,
        skills: list[str] | None = None,
        auto_desensitize: bool = True,
    ) -> dict:
        """
        添加新经验到 Gene Capsule

        Args:
            title: 经验标题
            description: 经验描述
            skills: 相关技能列表
            auto_desensitize: 自动脱敏

        Returns:
            dict: 添加结果
        """
        try:
            result = await self.platform.gene_capsule.add_experience(
                title=title,
                description=description,
                skills=skills or [],
                auto_desensitize=auto_desensitize,
            )
            # 使胶囊缓存失效
            self._capsule_cache = None
            return result
        except Exception as e:
            logger.warning(f"[GeneCapsuleAdapter] add_experience failed: {e}")
            return {"success": False, "error": str(e)}

    async def find_relevant_experiences(
        self,
        task_description: str,
        required_skills: list[str] | None = None,
        min_relevance: float = 0.3,
        limit: int = 5,
    ) -> list[dict]:
        """
        查找与任务相关的经验（用于 RAG）

        Args:
            task_description: 任务描述
            required_skills: 必需技能
            min_relevance: 最低相关度
            limit: 返回数量

        Returns:
            list[dict]: 相关经验列表
        """
        try:
            result = await self.platform.gene_capsule.match(
                task_description=task_description,
                required_skills=required_skills or [],
                min_relevance=min_relevance,
                limit=limit,
            )
            if result.get("success"):
                return result.get("data", {}).get("experiences", [])
            return []
        except Exception as e:
            logger.warning(f"[GeneCapsuleAdapter] find_relevant_experiences failed: {e}")
            return []

    async def build_rag_context(
        self,
        task_description: str,
        max_experiences: int = 5,
    ) -> str:
        """
        为 LLM 生成构建 RAG 上下文字符串

        Args:
            task_description: 当前任务描述
            max_experiences: 最大注入经验数

        Returns:
            str: 格式化的上下文字符串
        """
        experiences = await self.find_relevant_experiences(
            task_description=task_description,
            limit=max_experiences,
        )

        if not experiences:
            return ""

        context_parts = ["\n## 相关经验参考："]
        for i, exp in enumerate(experiences[:max_experiences], 1):
            title = exp.get("title", "未命名经验")
            description = exp.get("description", "")
            skills = exp.get("skills", [])
            context_parts.append(f"\n### 经验 {i}: {title}")
            context_parts.append(f"描述：{description}")
            if skills:
                context_parts.append(f"技能：{', '.join(skills)}")

        return "\n".join(context_parts)

    async def generate_with_experience(
        self,
        prompt: str,
        task_description: str,
        system_prompt: str = "你是一个有用的 AI 助手。",
        max_experiences: int = 3,
    ) -> str:
        """
        带 Gene Capsule 经验的 LLM 生成

        Args:
            prompt: 用户提示
            task_description: 当前任务描述（用于查找经验）
            system_prompt: 系统提示
            max_experiences: 最大注入经验数

        Returns:
            str: LLM 生成的响应
        """
        if not self.llm_adapter:
            logger.warning("[GeneCapsuleAdapter] No LLM adapter, falling back to plain generation")
            return prompt

        # 构建 RAG 上下文
        rag_context = await self.build_rag_context(
            task_description=task_description,
            max_experiences=max_experiences,
        )

        # 组装完整提示
        if rag_context:
            full_prompt = (
                f"{rag_context}\n\n"
                f"## 当前任务：{task_description}\n\n"
                f"## 你的响应：{prompt}"
            )
        else:
            full_prompt = prompt

        # 调用 LLM
        try:
            result = await self.llm_adapter.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=full_prompt,
            )
            return result
        except Exception as e:
            logger.warning(f"[GeneCapsuleAdapter] generate_with_experience failed: {e}")
            return ""

    async def match_agents(
        self,
        task_description: str,
        required_skills: list[str] | None = None,
        min_relevance: float = 0.3,
    ) -> list[dict]:
        """
        匹配具有相关经验的 Agent（用于 Pre-match Negotiation）

        Args:
            task_description: 任务描述
            required_skills: 必需技能
            min_relevance: 最低相关度

        Returns:
            list[dict]: 匹配的 Agent 列表
        """
        try:
            result = await self.platform.gene_capsule.search_agents(
                task_description=task_description,
                required_skills=required_skills or [],
                min_relevance=min_relevance,
                limit=10,
            )
            if result.get("success"):
                return result.get("data", {}).get("agents", [])
            return []
        except Exception as e:
            logger.warning(f"[GeneCapsuleAdapter] match_agents failed: {e}")
            return []

    async def get_skill_summary(self) -> dict:
        """获取 Gene Capsule 技能摘要"""
        capsule = await self.get_capsule()
        if not capsule:
            return {"skills": [], "total_experiences": 0}

        experiences = capsule.get("experiences", [])
        skills_count = {}
        for exp in experiences:
            for skill in exp.get("skills", []):
                skills_count[skill] = skills_count.get(skill, 0) + 1

        return {
            "skills": sorted(skills_count.keys(), key=lambda x: skills_count[x], reverse=True),
            "skills_count": skills_count,
            "total_experiences": len(experiences),
        }
