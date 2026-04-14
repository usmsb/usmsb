# -*- coding: utf-8 -*-
"""
L2 AgentMemory - 分层记忆系统

L2 = L1 + 记忆 + 工具调用能力

分层记忆：
- Working Memory: 当前会话
- Episodic Memory: 经历/情景
- Semantic Memory: 知识/语义
- Procedural Memory: 技能/程序
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryType(Enum):
    """记忆类型"""
    WORKING = "working"      # 工作记忆（当前会话）
    EPISODIC = "episodic"    # 情景记忆（经历）
    SEMANTIC = "semantic"    # 语义记忆（知识）
    PROCEDURAL = "procedural"  # 程序记忆（技能）


@dataclass
class MemoryEntry:
    """
    记忆条目
    
    统一存储所有类型的记忆。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # 内容
    content: Any = None
    
    # 类型
    memory_type: MemoryType = MemoryType.WORKING
    
    # 元数据
    importance: float = 0.5  # 0.0 - 1.0
    access_count: int = 0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    
    # 标签和索引
    tags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    
    # 关联
    related_memories: list[str] = field(default_factory=list)  # 关联的记忆 ID
    
    # 来源
    source: str = "unknown"
    
    def access(self) -> None:
        """访问记忆"""
        self.access_count += 1
        self.last_accessed = datetime.now().timestamp()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.memory_type.value,
            "content": str(self.content)[:100],
            "importance": self.importance,
            "access_count": self.access_count,
            "tags": self.tags,
            "created_at": self.created_at,
        }


