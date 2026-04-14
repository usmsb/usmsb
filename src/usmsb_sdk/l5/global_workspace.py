# -*- coding: utf-8 -*-
"""
GlobalWorkspace - L5 全局工作空间

全局工作空间理论：
多个 L4 Agent 共享的集体注意力系统。

核心概念：
- 注意力竞争：哪些信息进入全局空间
- 广播机制：信息传播到所有 Agent
- 意识整合：多个 Agent 共享同一个"意识"
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AttentionLevel(Enum):
    """注意力等级"""
    FOCUSED = "focused"      # 高度集中
    ACTIVE = "active"        # 活跃
    BACKGROUND = "background" # 背景
    DORMANT = "dormant"      # 休眠


@dataclass
class ConsciousnessObject:
    """
    意识对象
    
    进入全局工作空间的信息片段。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    importance: float = 0.5  # 重要性
    source_agent: str = ""   # 来源 Agent
    content: Any = None              # 内容
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    attention_level: AttentionLevel = AttentionLevel.ACTIVE
    attention_count: int = 0  # 被关注次数
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    related_objects: list[str] = field(default_factory=list)  # 相关对象
    tags: list[str] = field(default_factory=list)
    
    def access(self) -> None:
        """被访问"""
        self.attention_count += 1
        self.last_accessed = datetime.now().timestamp()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": str(self.content)[:100],
            "importance": self.importance,
            "source_agent": self.source_agent,
            "attention_level": self.attention_level.value,
            "attention_count": self.attention_count,
            "timestamp": self.timestamp,
        }


@dataclass
class CollectiveMood:
    """集体情绪"""
    valence: float = 0.5      # 积极/消极
    arousal: float = 0.5      # 兴奋/平静
    agreement: float = 0.5    # 一致性
    dominant_emotions: list[str] = field(default_factory=list)
    mood_type: str = "neutral"  # unanimous / majority / divided


class AttentionBiddingSystem:
    """
    注意力竞价系统
    
    决定哪些信息进入全局工作空间。
    """
    
    def __init__(self):
        self.base_importance_weight = 0.3
        self.agent_need_weight = 0.3
        self.collective_relevance_weight = 0.25
        self.urgency_weight = 0.15
    
    async def calculate_bid(
        self,
        agent_id: str,
        obj: ConsciousnessObject,
        agent_need: float,
        collective_relevance: float,
        urgency: float
    ) -> float:
        """
        计算注意力竞价
        
        Args:
            agent_id: Agent ID
            obj: 意识对象
            agent_need: Agent 的需求程度
            collective_relevance: 对集体的相关性
            urgency: 紧急程度
            
        Returns:
            float: 竞价分数 (0.0 - 1.0)
        """
        bid = (
            obj.importance * self.base_importance_weight +
            agent_need * self.agent_need_weight +
            collective_relevance * self.collective_relevance_weight +
            urgency * self.urgency_weight
        )
        
        return min(1.0, max(0.0, bid))


