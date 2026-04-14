# -*- coding: utf-8 -*-
"""
CollectiveMemory - L5 集体记忆

分布式集体记忆系统，让多个 Agent 共享知识。

核心能力：
- 分布式存储：记忆分散在多个节点
- 共识达成：一致性记忆
- 重要性索引：重要记忆优先检索
- 分布式检索：跨节点搜索
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryImportance(Enum):
    """记忆重要性"""
    CRITICAL = "critical"    # 关键记忆（永久）
    HIGH = "high"          # 重要记忆
    NORMAL = "normal"      # 普通记忆
    LOW = "low"            # 低价值记忆（可清除）


@dataclass
class Memory:
    """
    记忆
    
    Agent 的单个记忆片段。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None
    
    # 元数据
    importance: MemoryImportance = MemoryImportance.NORMAL
    source_agent: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    access_count: int = 0
    
    # 内容类型
    memory_type: str = "experience"  # experience, fact, skill, etc.
    
    # 标签
    tags: list[str] = field(default_factory=list)
    
    # 备份信息
    replicas: int = 0  # 备份数量
    backup_nodes: list[str] = field(default_factory=list)  # 备份节点
    
    def access(self) -> None:
        """访问记忆"""
        self.access_count += 1
        self.last_accessed = datetime.now().timestamp()
    
    def extract_facts(self) -> list[str]:
        """提取事实"""
        if isinstance(self.content, str):
            return [self.content]
        elif isinstance(self.content, dict):
            return [str(v) for v in self.content.values()]
        return []
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": str(self.content)[:100],
            "importance": self.importance.value,
            "source_agent": self.source_agent,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "memory_type": self.memory_type,
            "tags": self.tags,
        }


@dataclass
class ConsensusMemory:
    """共识记忆"""
    facts: dict[str, float]  # fact -> agreement_rate
    confidence: float = 0.5
    supporting_agents: int = 0
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class ImportanceIndex:
    """
    重要性索引
    
    评估和追踪记忆的重要性。
    """
    
    def __init__(self):
        self.base_scores: dict[str, float] = {}  # memory_id -> score
    
    async def evaluate(self, memory: Memory) -> float:
        """
        评估记忆重要性
        
        考虑因素：
        1. 来源（关键 Agent 产生的高）
        2. 访问频率
        3. 时间衰减
        4. 标签权重
        """
        score = 0.5  # 基础分
        
        # 重要性级别
        if memory.importance == MemoryImportance.CRITICAL:
            score = 1.0
        elif memory.importance == MemoryImportance.HIGH:
            score = 0.8
        elif memory.importance == MemoryImportance.LOW:
            score = 0.3
        
        # 访问频率加成
        if memory.access_count > 10:
            score = min(1.0, score + 0.1)
        elif memory.access_count > 50:
            score = min(1.0, score + 0.2)
        
        # 标签权重
        priority_tags = {"critical", "goal", "value", "identity", "skill"}
        for tag in memory.tags:
            if tag in priority_tags:
                score = min(1.0, score + 0.1)
        
        # 备份加成
        if memory.replicas >= 3:
            score = min(1.0, score + 0.05)
        
        self.base_scores[memory.id] = score
        return score
    
    def get_top_memories(
        self,
        memories: list[Memory],
        top_k: int = 10
    ) -> list[Memory]:
        """获取最重要的记忆"""
        scored = [(m, self.base_scores.get(m.id, 0.5)) for m in memories]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:top_k]]


class DistributedRecall:
    """
    分布式检索
    
    在多个 Agent 节点中检索记忆。
    """
    
    def __init__(self):
        self.gossip: Any = None  # Will be injected
        self.local_cache: list[Memory] = []
    
    async def search(
        self,
        query: str,
        top_k: int = 10
    ) -> list[Memory]:
        """
        搜索记忆
        
        策略：
        1. 本地向量搜索
        2. Gossip 查询远程节点
        3. 合并去重
        4. 重排序
        """
        # 简化的文本匹配搜索
        local_results = self._local_search(query, top_k * 2)
        remote_results = await self._gossip_search(query, top_k * 2)
        
        # 合并
        all_results = self._merge_and_dedup(local_results, remote_results)
        
        # 重排序（简化为按重要性）
        ranked = self._rerank(all_results, query)
        
        return ranked[:top_k]
    
    def _local_search(self, query: str, limit: int) -> list[Memory]:
        """本地搜索"""
        query_lower = query.lower()
        results = []
        
        for memory in self.local_cache:
            content_str = str(memory.content).lower()
            if query_lower in content_str:
                results.append(memory)
                if len(results) >= limit:
                    break
        
        return results
    
    async def _gossip_search(
        self,
        query: str,
        limit: int
    ) -> list[Memory]:
        """通过 Gossip 查询远程"""
        # 简化为空列表，实际实现会通过 Gossip 协议
        return []
    
    def _merge_and_dedup(
        self,
        local: list[Memory],
        remote: list[Memory]
    ) -> list[Memory]:
        """合并去重"""
        seen = set()
        results = []
        
        for memory in local + remote:
            if memory.id not in seen:
                seen.add(memory.id)
                results.append(memory)
        
        return results
    
    def _rerank(
        self,
        memories: list[Memory],
        query: str
    ) -> list[Memory]:
        """重排序"""
        # 简化为按访问次数和重要性排序
        return sorted(
            memories,
            key=lambda m: (m.access_count, m.importance.value),
            reverse=True
        )


