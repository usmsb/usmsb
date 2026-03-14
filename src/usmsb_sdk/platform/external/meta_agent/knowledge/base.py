"""
Knowledge Base - 知识库
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """知识库"""

    def __init__(self, config):
        self.config = config
        self.knowledge: list[dict[str, Any]] = []

    async def init(self):
        logger.info("Knowledge Base initialized")

    async def add(self, content: str, metadata: dict = None):
        """添加知识"""
        self.knowledge.append({"content": content, "metadata": metadata or {}})

    async def add_knowledge(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        添加知识到知识库

        Returns:
            知识ID
        """
        import uuid

        knowledge_id = str(uuid.uuid4())[:8]
        self.knowledge.append(
            {
                "id": knowledge_id,
                "content": content,
                "metadata": metadata or {},
            }
        )
        logger.info(f"Added knowledge: {knowledge_id}")
        return knowledge_id

    async def search(self, query: str) -> list:
        """搜索知识"""
        return []

    async def retrieve(self, query: str, top_k: int = 5) -> list:
        """检索知识"""
        # 简单的关键词匹配
        results = []
        query_lower = query.lower()
        for item in self.knowledge:
            if query_lower in item.get("content", "").lower():
                results.append(item)
                if len(results) >= top_k:
                    break
        return results

    def get_all(self) -> list[dict[str, Any]]:
        """获取所有知识"""
        return self.knowledge