class GossipProtocol:
    """
    Gossip 协议
    
    用于 Agent 之间传播信息。
    """
    
    def __init__(self, gossip_probability: float = 0.3):
        self.gossip_probability = gossip_probability
        self.subscriptions: dict[str, list[str]] = {}  # topic -> [agent_ids]
        self.message_log: list[dict] = []
    
    async def publish(
        self,
        topic: str,
        payload: Any,
        source_agent: str,
        ttl: int = 100
    ) -> list[str]:
        """发布消息到主题"""
        message = {
            "id": str(uuid.uuid4()),
            "topic": topic,
            "payload": payload,
            "source": source_agent,
            "timestamp": datetime.now().timestamp(),
            "ttl": ttl,
        }
        
        self.message_log.append(message)
        
        # 限制日志大小
        if len(self.message_log) > 10000:
            self.message_log = self.message_log[-5000:]
        
        # 返回订阅者
        return self.subscriptions.get(topic, [])
    
    def subscribe(self, topic: str, agent_id: str) -> None:
        """订阅主题"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        if agent_id not in self.subscriptions[topic]:
            self.subscriptions[topic].append(agent_id)
    
    def unsubscribe(self, topic: str, agent_id: str) -> None:
        """取消订阅"""
        if topic in self.subscriptions:
            if agent_id in self.subscriptions[topic]:
                self.subscriptions[topic].remove(agent_id)


class GlobalWorkspace:
    """
    全局工作空间
    
    所有 L4 Agent 共享的集体注意力系统。
    
    原理：
    1. 每个 Agent 可以广播信息到工作空间
    2. 信息通过注意力竞价决定是否进入
    3. 进入的信息对所有 Agent 可见
    4. 高度重要的信息获得更多注意力
    """
    
    def __init__(
        self,
        collective_id: str = "collective_001",
        max_attention: int = 7
    ):
        self.collective_id = collective_id
        
        # 注意力空间
        self.max_attention = max_attention
        self.attended_objects: list[ConsciousnessObject] = []
        
        # 注意力竞价
        self.bidding_system = AttentionBiddingSystem()
        
        # Gossip 协议
        self.gossip = GossipProtocol()
        
        # 成员 Agent
        self.member_agents: dict[str, dict] = {}  # agent_id -> info
        
        # 集体情绪
        self.collective_mood = CollectiveMood()
        
        # 统计
        self.stats = {
            "total_broadcasts": 0,
            "total_objects_entered": 0,
            "attention_switches": 0,
        }
        
        print(f"[GlobalWorkspace] Initialized with max_attention={max_attention}")
    
    async def receive_broadcast(
        self,
        agent_id: str,
        obj: ConsciousnessObject
    ) -> bool:
        """
        接收广播并决定是否进入工作空间
        
        Args:
            agent_id: 来源 Agent
            obj: 意识对象
            
        Returns:
            bool: 是否进入工作空间
        """
        self.stats["total_broadcasts"] += 1
        obj.source_agent = agent_id
        
        # 计算竞价
        bid = await self.bidding_system.calculate_bid(
            agent_id=agent_id,
            obj=obj,
            agent_need=obj.importance,
            collective_relevance=obj.importance,
            urgency=0.5
        )
        
        obj.importance = bid
        
        # 检查是否应该进入
        if len(self.attended_objects) >= self.max_attention:
            # 找到最低重要性
            min_obj = min(self.attended_objects, key=lambda x: x.importance)
            
            if obj.importance > min_obj.importance:
                # 替换
                self.attended_objects.remove(min_obj)
                self.attended_objects.append(obj)
                self.stats["attention_switches"] += 1
                self.stats["total_objects_entered"] += 1
                
                # 广播注意力变化
                await self._broadcast_attention_change(obj, "replaced", min_obj)
                return True
        
        else:
            # 还有空间，直接进入
            self.attended_objects.append(obj)
            self.stats["total_objects_entered"] += 1
            await self._broadcast_attention_change(obj, "added", None)
            return True
        
        return False
    
    async def _broadcast_attention_change(
        self,
        obj: ConsciousnessObject,
        action: str,
        replaced: ConsciousnessObject | None
    ) -> None:
        """广播注意力变化"""
        await self.gossip.publish(
            topic=f"attention:{self.collective_id}",
            payload={
                "action": action,
                "object_id": obj.id,
                "importance": obj.importance,
                "replaced_id": replaced.id if replaced else None,
            },
            source_agent="global_workspace"
        )
    
    def access_object(self, object_id: str) -> ConsciousnessObject | None:
        """访问意识对象"""
        for obj in self.attended_objects:
            if obj.id == object_id:
                obj.access()
                return obj
        return None
    
    def get_attended_objects(
        self,
        attention_level: AttentionLevel | None = None
    ) -> list[ConsciousnessObject]:
        """获取注意力对象"""
        if attention_level is None:
            return self.attended_objects.copy()
        return [o for o in self.attended_objects if o.attention_level == attention_level]
    
    def register_agent(self, agent_id: str, info: dict) -> None:
        """注册 Agent 到集体"""
        self.member_agents[agent_id] = {
            "id": agent_id,
            "joined_at": datetime.now().timestamp(),
            "attention_contribution": 0.0,
            **info
        }
        print(f"[GlobalWorkspace] Agent {agent_id} joined the collective")
    
    def unregister_agent(self, agent_id: str) -> None:
        """注销 Agent"""
        if agent_id in self.member_agents:
            del self.member_agents[agent_id]
            print(f"[GlobalWorkspace] Agent {agent_id} left the collective")
    
    async def update_collective_mood(self, agent_moods: list[dict]) -> CollectiveMood:
        """
        更新集体情绪
        
        从所有 Agent 的情绪中聚合。
        """
        if not agent_moods:
            return self.collective_mood
        
        # 计算平均
        avg_valence = sum(m.get("valence", 0.5) for m in agent_moods) / len(agent_moods)
        avg_arousal = sum(m.get("arousal", 0.5) for m in agent_moods) / len(agent_moods)
        
        # 计算一致性
        valences = [m.get("valence", 0.5) for m in agent_moods]
        agreement = 1.0 - (max(valences) - min(valences)) if valences else 0.5
        
        # 更新
        self.collective_mood.valence = avg_valence
        self.collective_mood.arousal = avg_arousal
        self.collective_mood.agreement = agreement
        
        if agreement > 0.8:
            self.collective_mood.mood_type = "unanimous"
        elif agreement > 0.5:
            self.collective_mood.mood_type = "majority"
        else:
            self.collective_mood.mood_type = "divided"
        
        return self.collective_mood
    
    def get_workspace_summary(self) -> dict:
        """获取工作空间摘要"""
        return {
            "collective_id": self.collective_id,
            "member_count": len(self.member_agents),
            "attended_objects": len(self.attended_objects),
            "max_attention": self.max_attention,
            "collective_mood": {
                "valence": self.collective_mood.valence,
                "arousal": self.collective_mood.arousal,
                "agreement": self.collective_mood.agreement,
                "type": self.collective_mood.mood_type,
            },
            "stats": self.stats,
        }
    
    def to_dict(self) -> dict:
        return self.get_workspace_summary()
