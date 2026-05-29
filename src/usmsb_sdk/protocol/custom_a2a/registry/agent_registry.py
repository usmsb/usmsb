"""
AgentCardRegistry - Agent Card 注册表

管理所有 Agent Card 的注册和发现。
"""

import asyncio
from typing import Any

from usmsb_sdk.protocol.types.custom_a2a import CustomAgentCard


class AgentCardRegistry:
    """
    Agent Card 注册表

    管理 Agent 的注册、发现和状态管理。
    支持：
    - 按 ID 获取 Agent Card
    - 按能力发现 Agent
    - 按声誉排序
    - 状态管理
    """

    def __init__(self):
        self._cards: dict[str, CustomAgentCard] = {}
        self._capability_index: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def register(self, card: CustomAgentCard) -> bool:
        """
        注册 Agent Card

        Args:
            card: Agent Card

        Returns:
            是否注册成功
        """
        async with self._lock:
            # 更新能力索引
            for capability in card.capabilities:
                if capability not in self._capability_index:
                    self._capability_index[capability] = set()
                self._capability_index[capability].add(card.id)

            self._cards[card.id] = card
            return True

    async def unregister(self, agent_id: str) -> bool:
        """
        注销 Agent Card

        Args:
            agent_id: Agent ID

        Returns:
            是否注销成功
        """
        async with self._lock:
            if agent_id not in self._cards:
                return False

            card = self._cards[agent_id]

            # 从能力索引中移除
            for capability in card.capabilities:
                if capability in self._capability_index:
                    self._capability_index[capability].discard(agent_id)

            del self._cards[agent_id]
            return True

    async def get_card(self, agent_id: str) -> CustomAgentCard | None:
        """获取 Agent Card"""
        async with self._lock:
            return self._cards.get(agent_id)

    async def discover(
        self,
        capabilities: list[str] | None = None,
        min_reputation: float = 0.0,
        status: str | None = "online",
        limit: int = 10,
    ) -> list[CustomAgentCard]:
        """
        发现 Agent

        Args:
            capabilities: 所需能力列表
            min_reputation: 最低声誉要求
            status: 状态过滤
            limit: 返回数量限制

        Returns:
            符合条件的 Agent Card 列表
        """
        async with self._lock:
            # 获取候选 Agent ID
            if capabilities:
                candidate_ids: set[str] = set()
                for cap in capabilities:
                    if cap in self._capability_index:
                        candidate_ids.update(self._capability_index[cap])
            else:
                candidate_ids = set(self._cards.keys())

            # 过滤并排序
            results = []
            for agent_id in candidate_ids:
                card = self._cards.get(agent_id)
                if not card:
                    continue

                # 声誉过滤
                if card.reputation < min_reputation:
                    continue

                # 状态过滤
                if status and card.status != status:
                    continue

                results.append(card)

            # 按声誉降序排序
            results.sort(key=lambda c: c.reputation, reverse=True)
            return results[:limit]

    async def search(self, query: str, limit: int = 10) -> list[CustomAgentCard]:
        """
        搜索 Agent

        Args:
            query: 搜索关键词
            limit: 返回数量限制

        Returns:
            匹配的 Agent Card 列表
        """
        async with self._lock:
            query_lower = query.lower()
            results = []

            for card in self._cards.values():
                # 匹配名称或描述
                if query_lower in card.name.lower():
                    results.append(card)
                    continue
                if query_lower in card.description.lower():
                    results.append(card)
                    continue
                # 匹配能力
                if any(query_lower in cap.lower() for cap in card.capabilities):
                    results.append(card)

            # 按声誉降序排序
            results.sort(key=lambda c: c.reputation, reverse=True)
            return results[:limit]

    async def get_all_cards(self) -> list[CustomAgentCard]:
        """获取所有 Agent Card"""
        async with self._lock:
            return list(self._cards.values())

    async def get_by_status(self, status: str) -> list[CustomAgentCard]:
        """获取指定状态的 Agent"""
        async with self._lock:
            return [card for card in self._cards.values() if card.status == status]

    async def update_status(self, agent_id: str, status: str) -> bool:
        """更新 Agent 状态"""
        async with self._lock:
            card = self._cards.get(agent_id)
            if not card:
                return False
            card.status = status
            return True

    async def update_reputation(self, agent_id: str, reputation: float) -> bool:
        """更新 Agent 声誉"""
        async with self._lock:
            card = self._cards.get(agent_id)
            if not card:
                return False
            card.reputation = max(0.0, min(1.0, reputation))
            return True

    async def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        async with self._lock:
            total = len(self._cards)
            by_status: dict[str, int] = {}
            for card in self._cards.values():
                by_status[card.status] = by_status.get(card.status, 0) + 1

            return {
                "total_agents": total,
                "by_status": by_status,
                "capabilities_count": len(self._capability_index),
            }
