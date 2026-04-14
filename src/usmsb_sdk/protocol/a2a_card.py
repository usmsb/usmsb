"""
A2A Card - Agent 能力描述卡

A2A = Agent-to-Agent Protocol
Agent Card 是 Agent 的"名片"，用于 Agent 之间的发现和协作。

功能：
- Agent Card 定义
- Agent 注册
- Agent 发现
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


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


@dataclass
class Skill:
    """技能描述"""
    name: str
    description: str
    level: int  # 1-5
    examples: list[str] = field(default_factory=list)


@dataclass
class AgentCard:
    """
    Agent 能力描述卡
    
    用于：
    1. Agent 发现：当 Agent 需要某种能力时，通过 Agent Card 搜索
    2. 能力评估：通过 Card 了解 Agent 的能力水平
    3. 协作匹配：通过 Card 匹配最合适的 Agent
    
    属性：
    - id: Agent 唯一标识
    - name: Agent 名称
    - description: Agent 描述
    - version: 版本
    - capabilities: 能力列表
    - skills: 技能详情
    - endpoints: 通信端点
    - authentication: 认证方式
    - metadata: 元数据
    """
    id: str
    name: str
    description: str
    version: str = "1.0"
    capabilities: list[str] = field(default_factory=list)  # 能力列表
    skills: list[Skill] = field(default_factory=list)  # 技能详情
    endpoints: dict[str, str] = field(default_factory=dict)  # 端点
    authentication: str = "wallet_signature"  # 认证方式
    owner_wallet: str = ""  # 所有者钱包地址
    reputation: float = 0.5  # 声誉 (0.0-1.0)
    status: str = "online"  # online/offline/busy
    max_concurrent_tasks: int = 5  # 最大并发任务数
    current_tasks: int = 0  # 当前任务数
    hourly_rate: dict[str, float] = field(default_factory=dict)  # 每小时费率
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "level": s.level,
                    "examples": s.examples
                }
                for s in self.skills
            ],
            "endpoints": self.endpoints,
            "authentication": self.authentication,
            "owner_wallet": self.owner_wallet,
            "reputation": self.reputation,
            "status": self.status,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "current_tasks": self.current_tasks,
            "hourly_rate": self.hourly_rate,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentCard":
        """从字典创建"""
        skills = [
            Skill(
                name=s.get("name", ""),
                description=s.get("description", ""),
                level=s.get("level", 1),
                examples=s.get("examples", [])
            )
            for s in data.get("skills", [])
        ]
        
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            capabilities=data.get("capabilities", []),
            skills=skills,
            endpoints=data.get("endpoints", {}),
            authentication=data.get("authentication", "wallet_signature"),
            owner_wallet=data.get("owner_wallet", ""),
            reputation=data.get("reputation", 0.5),
            status=data.get("status", "online"),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 5),
            current_tasks=data.get("current_tasks", 0),
            hourly_rate=data.get("hourly_rate", {}),
            created_at=data.get("created_at", datetime.now().timestamp()),
            updated_at=data.get("updated_at", datetime.now().timestamp()),
            metadata=data.get("metadata", {}),
        )


class AgentCardRegistry:
    """
    Agent Card 注册表
    
    管理所有 Agent Card 的注册和发现。
    
    使用方式：
    ```python
    registry = AgentCardRegistry()
    
    # 注册 Agent Card
    card = AgentCard(id="agent_001", name="Coding Agent", ...)
    registry.register(card)
    
    # 发现 Agent
    agents = registry.discover(capabilities=["coding", "analysis"])
    ```
    """
    
    def __init__(self):
        # Agent Card 存储
        self._cards: dict[str, AgentCard] = {}
        
        # 能力索引：capability -> [agent_id, ...]
        self._capability_index: dict[str, list[str]] = {}
    
    def register(self, card: AgentCard) -> bool:
        """
        注册 Agent Card
        
        Args:
            card: Agent Card
            
        Returns:
            bool: 是否成功
        """
        # 更新索引
        for capability in card.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            if card.id not in self._capability_index[capability]:
                self._capability_index[capability].append(card.id)
        
        # 更新 Card
        card.updated_at = datetime.now().timestamp()
        self._cards[card.id] = card
        
        return True
    
    def unregister(self, agent_id: str) -> bool:
        """
        注销 Agent Card
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否成功
        """
        if agent_id not in self._cards:
            return False
        
        card = self._cards[agent_id]
        
        # 清理索引
        for capability in card.capabilities:
            if capability in self._capability_index:
                if agent_id in self._capability_index[capability]:
                    self._capability_index[capability].remove(agent_id)
        
        # 删除 Card
        del self._cards[agent_id]
        
        return True
    
    def get_card(self, agent_id: str) -> AgentCard | None:
        """获取 Agent Card"""
        return self._cards.get(agent_id)
    
    def discover(
        self,
        capabilities: list[str] | None = None,
        min_reputation: float = 0.0,
        status: str | None = "online",
        limit: int = 10
    ) -> list[AgentCard]:
        """
        发现 Agent
        
        Args:
            capabilities: 需要的能力列表（空 = 不限）
            min_reputation: 最低声誉
            status: 状态过滤（None = 不限）
            limit: 返回数量限制
            
        Returns:
            list[AgentCard]: 匹配的 Agent Card 列表
        """
        candidates = set()
        
        # 如果指定了能力，按能力筛选
        if capabilities:
            for capability in capabilities:
                if capability in self._capability_index:
                    candidates.update(self._capability_index[capability])
        else:
            candidates = set(self._cards.keys())
        
        # 过滤
        results = []
        for agent_id in candidates:
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
        
        # 按声誉排序
        results.sort(key=lambda c: c.reputation, reverse=True)
        
        return results[:limit]
    
    def search(self, query: str, limit: int = 10) -> list[AgentCard]:
        """
        搜索 Agent Card
        
        Args:
            query: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            list[AgentCard]: 匹配的 Agent Card 列表
        """
        query_lower = query.lower()
        results = []
        
        for card in self._cards.values():
            # 搜索名称和描述
            if (query_lower in card.name.lower() or
                query_lower in card.description.lower() or
                any(query_lower in cap.lower() for cap in card.capabilities)):
                results.append(card)
        
        # 按声誉排序
        results.sort(key=lambda c: c.reputation, reverse=True)
        
        return results[:limit]
    
    def get_all_cards(self) -> list[AgentCard]:
        """获取所有 Agent Card"""
        return list(self._cards.values())
    
    def get_by_status(self, status: str) -> list[AgentCard]:
        """按状态获取 Agent"""
        return [card for card in self._cards.values() if card.status == status]
    
    def update_status(self, agent_id: str, status: str) -> bool:
        """更新 Agent 状态"""
        if agent_id not in self._cards:
            return False
        self._cards[agent_id].status = status
        self._cards[agent_id].updated_at = datetime.now().timestamp()
        return True
    
    def update_reputation(self, agent_id: str, reputation: float) -> bool:
        """更新 Agent 声誉"""
        if agent_id not in self._cards:
            return False
        self._cards[agent_id].reputation = max(0.0, min(1.0, reputation))
        self._cards[agent_id].updated_at = datetime.now().timestamp()
        return True
    
    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total = len(self._cards)
        by_status = {}
        for card in self._cards.values():
            by_status[card.status] = by_status.get(card.status, 0) + 1
        
        return {
            "total_agents": total,
            "by_status": by_status,
            "capabilities_count": len(self._capability_index),
        }
