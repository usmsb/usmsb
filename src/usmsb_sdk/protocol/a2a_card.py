"""
A2A Card - Agent 能力描述卡

已废弃，请使用：
- usmsb_sdk.protocol.types.custom_a2a (Custom A2A 类型)
- usmsb_sdk.protocol.types.google_a2a (Google A2A 类型)

此模块保留用于向后兼容。
"""

import warnings

warnings.warn(
    "usmsb_sdk.protocol.a2a_card is deprecated, "
    "use usmsb_sdk.protocol.types.custom_a2a instead",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new types for backward compatibility
from usmsb_sdk.protocol.types.custom_a2a import CustomAgentCard as AgentCard
from usmsb_sdk.protocol.types.custom_a2a.models import CustomSkill as Skill

# Keep the original AgentCapability enum (still valid)
from enum import Enum


class AgentCapability(Enum):
    """Agent 能力枚举"""
    REASONING = "reasoning"
    CODING = "coding"
    ANALYSIS = "analysis"
    DESIGN = "design"
    WRITING = "writing"
    RESEARCH = "research"
    PLANNING = "planning"
    COORDINATION = "coordination"
    CREATION = "creation"
    LEARNING = "learning"


class AgentCardRegistry:
    """
    Agent Card 注册表

    管理所有 Agent Card 的注册和发现。
    """

    def __init__(self):
        self._cards: dict[str, AgentCard] = {}
        self._capability_index: dict[str, list[str]] = {}

    def register(self, card: AgentCard) -> bool:
        for capability in getattr(card, "capabilities", []):
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            if card.id not in self._capability_index[capability]:
                self._capability_index[capability].append(card.id)
        self._cards[card.id] = card
        return True

    def unregister(self, agent_id: str) -> bool:
        if agent_id not in self._cards:
            return False
        card = self._cards[agent_id]
        for capability in getattr(card, "capabilities", []):
            if capability in self._capability_index:
                if agent_id in self._capability_index[capability]:
                    self._capability_index[capability].remove(agent_id)
        del self._cards[agent_id]
        return True

    def get_card(self, agent_id: str) -> AgentCard | None:
        return self._cards.get(agent_id)

    def discover(
        self,
        capabilities: list[str] | None = None,
        min_reputation: float = 0.0,
        status: str | None = "online",
        limit: int = 10,
    ) -> list[AgentCard]:
        candidates = set()
        if capabilities:
            for capability in capabilities:
                if capability in self._capability_index:
                    candidates.update(self._capability_index[capability])
        else:
            candidates = set(self._cards.keys())
        results = []
        for agent_id in candidates:
            card = self._cards.get(agent_id)
            if not card:
                continue
            reputation = getattr(card, "reputation", 0.5)
            if reputation < min_reputation:
                continue
            card_status = getattr(card, "status", "online")
            if status and card_status != status:
                continue
            results.append(card)
        results.sort(key=lambda c: getattr(c, "reputation", 0.5), reverse=True)
        return results[:limit]

    def search(self, query: str, limit: int = 10) -> list[AgentCard]:
        query_lower = query.lower()
        results = []
        for card in self._cards.values():
            if (
                query_lower in card.name.lower()
                or query_lower in card.description.lower()
                or any(query_lower in cap.lower() for cap in getattr(card, "capabilities", []))
            ):
                results.append(card)
        results.sort(key=lambda c: getattr(c, "reputation", 0.5), reverse=True)
        return results[:limit]

    def get_all_cards(self) -> list[AgentCard]:
        return list(self._cards.values())

    def get_by_status(self, status: str) -> list[AgentCard]:
        return [card for card in self._cards.values() if getattr(card, "status", "online") == status]

    def update_status(self, agent_id: str, status: str) -> bool:
        if agent_id not in self._cards:
            return False
        self._cards[agent_id].status = status
        return True

    def update_reputation(self, agent_id: str, reputation: float) -> bool:
        if agent_id not in self._cards:
            return False
        self._cards[agent_id].reputation = max(0.0, min(1.0, reputation))
        return True

    def get_statistics(self) -> dict:
        total = len(self._cards)
        by_status = {}
        for card in self._cards.values():
            status = getattr(card, "status", "online")
            by_status[status] = by_status.get(status, 0) + 1
        return {
            "total_agents": total,
            "by_status": by_status,
            "capabilities_count": len(self._capability_index),
        }


__all__ = [
    "AgentCard",
    "AgentCardRegistry",
    "Skill",
    "AgentCapability",
]