class CollectiveMemory:
    """
    集体记忆
    
    管理所有 Agent 的共享记忆。
    """
    
    def __init__(self, collective_id: str = "collective_001"):
        self.collective_id = collective_id
        
        # 记忆存储：agent_id -> [memories]
        self.fragments: dict[str, list[Memory]] = {}
        
        # 重要性索引
        self.importance_index = ImportanceIndex()
        
        # 分布式检索
        self.recall_protocol = DistributedRecall()
        
        # 共识阈值
        self.consensus_threshold = 0.6
        
        # 统计
        self.stats = {
            "total_memories": 0,
            "consensus_reached": 0,
            "replications": 0,
        }
        
        print(f"[CollectiveMemory] Initialized for {collective_id}")
    
    async def store(
        self,
        agent_id: str,
        memory: Memory,
        importance: MemoryImportance = MemoryImportance.NORMAL
    ) -> None:
        """
        存储记忆
        
        Args:
            agent_id: Agent ID
            memory: 记忆
            importance: 重要性
        """
        memory.source_agent = agent_id
        memory.importance = importance
        
        # 存储
        if agent_id not in self.fragments:
            self.fragments[agent_id] = []
        self.fragments[agent_id].append(memory)
        
        # 评估重要性
        importance_score = await self.importance_index.evaluate(memory)
        
        # 高重要性记忆备份
        if importance_score > 0.7:
            replicas = await self._find_backup_nodes(agent_id, k=5)
            for node in replicas:
                await self._replicate_to(node, memory)
            memory.replicas = len(replicas)
        
        self.stats["total_memories"] += 1
    
    async def _find_backup_nodes(
        self,
        source: str,
        k: int
    ) -> list[str]:
        """找到备份节点"""
        candidates = [
            aid for aid in self.fragments.keys()
            if aid != source
        ]
        return candidates[:k]
    
    async def _replicate_to(self, node: str, memory: Memory) -> None:
        """复制到节点"""
        if node not in self.fragments:
            self.fragments[node] = []
        self.fragments[node].append(memory)
        self.stats["replications"] += 1
    
    async def reach_consensus(self, topic: str) -> ConsensusMemory:
        """
        就某个话题达成共识
        
        Args:
            topic: 话题
            
        Returns:
            ConsensusMemory: 共识记忆
        """
        # 检索相关记忆
        relevant = await self.recall_protocol.search(topic, top_k=100)
        
        # 统计事实一致性
        fact_counts: dict[str, int] = {}
        for memory in relevant:
            for fact in memory.extract_facts():
                fact_counts[fact] = fact_counts.get(fact, 0) + 1
        
        # 计算共识
        total_agents = len(self.fragments)
        consensus_facts = {}
        
        for fact, count in fact_counts.items():
            agreement = count / total_agents
            if agreement > self.consensus_threshold:
                consensus_facts[fact] = agreement
        
        consensus = ConsensusMemory(
            facts=consensus_facts,
            confidence=len(consensus_facts) / max(len(fact_counts), 1),
            supporting_agents=sum(1 for f in relevant if any(fact in str(m.content) for fact in consensus_facts))
        )
        
        self.stats["consensus_reached"] += 1
        
        return consensus
    
    async def recall(
        self,
        query: str,
        top_k: int = 10
    ) -> list[Memory]:
        """
        检索记忆
        
        Args:
            query: 查询
            top_k: 返回数量
            
        Returns:
            list[Memory]: 相关记忆
        """
        return await self.recall_protocol.search(query, top_k)
    
    def get_agent_memories(self, agent_id: str) -> list[Memory]:
        """获取特定 Agent 的记忆"""
        return self.fragments.get(agent_id, [])
    
    def get_all_memories(self) -> list[Memory]:
        """获取所有记忆"""
        all_memories = []
        for memories in self.fragments.values():
            all_memories.extend(memories)
        return all_memories
    
    def get_statistics(self) -> dict:
        """获取统计"""
        all_memories = self.get_all_memories()
        
        return {
            "collective_id": self.collective_id,
            "total_memories": len(all_memories),
            "agent_count": len(self.fragments),
            "consensus_reached": self.stats["consensus_reached"],
            "replications": self.stats["replications"],
            "importance_distribution": {
                "critical": len([m for m in all_memories if m.importance == MemoryImportance.CRITICAL]),
                "high": len([m for m in all_memories if m.importance == MemoryImportance.HIGH]),
                "normal": len([m for m in all_memories if m.importance == MemoryImportance.NORMAL]),
                "low": len([m for m in all_memories if m.importance == MemoryImportance.LOW]),
            },
        }
    
    def to_dict(self) -> dict:
        return self.get_statistics()