@dataclass
class ConversationTurn:
    """对话回合"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"  # user / assistant / system
    content: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)


class WorkingMemory:
    """
    工作记忆
    
    当前会话的短期记忆。
    """
    
    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self.turns: list[ConversationTurn] = []
    
    def add_turn(self, role: str, content: str, metadata: dict | None = None) -> None:
        """添加对话回合"""
        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.turns.append(turn)
        
        # 限制大小
        if len(self.turns) > self.max_size:
            self.turns = self.turns[-self.max_size:]
    
    def get_context(self, last_n: int | None = None) -> list[ConversationTurn]:
        """获取上下文"""
        if last_n is None:
            return self.turns.copy()
        return self.turns[-last_n:]
    
    def get_last_turn(self) -> ConversationTurn | None:
        """获取最后一个回合"""
        return self.turns[-1] if self.turns else None
    
    def clear(self) -> None:
        """清空工作记忆"""
        self.turns.clear()
    
    def to_dict(self) -> dict:
        return {
            "turn_count": len(self.turns),
            "max_size": self.max_size,
            "recent": [
                {"role": t.role, "content": t.content[:50]}
                for t in self.turns[-5:]
            ]
        }


class EpisodicMemory:
    """
    情景记忆
    
    Agent 的经历记录。
    """
    
    def __init__(self, max_episodes: int = 1000):
        self.max_episodes = max_episodes
        self.episodes: list[MemoryEntry] = []
        
        # 按时间索引
        self.timeline_index: list[str] = []  # episode_ids
    
    def add_episode(
        self,
        content: Any,
        importance: float = 0.5,
        tags: list[str] | None = None,
        metadata: dict | None = None
    ) -> str:
        """添加经历"""
        episode = MemoryEntry(
            content=content,
            memory_type=MemoryType.EPISODIC,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.episodes.append(episode)
        self.timeline_index.append(episode.id)
        
        # 限制大小
        if len(self.episodes) > self.max_episodes:
            removed = self.episodes.pop(0)
            self.timeline_index.pop(0)
        
        return episode.id
    
    def get_recent(self, n: int = 10) -> list[MemoryEntry]:
        """获取最近的经历"""
        return self.episodes[-n:]
    
    def search(self, query: str) -> list[MemoryEntry]:
        """搜索经历"""
        results = []
        query_lower = query.lower()
        
        for episode in self.episodes:
            content_str = str(episode.content).lower()
            if query_lower in content_str:
                results.append(episode)
        
        return results
    
    def get_by_time_range(
        self,
        start_time: float,
        end_time: float | None = None
    ) -> list[MemoryEntry]:
        """按时间范围获取"""
        results = []
        for episode in self.episodes:
            if episode.created_at >= start_time:
                if end_time is None or episode.created_at <= end_time:
                    results.append(episode)
        return results
    
    def to_dict(self) -> dict:
        return {
            "episode_count": len(self.episodes),
            "max_episodes": self.max_episodes,
            "recent": [
                str(e.content)[:50] for e in self.episodes[-3:]
            ]
        }


class SemanticMemory:
    """
    语义记忆
    
    Agent 的知识存储。
    """
    
    def __init__(self):
        # 知识条目
        self.knowledge: list[MemoryEntry] = []
        
        # 标签索引: tag -> [entry_ids]
        self.tag_index: dict[str, list[str]] = {}
        
        # 关键词索引: keyword -> [entry_ids]
        self.keyword_index: dict[str, list[str]] = {}
    
    def add_knowledge(
        self,
        content: Any,
        importance: float = 0.5,
        tags: list[str] | None = None,
        keywords: list[str] | None = None
    ) -> str:
        """添加知识"""
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.SEMANTIC,
            importance=importance,
            tags=tags or [],
            keywords=keywords or [],
            source="learned"
        )
        
        self.knowledge.append(entry)
        
        # 更新索引
        for tag in entry.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(entry.id)
        
        for keyword in entry.keywords:
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = []
            self.keyword_index[keyword].append(entry.id)
        
        return entry.id
    
    def query_by_tags(self, tags: list[str]) -> list[MemoryEntry]:
        """按标签查询"""
        result_ids = set()
        for tag in tags:
            if tag in self.tag_index:
                result_ids.update(self.tag_index[tag])
        
        return [
            e for e in self.knowledge
            if e.id in result_ids
        ]
    
    def query_by_keywords(self, keywords: list[str]) -> list[MemoryEntry]:
        """按关键词查询"""
        result_ids = set()
        for keyword in keywords:
            if keyword in self.keyword_index:
                result_ids.update(self.keyword_index[keyword])
        
        return [
            e for e in self.knowledge
            if e.id in result_ids
        ]
    
    def search(self, query: str) -> list[MemoryEntry]:
        """全文搜索"""
        results = []
        query_lower = query.lower()
        
        for entry in self.knowledge:
            content_str = str(entry.content).lower()
            if query_lower in content_str:
                results.append(entry)
            elif any(query_lower in kw.lower() for kw in entry.keywords):
                results.append(entry)
        
        return results
    
    def get_all_tags(self) -> list[str]:
        """获取所有标签"""
        return list(self.tag_index.keys())
    
    def to_dict(self) -> dict:
        return {
            "knowledge_count": len(self.knowledge),
            "tag_count": len(self.tag_index),
            "tags": list(self.tag_index.keys())[:10],
        }


class ProceduralMemory:
    """
    程序记忆
    
    Agent 的技能/程序性知识。
    """
    
    def __init__(self):
        # 技能: name -> skill_data
        self.skills: dict[str, dict] = {}
    
    def add_skill(
        self,
        name: str,
        description: str,
        implementation: Any,
        examples: list[str] | None = None,
        success_rate: float = 0.5
    ) -> None:
        """添加技能"""
        self.skills[name] = {
            "description": description,
            "implementation": implementation,
            "examples": examples or [],
            "success_rate": success_rate,
            "usage_count": 0,
            "created_at": datetime.now().timestamp(),
        }
    
    def get_skill(self, name: str) -> dict | None:
        """获取技能"""
        return self.skills.get(name)
    
    def update_skill_success(
        self,
        name: str,
        success: bool,
        quality: float = 0.5
    ) -> None:
        """更新技能成功率"""
        if name in self.skills:
            skill = self.skills[name]
            skill["usage_count"] += 1
            n = skill["usage_count"]
            # 指数加权移动平均
            skill["success_rate"] = (
                skill["success_rate"] * (n - 1) + (1.0 if success else 0.0)
            ) / n
    
    def list_skills(self) -> list[str]:
        """列出所有技能"""
        return list(self.skills.keys())
    
    def get_best_skills(self, n: int = 5) -> list[tuple[str, float]]:
        """获取成功率最高的技能"""
        sorted_skills = sorted(
            self.skills.items(),
            key=lambda x: x[1]["success_rate"],
            reverse=True
        )
        return [(name, data["success_rate"]) for name, data in sorted_skills[:n]]
    
    def to_dict(self) -> dict:
        return {
            "skill_count": len(self.skills),
            "skills": list(self.skills.keys()),
        }


class AgentMemory:
    """
    完整分层记忆系统
    
    L2 Agent 的记忆基础设施。
    """
    
    def __init__(
        self,
        agent_id: str,
        working_memory_size: int = 20,
        episodic_memory_size: int = 1000
    ):
        self.agent_id = agent_id
        
        # 分层记忆
        self.working = WorkingMemory(max_size=working_memory_size)
        self.episodic = EpisodicMemory(max_episodes=episodic_memory_size)
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        
        # 向量存储（简化版，真实实现会用 ChromaDB）
        self.vector_store: dict[str, list[float]] = {}
        
        print(f"[AgentMemory] Initialized for {agent_id}")
    
    # ========== Working Memory ==========
    
    def add_working_memory(
        self,
        role: str,
        content: str,
        metadata: dict | None = None
    ) -> None:
        """添加工作记忆"""
        self.working.add_turn(role, content, metadata)
    
    def get_working_context(self, last_n: int | None = None) -> list[ConversationTurn]:
        """获取工作记忆上下文"""
        return self.working.get_context(last_n)
    
    # ========== Episodic Memory ==========
    
    def add_episode(
        self,
        content: Any,
        importance: float = 0.5,
        tags: list[str] | None = None
    ) -> str:
        """添加情景记忆"""
        return self.episodic.add_episode(content, importance, tags)
    
    def search_episodes(self, query: str) -> list[MemoryEntry]:
        """搜索情景记忆"""
        return self.episodic.search(query)
    
    # ========== Semantic Memory ==========
    
    def add_knowledge(
        self,
        content: Any,
        importance: float = 0.5,
        tags: list[str] | None = None,
        keywords: list[str] | None = None
    ) -> str:
        """添加语义记忆"""
        return self.semantic.add_knowledge(content, importance, tags, keywords)
    
    def query_knowledge(
        self,
        tags: list[str] | None = None,
        keywords: list[str] | None = None
    ) -> list[MemoryEntry]:
        """查询知识"""
        if tags:
            return self.semantic.query_by_tags(tags)
        elif keywords:
            return self.semantic.query_by_keywords(keywords)
        return []
    
    # ========== Procedural Memory ==========
    
    def add_skill(
        self,
        name: str,
        description: str,
        implementation: Any,
        examples: list[str] | None = None
    ) -> None:
        """添加技能"""
        self.procedural.add_skill(name, description, implementation, examples)
    
    def get_skill(self, name: str) -> dict | None:
        """获取技能"""
        return self.procedural.get_skill(name)
    
    def record_skill_usage(self, skill_name: str, success: bool) -> None:
        """记录技能使用"""
        self.procedural.update_skill_success(skill_name, success)
    
    # ========== 统一接口 ==========
    
    async def get_context(self, query: str | None = None) -> dict:
        """
        获取上下文
        
        Args:
            query: 可选的查询词
            
        Returns:
            dict: 包含各层记忆的上下文
        """
        context = {
            "working": self.working.to_dict(),
            "episodic": self.episodic.to_dict(),
            "semantic": self.semantic.to_dict(),
            "procedural": self.procedural.to_dict(),
        }
        
        # 如果有查询，添加相关记忆
        if query:
            context["relevant_episodes"] = [
                e.to_dict() for e in self.episodic.search(query)[:5]
            ]
            context["relevant_knowledge"] = [
                e.to_dict() for e in self.semantic.search(query)[:5]
            ]
        
        return context
    
    def add_turn(
        self,
        user_input: str,
        assistant_response: str,
        metadata: dict | None = None
    ) -> None:
        """添加对话回合（同时添加用户和助手）"""
        self.working.add_turn("user", user_input, metadata)
        self.working.add_turn("assistant", assistant_response, metadata)
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "working": self.working.to_dict(),
            "episodic": self.episodic.to_dict(),
            "semantic": self.semantic.to_dict(),
            "procedural": self.procedural.to_dict(),
        }
    
    def __repr__(self) -> str:
        return f"AgentMemory({self.agent_id})"
